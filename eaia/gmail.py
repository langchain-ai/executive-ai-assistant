import logging
from datetime import datetime, timedelta, time
from pathlib import Path
from typing import Iterable
import pytz
import os
import json

from dateutil import parser
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email.utils
from langchain_auth import Client

from langchain_core.tools import tool
from langchain_core.pydantic_v1 import BaseModel, Field

from eaia.schemas import EmailData

logger = logging.getLogger(__name__)
_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
]


async def get_credentials(
    user_email: str,
    langsmith_api_key: str | None = None
) -> Credentials:
    """Get Google API credentials using langchain auth-client.
    
    Args:
        user_email: User's Gmail email address (used as user_id for auth)
        langsmith_api_key: LangSmith API key for auth client
        
    Returns:
        Google OAuth2 credentials
    """
    api_key = langsmith_api_key or os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        raise ValueError("LANGSMITH_API_KEY environment variable must be set")
    
    client = Client(api_key=api_key)
    
    try:
        # Authenticate with Google using the user's email as user_id
        auth_result = await client.authenticate(
            provider="google",
            scopes=_SCOPES,
            user_id=user_email
        )
        
        if auth_result.needs_auth:
            print(f"Please visit: {auth_result.auth_url}")
            print("Complete the OAuth flow and then retry.")
            
            # Wait for completion outside of LangGraph context
            completed_result = await client.wait_for_completion(
                auth_id=auth_result.auth_id,
                timeout=300
            )
            token = completed_result.token
        else:
            token = auth_result.token
        
        if not token:
            raise ValueError("Failed to obtain access token")
        
        # Create credentials object from the token
        # langchain auth-client returns the access token as a string
        creds = Credentials(
            token=token,
            scopes=_SCOPES
        )
        
        return creds
        
    finally:
        await client.close()


def extract_message_part(msg):
    """Recursively walk through the email parts to find message body."""
    if msg["mimeType"] == "text/plain":
        body_data = msg.get("body", {}).get("data")
        if body_data:
            return base64.urlsafe_b64decode(body_data).decode("utf-8")
    elif msg["mimeType"] == "text/html":
        body_data = msg.get("body", {}).get("data")
        if body_data:
            return base64.urlsafe_b64decode(body_data).decode("utf-8")
    if "parts" in msg:
        for part in msg["parts"]:
            body = extract_message_part(part)
            if body:
                return body
    return "No message body available."


def parse_time(send_time: str):
    try:
        parsed_time = parser.parse(send_time)
        return parsed_time
    except (ValueError, TypeError) as e:
        raise ValueError(f"Error parsing time: {send_time} - {e}")


def create_message(sender, to, subject, message_text, thread_id, original_message_id):
    message = MIMEMultipart()
    message["to"] = ", ".join(to)
    message["from"] = sender
    message["subject"] = subject
    message["In-Reply-To"] = original_message_id
    message["References"] = original_message_id
    message["Message-ID"] = email.utils.make_msgid()
    msg = MIMEText(message_text)
    message.attach(msg)
    raw = base64.urlsafe_b64encode(message.as_bytes())
    raw = raw.decode()
    return {"raw": raw, "threadId": thread_id}


def get_recipients(
    headers,
    email_address,
    addn_receipients=None,
):
    recipients = set(addn_receipients or [])
    sender = None
    for header in headers:
        if header["name"].lower() in ["to", "cc"]:
            recipients.update(header["value"].replace(" ", "").split(","))
        if header["name"].lower() == "from":
            sender = header["value"]
    if sender:
        recipients.add(sender)  # Ensure the original sender is included in the response
    for r in list(recipients):
        if email_address in r:
            recipients.remove(r)
    return list(recipients)


def send_message(service, user_id, message):
    message = service.users().messages().send(userId=user_id, body=message).execute()
    return message


def send_email(
    email_id,
    response_text,
    email_address,
    gmail_token: str | None = None,
    gmail_secret: str | None = None,
    addn_receipients=None,
):
    import asyncio
    creds = asyncio.run(get_credentials(email_address))

    service = build("gmail", "v1", credentials=creds)
    message = service.users().messages().get(userId="me", id=email_id).execute()

    headers = message["payload"]["headers"]
    message_id = next(
        header["value"] for header in headers if header["name"].lower() == "message-id"
    )
    thread_id = message["threadId"]

    # Get recipients and sender
    recipients = get_recipients(headers, email_address, addn_receipients)

    # Create the response
    subject = next(
        header["value"] for header in headers if header["name"].lower() == "subject"
    )
    response_subject = subject
    response_message = create_message(
        "me", recipients, response_subject, response_text, thread_id, message_id
    )
    # Send the response
    send_message(service, "me", response_message)


async def fetch_group_emails(
    to_email,
    minutes_since: int = 30,
    gmail_token: str | None = None,
    gmail_secret: str | None = None,
) -> Iterable[EmailData]:
    creds = await get_credentials(to_email)

    service = build("gmail", "v1", credentials=creds)
    after = int((datetime.now() - timedelta(minutes=minutes_since)).timestamp())

    query = f"(to:{to_email} OR from:{to_email}) after:{after}"
    messages = []
    nextPageToken = None
    # Fetch messages matching the query
    while True:
        results = (
            service.users()
            .messages()
            .list(userId="me", q=query, pageToken=nextPageToken)
            .execute()
        )
        if "messages" in results:
            messages.extend(results["messages"])
        nextPageToken = results.get("nextPageToken")
        if not nextPageToken:
            break

    count = 0
    for message in messages:
        try:
            msg = (
                service.users().messages().get(userId="me", id=message["id"]).execute()
            )
            thread_id = msg["threadId"]
            payload = msg["payload"]
            headers = payload.get("headers")
            # Get the thread details
            thread = service.users().threads().get(userId="me", id=thread_id).execute()
            messages_in_thread = thread["messages"]
            # Check the last message in the thread
            last_message = messages_in_thread[-1]
            last_headers = last_message["payload"]["headers"]
            from_header = next(
                header["value"] for header in last_headers if header["name"] == "From"
            )
            last_from_header = next(
                header["value"]
                for header in last_message["payload"].get("headers")
                if header["name"] == "From"
            )
            if to_email in last_from_header:
                yield {
                    "id": message["id"],
                    "thread_id": message["threadId"],
                    "user_respond": True,
                }
            # Check if the last message was from you and if the current message is the last in the thread
            if to_email not in from_header and message["id"] == last_message["id"]:
                subject = next(
                    header["value"] for header in headers if header["name"] == "Subject"
                )
                from_email = next(
                    (header["value"] for header in headers if header["name"] == "From"),
                    "",
                ).strip()
                _to_email = next(
                    (header["value"] for header in headers if header["name"] == "To"),
                    "",
                ).strip()
                if reply_to := next(
                    (
                        header["value"]
                        for header in headers
                        if header["name"] == "Reply-To"
                    ),
                    "",
                ).strip():
                    from_email = reply_to
                send_time = next(
                    header["value"] for header in headers if header["name"] == "Date"
                )
                # Only process emails that are less than an hour old
                parsed_time = parse_time(send_time)
                body = extract_message_part(payload)
                yield {
                    "from_email": from_email,
                    "to_email": _to_email,
                    "subject": subject,
                    "page_content": body,
                    "id": message["id"],
                    "thread_id": message["threadId"],
                    "send_time": parsed_time.isoformat(),
                }
                count += 1
        except Exception:
            logger.info(f"Failed on {message}")

    logger.info(f"Found {count} emails.")


def mark_as_read(
    message_id,
    user_email: str,
    gmail_token: str | None = None,
    gmail_secret: str | None = None,
):
    import asyncio
    creds = asyncio.run(get_credentials(user_email))

    service = build("gmail", "v1", credentials=creds)
    service.users().messages().modify(
        userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()


class CalInput(BaseModel):
    date_strs: list[str] = Field(
        description="The days for which to retrieve events. Each day should be represented by dd-mm-yyyy string."
    )


@tool(args_schema=CalInput)
def get_events_for_days(date_strs: list[str]):
    """
    Retrieves events for a list of days. If you want to check for multiple days, call this with multiple inputs.

    Input in the format of ['dd-mm-yyyy', 'dd-mm-yyyy']

    Args:
    date_strs: The days for which to retrieve events (dd-mm-yyyy string).

    Returns: availability for those days.
    """
    import asyncio
    # Note: This function needs user_email from config - will be handled by calling code
    from .main.config import get_config
    from langchain_core.runnables.config import ensure_config
    
    config = ensure_config()
    user_config = get_config(config)
    user_email = user_config["email"]
    
    creds = asyncio.run(get_credentials(user_email))
    service = build("calendar", "v3", credentials=creds)
    results = ""
    for date_str in date_strs:
        # Convert the date string to a datetime.date object
        day = datetime.strptime(date_str, "%d-%m-%Y").date()

        start_of_day = datetime.combine(day, time.min).isoformat() + "Z"
        end_of_day = datetime.combine(day, time.max).isoformat() + "Z"

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start_of_day,
                timeMax=end_of_day,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        results += f"***FOR DAY {date_str}***\n\n" + print_events(events)
    return results


def format_datetime_with_timezone(dt_str, timezone="US/Pacific"):
    """
    Formats a datetime string with the specified timezone.

    Args:
    dt_str: The datetime string to format.
    timezone: The timezone to use for formatting.

    Returns:
    A formatted datetime string with the timezone abbreviation.
    """
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    tz = pytz.timezone(timezone)
    dt = dt.astimezone(tz)
    return dt.strftime("%Y-%m-%d %I:%M %p %Z")


def print_events(events):
    """
    Prints the events in a human-readable format.

    Args:
    events: List of events to print.
    """
    if not events:
        return "No events found for this day."

    result = ""

    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        end = event["end"].get("dateTime", event["end"].get("date"))
        summary = event.get("summary", "No Title")

        if "T" in start:  # Only format if it's a datetime
            start = format_datetime_with_timezone(start)
            end = format_datetime_with_timezone(end)

        result += f"Event: {summary}\n"
        result += f"Starts: {start}\n"
        result += f"Ends: {end}\n"
        result += "-" * 40 + "\n"
    return result


def send_calendar_invite(
    emails, title, start_time, end_time, email_address, timezone="PST"
):
    import asyncio
    creds = asyncio.run(get_credentials(email_address))
    service = build("calendar", "v3", credentials=creds)

    # Parse the start and end times
    start_datetime = datetime.fromisoformat(start_time)
    end_datetime = datetime.fromisoformat(end_time)
    emails = list(set(emails + [email_address]))
    event = {
        "summary": title,
        "start": {
            "dateTime": start_datetime.isoformat(),
            "timeZone": timezone,
        },
        "end": {
            "dateTime": end_datetime.isoformat(),
            "timeZone": timezone,
        },
        "attendees": [{"email": email} for email in emails],
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 24 * 60},
                {"method": "popup", "minutes": 10},
            ],
        },
        "conferenceData": {
            "createRequest": {
                "requestId": f"{title}-{start_datetime.isoformat()}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }

    try:
        service.events().insert(
            calendarId="primary",
            body=event,
            sendNotifications=True,
            conferenceDataVersion=1,
        ).execute()
        return True
    except Exception as e:
        logger.info(f"An error occurred while sending the calendar invite: {e}")
        return False

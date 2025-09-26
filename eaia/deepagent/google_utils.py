"""Google tools for oap_tool_server (Gmail and Google Calendar functions)."""

import os
import base64
import logging
from datetime import datetime, time
from typing import List, Dict, Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email.utils
import pytz
from langsmith import traceable
from dotenv import load_dotenv
load_dotenv("../../.env")

logger = logging.getLogger(__name__)

_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]

async def get_credentials():
    from langchain_auth import Client
    client = Client(api_key=os.environ["LANGSMITH_API_KEY"])
    auth_result = await client.authenticate(
        provider="google-oap-prod",
        scopes=_SCOPES,
        user_id=os.environ["EMAIL"]
    )
    from google.oauth2.credentials import Credentials
    print(auth_result)
    return Credentials(auth_result.token)


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


def create_message(
    sender, to, subject, message_text, thread_id=None, original_message_id=None
):
    """Create an email message for sending."""
    message = MIMEMultipart()
    message["to"] = ", ".join(to) if isinstance(to, list) else to
    message["from"] = sender
    message["subject"] = subject
    if original_message_id:
        message["In-Reply-To"] = original_message_id
        message["References"] = original_message_id
    message["Message-ID"] = email.utils.make_msgid()
    msg = MIMEText(message_text)
    message.attach(msg)
    raw = base64.urlsafe_b64encode(message.as_bytes())
    raw = raw.decode()
    return {"raw": raw, "threadId": thread_id} if thread_id else {"raw": raw}


def format_datetime_with_timezone(dt_str, timezone="US/Pacific"):
    """Format a datetime string with the specified timezone."""
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    tz = pytz.timezone(timezone)
    dt = dt.astimezone(tz)
    return dt.strftime("%Y-%m-%d %I:%M %p %Z")


@traceable
async def gmail_send_email(
    to: str,
    subject: str,
    body: str,
    reply_to_message_id: Optional[str] = None,
) -> Dict[str, str]:
    """Send an email via Gmail.

    Args:
        context: Authentication context (automatically injected)
        to: Recipient email address (comma-separated for multiple recipients)
        subject: Email subject
        body: Email body content
        reply_to_message_id: Optional message ID to reply to

    Returns:
        Dict containing success status and message ID
    """
    from googleapiclient.discovery import build

    credentials = await get_credentials()
    service = build("gmail", "v1", credentials=credentials)

    try:
        to_list = [addr.strip() for addr in to.split(",")]
        thread_id = None
        original_message_id = None

        if reply_to_message_id:
            # Get original message for threading
            original_msg = (
                service.users()
                .messages()
                .get(userId="me", id=reply_to_message_id)
                .execute()
            )
            thread_id = original_msg.get("threadId")
            headers = original_msg.get("payload", {}).get("headers", [])
            original_message_id = next(
                (h["value"] for h in headers if h["name"] == "Message-ID"), None
            )

        message = create_message(
            "me", to_list, subject, body, thread_id, original_message_id
        )
        result = service.users().messages().send(userId="me", body=message).execute()
        return {
            "success": True,
            "message_id": result["id"],
            "thread_id": result.get("threadId"),
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to send email: {str(e)}"}


@traceable
async def gmail_mark_as_read(
    message_id: str,
) -> Dict[str, str]:
    """Mark a Gmail message as read.

    Args:
        context: Authentication context (automatically injected)
        message_id: ID of the message to mark as read

    Returns:
        Dict containing success status
    """
    from googleapiclient.discovery import build

    credentials = await get_credentials()
    service = build("gmail", "v1", credentials=credentials)

    try:
        service.users().messages().modify(
            userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
        ).execute()

        return {"success": True, "message": f"Message {message_id} marked as read"}

    except Exception as e:
        return {"success": False, "error": f"Failed to mark as read: {str(e)}"}


@traceable
async def google_calendar_list_events_for_date(
    date_str: str,
) -> List[Dict]:
    """List Google Calendar events for a specific day with basic info and event IDs.

    Args:
        context: Authentication context (automatically injected)
        date_str: Date in 'dd-mm-yyyy' format

    Returns:
        List of events with id, summary, start_time, end_time for the specified day
    """
    from googleapiclient.discovery import build

    credentials = await get_credentials()
    service = build("calendar", "v3", credentials=credentials)

    try:
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
        event_list = []

        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))
            summary = event.get("summary", "No Title")

            # Format datetime if it has timezone info
            if "T" in start:
                start = format_datetime_with_timezone(start)
                end = format_datetime_with_timezone(end)

            event_list.append(
                {
                    "id": event["id"],
                    "summary": summary,
                    "start_time": start,
                    "end_time": end,
                }
            )

        return event_list

    except Exception as e:
        logger.error(f"Failed to get calendar events: {str(e)}")
        return [{"error": f"Failed to get calendar events: {str(e)}"}]


@traceable
async def google_calendar_create_event(
    title: str,
    start_time: str,
    end_time: str,
    attendee_emails: List[str],
    timezone: str = "UTC",
) -> Dict[str, str]:
    """Create a Google Calendar event with meeting invite.

    Args:
        context: Authentication context (automatically injected)
        title: Event title
        start_time: Start time in ISO format (e.g., '2023-12-25T10:00:00')
        end_time: End time in ISO format (e.g., '2023-12-25T11:00:00')
        attendee_emails: List of attendee email addresses
        timezone: Timezone for the event (default: UTC)

    Returns:
        Dict containing success status and event details
    """
    from googleapiclient.discovery import build

    credentials = await get_credentials()
    service = build("calendar", "v3", credentials=credentials)

    try:
        start_datetime = datetime.fromisoformat(start_time)
        end_datetime = datetime.fromisoformat(end_time)

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
            "attendees": [{"email": email} for email in attendee_emails],
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
                    # "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
        }

        created_event = (
            service.events()
            .insert(
                calendarId="primary",
                body=event,
                sendNotifications=True,
                conferenceDataVersion=1,
            )
            .execute()
        )

        return {
            "success": True,
            "event_id": created_event["id"],
            "event_link": created_event.get("htmlLink"),
            "hangout_link": created_event.get("conferenceData", {})
            .get("entryPoints", [{}])[0]
            .get("uri"),
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to create calendar event: {str(e)}"}

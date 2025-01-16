import os
import base64
import logging
from datetime import datetime, timedelta, time
from pathlib import Path
from typing import Iterable, List

import pytz
from dateutil import parser
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email.utils
from functools import lru_cache

logger = logging.getLogger(__name__)

# Constants
_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
]
_ROOT = Path(__file__).parent.absolute()
_SECRETS_DIR = _ROOT / ".secrets"
_SECRETS_PATH = str(_SECRETS_DIR / "secrets.json")
_TOKEN_PATH = str(_SECRETS_DIR / "token.json")

# Utility Functions
def get_header(headers, name, default=None):
    return next((header["value"] for header in headers if header["name"].lower() == name.lower()), default)

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
        return parser.parse(send_time)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Error parsing time: {send_time} - {e}")

# Credentials Handling
@lru_cache(maxsize=1)
def get_credentials(gmail_token: str | None = None, gmail_secret: str | None = None) -> Credentials:
    creds = None
    _SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    
    if gmail_token:
        with open(_TOKEN_PATH, "w") as token:
            token.write(gmail_token)
    if gmail_secret:
        with open(_SECRETS_PATH, "w") as secret:
            secret.write(gmail_secret)

    if os.path.exists(_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(_TOKEN_PATH)

    if not creds or not creds.valid or not creds.has_scopes(_SCOPES):
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(_SECRETS_PATH, _SCOPES)
            creds = flow.run_local_server(port=54191)
        with open(_TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    return creds

# Gmail Functions
def get_gmail_service():
    creds = get_credentials()
    return build("gmail", "v1", credentials=creds)

def fetch_emails(query: str, to_email: str, minutes_since: int = 30) -> Iterable[dict]:
    service = get_gmail_service()
    after = int((datetime.now() - timedelta(minutes=minutes_since)).timestamp())
    query = f"(to:{to_email} OR from:{to_email}) after:{after}"

    messages = []
    next_page_token = None
    while True:
        results = service.users().messages().list(userId="me", q=query, pageToken=next_page_token).execute()
        if "messages" in results:
            messages.extend(results["messages"])
        next_page_token = results.get("nextPageToken")
        if not next_page_token:
            break

    for message in messages:
        try:
            msg = service.users().messages().get(userId="me", id=message["id"]).execute()
            payload = msg["payload"]
            headers = payload.get("headers")

            subject = get_header(headers, "Subject")
            from_email = get_header(headers, "From")
            send_time = parse_time(get_header(headers, "Date"))
            body = extract_message_part(payload)

            yield {
                "id": message["id"],
                "subject": subject,
                "from_email": from_email,
                "send_time": send_time,
                "body": body,
            }
        except Exception as e:
            logger.error(f"Failed to fetch email: {e}")

def send_email_response(message_id: str, response_text: str, additional_recipients: List[str] = None):
    service = get_gmail_service()
    message = service.users().messages().get(userId="me", id=message_id).execute()
    headers = message["payload"]["headers"]

    recipients = set(additional_recipients or [])
    recipients.add(get_header(headers, "From"))

    subject = get_header(headers, "Subject")
    response_subject = f"Re: {subject}"

    reply_message = MIMEMultipart()
    reply_message["to"] = ", ".join(recipients)
    reply_message["subject"] = response_subject
    msg = MIMEText(response_text)
    reply_message.attach(msg)

    raw = base64.urlsafe_b64encode(reply_message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()

# Google Calendar Functions
def get_calendar_service():
    creds = get_credentials()
    return build("calendar", "v3", credentials=creds)

def get_events_for_days(date_strs: List[str]):
    service = get_calendar_service()
    results = ""
    for date_str in date_strs:
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
        results += f"***FOR DAY {date_str}***\n\n" + format_events(events)
    return results

def format_events(events):
    if not events:
        return "No events found for this day.\n"

    result = ""
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        end = event["end"].get("dateTime", event["end"].get("date"))
        summary = event.get("summary", "No Title")

        if "T" in start:  # Only format if it's a datetime
            start = format_datetime_with_timezone(start)
            end = format_datetime_with_timezone(end)

        result += f"Event: {summary}\nStarts: {start}\nEnds: {end}\n{'-' * 40}\n"
    return result

def format_datetime_with_timezone(dt_str, timezone="US/Pacific"):
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    tz = pytz.timezone(timezone)
    dt = dt.astimezone(tz)
    return dt.strftime("%Y-%m-%d %I:%M %p %Z")

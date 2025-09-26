from slack_sdk.web.async_client import AsyncWebClient
import os
from dotenv import load_dotenv
load_dotenv(".env")
from dateutil import parser

TEMPLATE = """# {subject}

[Click here to view the email]({url})

**To**: {to}
**From**: {_from}

{page_content}
"""

def generate_email_markdown(email: dict):
    return TEMPLATE.format(
        subject=email["subject"],
        url=f"https://mail.google.com/mail/u/0/#inbox/{email['id']}",
        to=email["to_email"],
        _from=email["from_email"],
        page_content=email["page_content"],
    )

async def send_slack_message(state, config):
    client = AsyncWebClient(token=os.environ["SLACK_BOT_TOKEN"])
    userId = config["configurable"].get("slack_user_id", None)
    if userId is None:
        return
    if state["notified"]:
        return
    response = await client.conversations_open(users=[userId])
    channel_id = response["channel"]["id"]

    await client.chat_postMessage(
        channel=channel_id,
        text=state["email"]["subject"],
    )

def parse_time(send_time: str):
    try:
        parsed_time = parser.parse(send_time)
        return parsed_time
    except (ValueError, TypeError) as e:
        raise ValueError(f"Error parsing time: {send_time} - {e}")
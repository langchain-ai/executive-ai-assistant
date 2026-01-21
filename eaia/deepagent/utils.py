from dotenv import load_dotenv
load_dotenv(".env")
from dateutil import parser

TEMPLATE = """# {subject}

[Click here to view the email]({url})

**To**: {to}
**From**: {_from}

{page_content}
"""

FILE_TEMPLATE = """
id: {id}
thread_id: {thread_id}
send_time: {send_time}

<email>
**To**: {to}
**From**: {_from}
# {subject}

{page_content}
</email>
"""

SLACK_MSG_TEMPLATE = """You got a message from {_from}: {subject}"""

def generate_email_markdown(email: dict):
    return TEMPLATE.format(
        subject=email["subject"],
        url=f"https://mail.google.com/mail/u/0/#inbox/{email['id']}",
        to=email["to_email"],
        _from=email["from_email"],
        page_content=email["page_content"],
    )

def parse_time(send_time: str):
    try:
        parsed_time = parser.parse(send_time)
        return parsed_time
    except (ValueError, TypeError) as e:
        raise ValueError(f"Error parsing time: {send_time} - {e}")
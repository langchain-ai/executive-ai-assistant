from langgraph.types import interrupt, Command
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langchain.agents.tool_node import InjectedState
from langchain.agents.middleware import AgentMiddleware, ModelRequest
from deepagents import create_deep_agent    
from eaia.deepagent.google_utils import gmail_send_email, gmail_mark_as_read, google_calendar_list_events_for_date, google_calendar_create_event
from eaia.deepagent.prompts import SYSTEM_PROMPT, EMAIL_INPUT_PROMPT, FIND_MEETING_TIME_SYSTEM_PROMPT
from eaia.deepagent.types import EmailAgentState
from eaia.deepagent.utils import generate_email_markdown, send_slack_message
import yaml
from typing import Annotated
from pathlib import Path
import json
from datetime import datetime

@tool(description="Get feedback from the user on what to do with the email")
def message_user(
    state: Annotated[EmailAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    response = interrupt(
        [
            {
                "action_request": {"action": "Get Clarification from User", "args": {}},
                "config": {
                    "allow_respond": True,
                    "allow_accept": False,
                    "allow_edit": False,
                    "description": generate_email_markdown(state["email"])
                }
            }
        ]
    )[0]
    if response["type"] == "response":
        message = f"I asked the user what we should do, this was the response: {response['args']}"
    else:
        message = "The user failed to respond to the question. Please ask again."
    return Command(
        update={
            "messages": [
                ToolMessage(message, tool_call_id=tool_call_id)
            ],
        }
    )

@tool(description="Write an email response to the user")
async def write_email_response(
    content: str,
    new_recipients: list[str],
    state: Annotated[EmailAgentState, InjectedState],
):
    recipients = [state["email"]["to_email"]]
    if isinstance(new_recipients, str):
        new_recipients = json.loads(new_recipients)
        if len(new_recipients) == 0:
            recipients.extend(new_recipients)
    try:
        await gmail_send_email(
            to=",".join(recipients),
            subject=state["email"]["subject"],
            body=content,
            reply_to_message_id=state["email"]["id"],
        )
    except Exception as e:
        return f"Error sending email: {e}"
    return "Successfully sent an email response"
    

@tool(description="Start a new email thread")
async def start_new_email_thread(
    content: str,
    subject: str,
    recipients: list[str]
):
    try:
        await gmail_send_email(
            to=",".join(recipients),
            subject=subject,
            body=content,
        )
    except Exception as e:
        return f"Error sending email: {e}"
    return "Successfully started a new email thread"

@tool(description="Create a new calendar event by sending an invite. The start_time and end_time should be in `2024-07-01T14:00:00` format. IANA Time Zone Database name")
async def send_calendar_invite(
    emails: list[str],
    event_title: str,
    start_time: str,
    end_time: str,
    timezone: str = "America/New_York",
):
    try:
        await google_calendar_create_event(
            title=event_title,
            start_time=start_time,
            end_time=end_time,
            attendee_emails=emails,
            timezone=timezone,
        )
    except Exception as e:
        return f"Error creating calendar event: {e}"
    return "Successfully created a calendar event"

@tool(description="Mark an email as read")
async def mark_email_as_read(
    state: Annotated[EmailAgentState, InjectedState],
):
    try:
        await gmail_mark_as_read(state["email"]["id"])
    except Exception as e:
        return f"Error marking email as read: {e}"
    return "Successfully marked an email as read"

@tool(description="Search events for a day. The date str should be in `dd-mm-yyyy` format")
async def get_events_for_days(
    date_str: str,
):
    try:
        events = await google_calendar_list_events_for_date(date_str)
        return events
    except Exception as e:
        return f"Error getting events for day: {e}"

class EmailAgentMiddleware(AgentMiddleware):
    state_schema=EmailAgentState

    def modify_model_request(self, model_request: ModelRequest, agent_state: EmailAgentState) -> ModelRequest:
        hydrated_prompt = EMAIL_INPUT_PROMPT.format(
            author=agent_state["email"]["from_email"],
            to=agent_state["email"].get("to_email", ""),
            subject=agent_state["email"]["subject"],
            email_thread=agent_state["email"]["page_content"]
        )
        model_request.system_prompt = model_request.system_prompt + "\n\n" + hydrated_prompt
        return model_request


class NotifyUserViaSlackMiddleware(AgentMiddleware):
    # TODO: Implement this later
    pass


config_path = Path(__file__).parent / "config.yaml"
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

agent = create_deep_agent(
    tools=[message_user, write_email_response, start_new_email_thread, send_calendar_invite, mark_email_as_read],
    instructions=SYSTEM_PROMPT.format(
        full_name=config["full_name"],
        name=config["name"],
        background=config["background"],
        triage_no=config["triage_no"],
        triage_email=config["triage_email"],
        triage_notify=config["triage_notify"],
        response_preferences=config["response_preferences"],
        background_preferences=config["background_preferences"]
    ),
    subagents=[
        {
            "name": "find_meeting_times",
            "description": "This agent is responsible for finding the best available meeting times for the user.",
            "prompt": FIND_MEETING_TIME_SYSTEM_PROMPT.format(
                full_name=config["full_name"],
                name=config["name"],
                background=config["background"],
                timezone=config["timezone"],
                schedule_preferences=config["schedule_preferences"],
                current_date=datetime.now().strftime("%Y-%m-%d")
            ),
            "tools": [get_events_for_days],
            "middleware": [EmailAgentMiddleware()]
        }
    ],
    middleware=[EmailAgentMiddleware()],
    tool_configs={
        "write_email_response": {
            "allow_accept": True,
            "allow_respond": True,
            "allow_edit": True,
            "description": "Write an email response to the user"
        },
        "start_new_email_thread": {
            "allow_accept": True,
            "allow_respond": True,
            "allow_edit": True,
            "description": "Start a new email thread"
        },
        "send_calendar_invite": {
            "allow_accept": True,
            "allow_respond": True,
            "allow_edit": True,
            "description": "Send a calendar invite to create a meeting"
        }
    },
).with_config({"recursion_limit": 1000})

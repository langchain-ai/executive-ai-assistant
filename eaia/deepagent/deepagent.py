from langgraph.types import interrupt, Command
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langchain.tools.tool_node import InjectedState
from langchain.agents.middleware import AgentMiddleware, ModelRequest
from deepagents import async_create_deep_agent    
from eaia.deepagent.google_utils import gmail_send_email, gmail_mark_as_read, google_calendar_list_events_for_date, google_calendar_create_event
from eaia.deepagent.prompts import SYSTEM_PROMPT, FIND_MEETING_TIME_SYSTEM_PROMPT
from eaia.deepagent.types import EmailAgentState, NotifiedState, EmailConfigSchema
from eaia.deepagent.utils import generate_email_markdown, SLACK_MSG_TEMPLATE
from langchain_core.runnables import RunnableConfig
from typing import Annotated
import json
from slack_sdk.web.async_client import AsyncWebClient
import os
from dotenv import load_dotenv
from datetime import datetime
load_dotenv("../.env")


@tool(description="Get feedback from the user on what to do with the email")
def message_user(
    question_for_user: str,
    state: Annotated[EmailAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    description = generate_email_markdown(state["email"])
    response = interrupt(
        [
            {
                "action_request": {"action": "Get Clarification from User", "args": {}},
                "config": {
                    "allow_respond": True,
                    "allow_accept": False,
                    "allow_edit": False,
                    "description": description
                },
                "description": f"{question_for_user}\n\n {description}"
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
    recipients = [state["email"]["from_email"]]
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
    # NOTE: Commenting this out in favor of the AddFileToSystemPromptMiddleware
    # def modify_model_request(self, model_request: ModelRequest, agent_state: EmailAgentState) -> ModelRequest:
    #     hydrated_prompt = EMAIL_INPUT_PROMPT.format(
    #         author=agent_state["email"]["from_email"],
    #         to=agent_state["email"].get("to_email", ""),
    #         subject=agent_state["email"]["subject"],
    #         email_thread=agent_state["email"]["page_content"]
    #     )
    #     model_request.system_prompt = model_request.system_prompt + "\n\n" + hydrated_prompt
    #     return model_request


class NotifyUserViaSlackMiddleware(AgentMiddleware):
    state_schema = NotifiedState
    async def after_model(self, state: NotifiedState) -> NotifiedState | None:
        messages = state["messages"]
        notified = state["notified"] if "notified" in state else False
        # We only want this to execute on the first AI Message
        if not messages or len(messages) > 2 or notified:
            return
        last_message = messages[-1]
        userId = os.environ["SLACK_USER_ID"]
        if last_message.type != "ai" or userId is None:
            return
        if "mark_email_as_read" not in [tool_call["name"] for tool_call in last_message.tool_calls]:
            client = AsyncWebClient(token=os.environ["SLACK_BOT_TOKEN"])
            response = await client.conversations_open(users=[userId])
            channel_id = response["channel"]["id"]

            await client.chat_postMessage(
                channel=channel_id,
                text=SLACK_MSG_TEMPLATE.format(
                    _from=state["email"]["from_email"],
                    subject=state["email"]["subject"]
                ),
            )
            return {"notified": True}

class AddFileToSystemPromptMiddleware(AgentMiddleware):
    def __init__(self, files_to_inject: list[str]):
        self.files_to_inject = files_to_inject

    def modify_model_request(self, model_request: ModelRequest, agent_state: dict) -> ModelRequest:
        if "files" not in agent_state:
            print("No files in State - something went wrong")
            return model_request
        files_str = "Here are some relevant files that are accessible in your filesystem: \n\n"
        for file in self.files_to_inject:
            if file in agent_state["files"]:
                files_str += f"{file}\n"
                files_str += f"{agent_state['files'][file]}\n"
                files_str += f"{'-'*30}\n"
        model_request.system_prompt = model_request.system_prompt + "\n\n" + files_str
        return model_request

async def get_deepagent(config: RunnableConfig):
    configurable = config.get("configurable", {})
    graph_config = EmailConfigSchema(**configurable)
    instructions = SYSTEM_PROMPT.format(
        full_name=graph_config.full_name,
        name=graph_config.name,
        background=graph_config.background,
        schedule_preferences=graph_config.schedule_preferences,
        background_preferences=graph_config.background_preferences,
        triage_no=graph_config.triage_no,
        triage_notify=graph_config.triage_notify,
        triage_respond=graph_config.triage_respond,
        writing_preferences=graph_config.writing_preferences,
        timezone=graph_config.timezone,
    )
    find_meeting_times_instructions = FIND_MEETING_TIME_SYSTEM_PROMPT.format(
        full_name=graph_config.full_name,
        name=graph_config.name,
        background=graph_config.background,
        timezone=graph_config.timezone,
        schedule_preferences=graph_config.schedule_preferences,
        current_date=datetime.now().strftime("%Y-%m-%d")
    )

    agent = async_create_deep_agent(
        tools=[message_user, write_email_response, start_new_email_thread, send_calendar_invite, mark_email_as_read],
        instructions=instructions,
        subagents=[
            {
                "name": "find_meeting_times",
                "description": "This agent is responsible for finding the best available meeting times for the user.",
                "prompt": find_meeting_times_instructions,
                "tools": [get_events_for_days],
                "middleware": [EmailAgentMiddleware()]
            }
        ],
        middleware=[
            EmailAgentMiddleware(),
            AddFileToSystemPromptMiddleware(files_to_inject=["email.txt"]),
            NotifyUserViaSlackMiddleware()
        ],
        tool_configs={
            "write_email_response": {
                "allow_accept": True,
                "allow_respond": True,
                "allow_edit": True,
                "description": "I've written an email response to the user. Please review it and make any necessary changes."
            },
            "start_new_email_thread": {
                "allow_accept": True,
                "allow_respond": True,
                "allow_edit": True,
                "description": "I've started a new email thread. Please review it and make any necessary changes."
            },
            "send_calendar_invite": {
                "allow_accept": True,
                "allow_respond": True,
                "allow_edit": True,
                "description": "I'm looking to create a calendar invite to create a meeting. Please review it and make any necessary changes."
            }
        },
        context_schema=EmailConfigSchema
    ).with_config({"recursion_limit": 1000})
    return agent

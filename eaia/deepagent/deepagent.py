from langgraph.types import interrupt, Command
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langchain.tools.tool_node import InjectedState
from langchain.agents.middleware import AgentMiddleware, ModelRequest, AgentState
from langgraph.graph.ui import AnyUIMessage, ui_message_reducer, push_ui_message
from deepagents import async_create_deep_agent    
from eaia.deepagent.google_utils import gmail_send_email, gmail_mark_as_read, google_calendar_list_events_for_date, google_calendar_create_event
from eaia.deepagent.prompts import SYSTEM_PROMPT, FIND_MEETING_TIME_SYSTEM_PROMPT, INSTRUCTIONS_PROMPT
from eaia.deepagent.types import EmailAgentState, NotifiedState, EmailConfigSchema
from eaia.deepagent.utils import generate_email_markdown, SLACK_MSG_TEMPLATE
from langchain_core.runnables import RunnableConfig
from typing import Annotated, Any, Sequence, TypedDict, Optional
import json
from slack_sdk.web.async_client import AsyncWebClient
import os
from dotenv import load_dotenv
from datetime import datetime
from langgraph.runtime import get_runtime
from langgraph.runtime import Runtime
from ai_filesystem import FilesystemClient

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
                "action_request": {"action": "Get Clarification from User", "args": {"Question": question_for_user}},
                "config": {
                    "allow_respond": True,
                    "allow_accept": False,
                    "allow_edit": False,
                    "description": description
                },
                "description": description
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
    runtime = get_runtime(EmailConfigSchema)
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
            user_email=runtime.context.email
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
    runtime = get_runtime(EmailConfigSchema)
    try:
        await gmail_send_email(
            to=",".join(recipients),
            subject=subject,
            body=content,
            user_email=runtime.context.email
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
    runtime = get_runtime(EmailConfigSchema)
    try:
        await google_calendar_create_event(
            title=event_title,
            start_time=start_time,
            end_time=end_time,
            attendee_emails=emails,
            timezone=timezone,  
            user_email=runtime.context.email
        )
    except Exception as e:
        return f"Error creating calendar event: {e}"
    return "Successfully created a calendar event"

@tool(description="Mark an email as read")
async def mark_email_as_read(
    state: Annotated[EmailAgentState, InjectedState],
):
    runtime = get_runtime(EmailConfigSchema)
    try:
        await gmail_mark_as_read(state["email"]["id"], runtime.context.email)
    except Exception as e:
        return f"Error marking email as read: {e}"  
    return "Successfully marked an email as read"

@tool(description="Search events for a day. The date str should be in `dd-mm-yyyy` format")
async def get_events_for_days(
    date_str: str,
):
    runtime = get_runtime(EmailConfigSchema)
    try:
        events = await google_calendar_list_events_for_date(date_str, runtime.context.email)
        return events
    except Exception as e:
        return f"Error getting events for day: {e}"

class EmailAgentMiddleware(AgentMiddleware):
    state_schema=EmailAgentState

    def before_model(self, agent_state: EmailAgentState, runtime: Any) -> EmailAgentState:
        # If the last message is a human message, make sure any dangling tool calls are cleaned up.
        messages = agent_state["messages"]
        if not messages or len(messages) == 0:
            return
        last_message = messages[-1]
        if last_message.type != "human":
            return
        # Iterate through all AI messages and fix dangling tool calls
        index = 0
        while index < len(messages):
            msg = messages[index]
            if msg.type == "ai" and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    has_tool_response = any(
                        m.type == "tool" and m.tool_call_id == tool_call["id"]
                        for m in messages[index + 1:]
                    )
                    if not has_tool_response:
                        messages.insert(
                            index + 1,
                            ToolMessage(
                                content=f"Before this tool call: {tool_call['name']} could be approved by the user, a follow-up came in. Please ignore this tool call, it did not execute.",
                                tool_call_id=tool_call["id"]
                            )
                        )
            index += 1
        return agent_state


class UIState(AgentState):
    ui: Annotated[Sequence[AnyUIMessage], ui_message_reducer]

class ToolGenUI(TypedDict):
    component_name: str

# NOTE: Push the UI Message in a separate middleware for now.
class GenUIMiddleware(AgentMiddleware):
    state_schema = UIState

    def __init__(self, tool_to_genui_map: dict[str, ToolGenUI]):
        self.tool_to_genui_map = tool_to_genui_map
        
    def after_model(self, state: UIState, runtime: Runtime) -> dict[str, Any] | None:
        last_message = state["messages"][-1]
        if last_message.type != "ai":
            return
        if last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                if tool_call["name"] in self.tool_to_genui_map:
                    component_name = self.tool_to_genui_map[tool_call["name"]]["component_name"]
                    push_ui_message(
                        component_name,
                        {},
                        metadata={
                            "tool_call_id": tool_call["id"]
                        },
                        message=last_message
                    )

class NotifyUserViaSlackMiddleware(AgentMiddleware):
    state_schema = NotifiedState
    async def after_model(self, state: NotifiedState, runtime: Any) -> NotifiedState | None:
        messages = state["messages"]
        notified = state["notified"] if "notified" in state else False
        if not messages or notified:
            return
        last_message = messages[-1]
        userId = runtime.context.slack_user_id
        if last_message.type != "ai" or userId is None:
            return
        tools_to_notify_on= [
            "write_email_response",
            "start_new_email_thread",
            "send_calendar_invite",
            "message_user"
        ]
        if any(tool_call["name"] in tools_to_notify_on for tool_call in last_message.tool_calls):
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

class FilesystemHydratedState(AgentState):
    filesystem_hydrated: bool = False

class WriteConfigInstructionsToFilesystemMiddleware(AgentMiddleware):
    state_schema = FilesystemHydratedState

    def before_model(self, agent_state: FilesystemHydratedState, runtime: Runtime) -> AgentState:
        # If instructions have not been written to long-term memory, write them.
        hydrated = agent_state["filesystem_hydrated"] if "filesystem_hydrated" in agent_state else False
        if not hydrated and os.getenv("LONGTERM_FILESYSTEM_NAME") and os.getenv("AGENT_FS_API_KEY"):
            filesystem_client = FilesystemClient(
                filesystem=os.getenv("LONGTERM_FILESYSTEM_NAME")
            )
            file_data_list = filesystem_client._list_files()
            if not any(file_data.path == "instructions.txt" for file_data in file_data_list):
                system_prompt = INSTRUCTIONS_PROMPT.format(
                    full_name=runtime.context.full_name,
                    name=runtime.context.name,
                    background=runtime.context.background,
                    schedule_preferences=runtime.context.schedule_preferences,
                    background_preferences=runtime.context.background_preferences,
                    triage_no=runtime.context.triage_no,
                    triage_notify=runtime.context.triage_notify,
                    triage_respond=runtime.context.triage_respond,
                    writing_preferences=runtime.context.writing_preferences,
                    timezone=runtime.context.timezone
                )
                filesystem_client.create_file(
                    "instructions.txt",
                    system_prompt
                )
        return {"filesystem_hydrated": True}

    def modify_model_request(self, model_request: ModelRequest, agent_state: FilesystemHydratedState) -> ModelRequest:
        # Get instructions from long-term memory
        if os.getenv("LONGTERM_FILESYSTEM_NAME") and os.getenv("AGENT_FS_API_KEY"):
            filesystem_client = FilesystemClient(
                filesystem=os.getenv("LONGTERM_FILESYSTEM_NAME")
            )
            instructions = filesystem_client.read_file("instructions.txt")
            model_request.system_prompt = SYSTEM_PROMPT.format(
                instructions=instructions,
                existing_system_prompt=model_request.system_prompt
            )
        return model_request


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
        instructions="",  # NOTE: This is populated by Middleware now,
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
            WriteConfigInstructionsToFilesystemMiddleware(),
            EmailAgentMiddleware(),
            NotifyUserViaSlackMiddleware(),
            GenUIMiddleware(tool_to_genui_map={
                "write_email_response": {"component_name": "write_email_response"},
                "start_new_email_thread": {"component_name": "start_new_email_thread"},
                "send_calendar_invite": {"component_name": "send_calendar_invite"},
                "get_events_for_days": {"component_name": "get_events_for_days"},
                "message_user": {"component_name": "message_user"},
                "mark_email_as_read": {"component_name": "email_marked_as_read"}
            })
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

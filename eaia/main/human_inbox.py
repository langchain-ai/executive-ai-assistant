"""Parts of the graph that require human input."""

import uuid
import os

from langsmith import traceable
from eaia.schemas import State, email_template
from langgraph.types import interrupt
from langgraph.store.base import BaseStore
from typing import TypedDict, Literal, Union, Optional
from langgraph_sdk import get_client
from eaia.main.config import get_config
from eaia.prompt_registry import (
    REWRITE_PROMPT,
    RESPONSE_PROMPT,
    BACKGROUND_PROMPT,
    CALENDAR_PROMPT,
)
from slack_sdk.web.async_client import AsyncWebClient

LGC = get_client()


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


class HumanInterruptConfig(TypedDict):
    allow_ignore: bool
    allow_respond: bool
    allow_edit: bool
    allow_accept: bool


class ActionRequest(TypedDict):
    action: str
    args: dict


class HumanInterrupt(TypedDict):
    action_request: ActionRequest
    config: HumanInterruptConfig
    description: Optional[str]


class HumanResponse(TypedDict):
    type: Literal["accept", "ignore", "response", "edit"]
    args: Union[None, str, ActionRequest]


TEMPLATE = """# {subject}

[Click here to view the email]({url})

**To**: {to}
**From**: {_from}

{page_content}
"""


def _generate_email_markdown(state: State):
    contents = state["email"]
    return TEMPLATE.format(
        subject=contents["subject"],
        url=f"https://mail.google.com/mail/u/0/#inbox/{contents['id']}",
        to=contents["to_email"],
        _from=contents["from_email"],
        page_content=contents["page_content"],
    )


async def save_email(state: State, config, store: BaseStore, status: str):
    namespace = (
        config["configurable"]["assistant_id"],
        "triage_examples",
    )
    key = state["email"]["id"]
    response = await store.aget(namespace, key)
    if response is None:
        data = {"input": state["email"], "triage": status}
        await store.aput(namespace, str(uuid.uuid4()), data)


@traceable
async def send_message(state: State, config, store):
    prompt_config = get_config(config)
    memory = prompt_config["memory"]
    user = prompt_config["name"]
    tool_call = state["messages"][-1].tool_calls[0]
    request: HumanInterrupt = {
        "action_request": {"action": tool_call["name"], "args": tool_call["args"]},
        "config": {
            "allow_ignore": True,
            "allow_respond": True,
            "allow_edit": False,
            "allow_accept": False,
        },
        "description": _generate_email_markdown(state),
    }
    response = interrupt([request])[0]
    _email_template = email_template.format(
        email_thread=state["email"]["page_content"],
        author=state["email"]["from_email"],
        subject=state["email"]["subject"],
        to=state["email"].get("to_email", ""),
    )
    if response["type"] == "response":
        msg = {
            "type": "tool",
            "name": tool_call["name"],
            "content": response["args"],
            "tool_call_id": tool_call["id"],
        }
        if memory:
            await save_email(state, config, store, "email")
            rewrite_state = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"Draft a response to this email:\n\n{_email_template}",
                    }
                ]
                + state["messages"],
                "feedback": f"{user} responded in this way: {response['args']}",
                "prompt_keys": [BACKGROUND_PROMPT.key],
                "assistant_key": config["configurable"]["assistant_id"],
            }
            await LGC.runs.create(None, "multi_reflection_graph", input=rewrite_state)
    elif response["type"] == "ignore":
        msg = {
            "role": "assistant",
            "content": "",
            "id": state["messages"][-1].id,
            "tool_calls": [
                {
                    "id": tool_call["id"],
                    "name": "Ignore",
                    "args": {"ignore": True},
                }
            ],
        }
        if memory:
            await save_email(state, config, store, "no")
    else:
        raise ValueError(f"Unexpected response: {response}")

    return {"messages": [msg]}


@traceable
async def send_email_draft(state: State, config, store):
    prompt_config = get_config(config)
    memory = prompt_config["memory"]
    user = prompt_config["name"]
    tool_call = state["messages"][-1].tool_calls[0]
    request: HumanInterrupt = {
        "action_request": {"action": tool_call["name"], "args": tool_call["args"]},
        "config": {
            "allow_ignore": True,
            "allow_respond": True,
            "allow_edit": True,
            "allow_accept": True,
        },
        "description": _generate_email_markdown(state),
    }
    response = interrupt([request])[0]
    _email_template = email_template.format(
        email_thread=state["email"]["page_content"],
        author=state["email"]["from_email"],
        subject=state["email"]["subject"],
        to=state["email"].get("to_email", ""),
    )
    if response["type"] == "response":
        msg = {
            "type": "tool",
            "name": tool_call["name"],
            "content": f"Error, {user} interrupted and gave this feedback: {response['args']}",
            "tool_call_id": tool_call["id"],
        }
        if memory:
            await save_email(state, config, store, "email")
            rewrite_state = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"Draft a response to this email:\n\n{_email_template}",
                    }
                ]
                + state["messages"],
                "feedback": f"Error, {user} interrupted and gave this feedback: {response['args']}",
                "prompt_keys": [
                    REWRITE_PROMPT.key,
                    RESPONSE_PROMPT.key,
                    BACKGROUND_PROMPT.key,
                    CALENDAR_PROMPT.key,
                ],
                "assistant_key": config["configurable"]["assistant_id"],
            }
            await LGC.runs.create(None, "multi_reflection_graph", input=rewrite_state)
    elif response["type"] == "ignore":
        msg = {
            "role": "assistant",
            "content": "",
            "id": state["messages"][-1].id,
            "tool_calls": [
                {
                    "id": tool_call["id"],
                    "name": "Ignore",
                    "args": {"ignore": True},
                }
            ],
        }
        if memory:
            await save_email(state, config, store, "no")
    elif response["type"] == "edit":
        msg = {
            "role": "assistant",
            "content": state["messages"][-1].content,
            "id": state["messages"][-1].id,
            "tool_calls": [
                {
                    "id": tool_call["id"],
                    "name": tool_call["name"],
                    "args": response["args"]["args"],
                }
            ],
        }
        if memory:
            corrected = response["args"]["args"]["content"]
            await save_email(state, config, store, "email")
            rewrite_state = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"Draft a response to this email:\n\n{_email_template}",
                    },
                    {
                        "role": "assistant",
                        "content": state["messages"][-1].tool_calls[0]["args"][
                            "content"
                        ],
                    },
                ],
                "feedback": f"A better response would have been: {corrected}",
                "prompt_keys": [
                    REWRITE_PROMPT.key,
                    RESPONSE_PROMPT.key,
                    BACKGROUND_PROMPT.key,
                    CALENDAR_PROMPT.key,
                ],
                "assistant_key": config["configurable"]["assistant_id"],
            }
            await LGC.runs.create(None, "multi_reflection_graph", input=rewrite_state)
    elif response["type"] == "accept":
        if memory:
            await save_email(state, config, store, "email")
        return None
    else:
        raise ValueError(f"Unexpected response: {response}")
    return {"messages": [msg]}


@traceable
async def notify(state: State, config, store):
    prompt_config = get_config(config)
    memory = prompt_config["memory"]
    user = prompt_config["name"]
    request: HumanInterrupt = {
        "action_request": {"action": "Notify", "args": {}},
        "config": {
            "allow_ignore": True,
            "allow_respond": True,
            "allow_edit": False,
            "allow_accept": False,
        },
        "description": _generate_email_markdown(state),
    }
    response = interrupt([request])[0]
    _email_template = email_template.format(
        email_thread=state["email"]["page_content"],
        author=state["email"]["from_email"],
        subject=state["email"]["subject"],
        to=state["email"].get("to_email", ""),
    )
    if response["type"] == "response":
        msg = {"type": "user", "content": response["args"]}
        if memory:
            await save_email(state, config, store, "email")
            rewrite_state = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"Draft a response to this email:\n\n{_email_template}",
                    }
                ]
                + state["messages"],
                "feedback": f"{user} gave these instructions: {response['args']}",
                "prompt_keys": [
                    RESPONSE_PROMPT.key,
                    BACKGROUND_PROMPT.key,
                    CALENDAR_PROMPT.key,
                ],
                "assistant_key": config["configurable"]["assistant_id"],
            }
            await LGC.runs.create(None, "multi_reflection_graph", input=rewrite_state)
    elif response["type"] == "ignore":
        msg = {
            "role": "assistant",
            "content": "",
            "id": str(uuid.uuid4()),
            "tool_calls": [
                {
                    "id": "foo",
                    "name": "Ignore",
                    "args": {"ignore": True},
                }
            ],
        }
        if memory:
            await save_email(state, config, store, "no")
    else:
        raise ValueError(f"Unexpected response: {response}")

    return {"messages": [msg]}


@traceable
async def send_cal_invite(state: State, config, store):
    prompt_config = get_config(config)
    memory = prompt_config["memory"]
    user = prompt_config["name"]
    tool_call = state["messages"][-1].tool_calls[0]
    request: HumanInterrupt = {
        "action_request": {"action": tool_call["name"], "args": tool_call["args"]},
        "config": {
            "allow_ignore": True,
            "allow_respond": True,
            "allow_edit": True,
            "allow_accept": True,
        },
        "description": _generate_email_markdown(state),
    }
    response = interrupt([request])[0]
    _email_template = email_template.format(
        email_thread=state["email"]["page_content"],
        author=state["email"]["from_email"],
        subject=state["email"]["subject"],
        to=state["email"].get("to_email", ""),
    )
    if response["type"] == "response":
        msg = {
            "type": "tool",
            "name": tool_call["name"],
            "content": f"Error, {user} interrupted and gave this feedback: {response['args']}",
            "tool_call_id": tool_call["id"],
        }
        if memory:
            await save_email(state, config, store, "email")
            rewrite_state = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"Draft a response to this email:\n\n{_email_template}",
                    }
                ]
                + state["messages"],
                "feedback": f"{user} interrupted gave these instructions: {response['args']}",
                "prompt_keys": [
                    RESPONSE_PROMPT.key,
                    BACKGROUND_PROMPT.key,
                    CALENDAR_PROMPT.key,
                ],
                "assistant_key": config["configurable"]["assistant_id"],
            }
            await LGC.runs.create(None, "multi_reflection_graph", input=rewrite_state)
    elif response["type"] == "ignore":
        msg = {
            "role": "assistant",
            "content": "",
            "id": state["messages"][-1].id,
            "tool_calls": [
                {
                    "id": tool_call["id"],
                    "name": "Ignore",
                    "args": {"ignore": True},
                }
            ],
        }
        if memory:
            await save_email(state, config, store, "no")
    elif response["type"] == "edit":
        msg = {
            "role": "assistant",
            "content": state["messages"][-1].content,
            "id": state["messages"][-1].id,
            "tool_calls": [
                {
                    "id": tool_call["id"],
                    "name": tool_call["name"],
                    "args": response["args"]["args"],
                }
            ],
        }
        if memory:
            await save_email(state, config, store, "email")
            rewrite_state = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"Draft a response to this email:\n\n{_email_template}",
                    }
                ]
                + state["messages"],
                "feedback": f"{user} interrupted gave these instructions: {response['args']}",
                "prompt_keys": [
                    RESPONSE_PROMPT.key,
                    BACKGROUND_PROMPT.key,
                    CALENDAR_PROMPT.key,
                ],
                "assistant_key": config["configurable"]["assistant_id"],
            }
            await LGC.runs.create(None, "multi_reflection_graph", input=rewrite_state)
    elif response["type"] == "accept":
        if memory:
            await save_email(state, config, store, "email")
        return None
    else:
        raise ValueError(f"Unexpected response: {response}")

    return {"messages": [msg]}

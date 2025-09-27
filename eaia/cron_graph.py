import hashlib
import operator
import uuid
from typing import Annotated, TypedDict

import httpx
import langsmith as ls
from langgraph.graph import END, START, StateGraph
from langgraph_sdk import get_client
from langchain_core.messages import HumanMessage
from eaia.gmail import fetch_group_emails
from eaia.main.config import get_config
from eaia.deepagent.utils import FILE_TEMPLATE
from dotenv import load_dotenv
load_dotenv("../.env")

client = get_client()


class JobKickoff(TypedDict):
    minutes_since: int
    assistant_id: str
    count: Annotated[int, operator.add]


async def main(state: JobKickoff, config):
    minutes_since: int = state["minutes_since"]
    print(config)
    email = get_config(config)["email"]
    assistant_id = state["assistant_id"]
    # TODO: This really should be async
    count = 0
    async for email in fetch_group_emails(
        email, minutes_since=minutes_since, assistant_id=assistant_id
    ):
        thread_id = str(
            uuid.UUID(hex=hashlib.md5(email["thread_id"].encode("UTF-8")).hexdigest())
        )
        async with ls.trace(
            "Schedule processing",
            inputs={"thread_id": thread_id},
            metadata={"assistant_id": assistant_id, "email": email},
        ) as rt:
            try:
                thread_info = await client.threads.get(thread_id)
            except httpx.HTTPStatusError as e:
                if "user_respond" in email:
                    rt.metadata["end_reason"] = "user_respond"
                    continue
                if e.response.status_code == 404:
                    thread_info = await client.threads.create(
                        thread_id=thread_id, if_exists="do_nothing"
                    )
                else:
                    rt.metadata["end_reason"] = "unknown_error"
                    rt.error = str(e)
                    raise e
            if "user_respond" in email:
                rt.metadata["end_reason"] = "user_respond"
                await client.threads.update_state(thread_id, None, as_node="__end__")
                continue
            recent_email = thread_info["metadata"].get("email_id")
            if recent_email == email["id"]:
                print(f"Duplicate email: {email}")
                rt.metadata["end_reason"] = "duplicate"
                continue
            await client.threads.update(thread_id, metadata={"email_id": email["id"]})
            rt.metadata["end_reason"] = "success"
            rt.add_outputs({"email": email})
            count += 1

            # Pass in email through the filesystem as well as state
            email_str = FILE_TEMPLATE.format(
                id=email["id"],
                thread_id=email["thread_id"],
                send_time=email["send_time"],
                subject=email["subject"],
                to=email["to_email"],
                _from=email["from_email"],
                page_content=email["page_content"],
            )
            await client.runs.create(
                thread_id,
                assistant_id,
                input={
                    "email": email,
                    "messages": HumanMessage(content="Decide what the best actions are, and handle this new email that just came in."),
                    "files": {
                        "email.txt": email_str
                    }
                },
                multitask_strategy="rollback",
                config={"configurable": {"email": email["to_email"]}, "recursion_limit": 1000},
            )

    return {"count": count}

class EmailConfig:
    email: str

graph = StateGraph(JobKickoff, EmailConfig)
graph.add_node(main)
graph.add_edge(START, "main")
graph.add_edge("main", END)
graph = graph.compile()

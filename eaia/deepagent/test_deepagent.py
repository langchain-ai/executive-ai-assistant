from dotenv import load_dotenv
from eaia.deepagent.deepagent import agent
from langgraph.types import Command
import uuid

load_dotenv("../.env")

config = {"configurable": {"thread_id": uuid.uuid4()}}

async def main():
    await agent.ainvoke({
        "email": {
            "id": "19982d57fe3c5fa0",
            "thread_id": "1234",
            "from_email": "truffulatree2500@gmail.com",
            "subject": "Testing",
            "page_content": "Hey Nick, I need direct feedback from you. I’d like to discuss the latest project related to deepagents and how it will affect the future of our company.",
            "send_time": "2:10pm",
            "to_email": "nick@langchain.dev"
        },
        "messages": [
            {
            "content": "Decide what the best actions are, and handle this new email that just came in.",
            "type": "human"
            }
        ],
        "files": {
            "email.txt": "Hey Nick, I need direct feedback from you. I’d like to discuss the latest project related to deepagents and how it will affect the future of our company."
        }
    }, config=config)

    await agent.ainvoke(
        Command(resume=[{
            "args": "Yes I am familiar with it, tell him that I will call him later tonight on my phone, don't schedule a meeting.",
            "type": "response"
        }]),
        config=config
    )

    await agent.ainvoke(
        Command(resume=[{
            "args": "Actually, give him my phone number too, 7347569569, and tell him to call me anytime he is free.",
            "type": "response"
        }]),
        config=config
    )

    response = await agent.ainvoke(
        Command(resume=[{"args": "","type": "accept"}]),
        config=config
    )
    print(response)

import asyncio
# from slack_sdk.web.async_client import AsyncWebClient
# import os

# async def send_slack_msg():
#     userId = os.environ["SLACK_USER_ID"]
#     client = AsyncWebClient(token=os.environ["SLACK_BOT_TOKEN"])
#     response = await client.conversations_open(users=[userId])
#     print(response)
#     channel_id = response["channel"]["id"]

#     response2 = await client.chat_postMessage(
#         channel=channel_id,
#         text="Sample msg",
#     )
#     print(response2)

if __name__ == "__main__":
    asyncio.run(main())
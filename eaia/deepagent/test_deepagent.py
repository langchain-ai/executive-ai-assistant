from dotenv import load_dotenv
from eaia.deepagent.deepagent import agent
from langgraph.types import Command
import uuid
from langgraph_sdk import get_client
import asyncio

load_dotenv("../.env")


THREAD_ID = "c84af348-21b9-4de5-f49f-4e0ec2518890"

async def main():
    client = get_client()
    response = client.runs.create(
        THREAD_ID,
        "assistant_id",
        input={},
        config={},
    )
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
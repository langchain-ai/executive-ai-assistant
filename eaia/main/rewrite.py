"""Agent responsible for rewriting the email in a better tone."""

from langchain_openai import ChatOpenAI

from eaia.schemas import State, ReWriteEmail

from eaia.prompt_registry import registry, REWRITE_PROMPT
from langchain_core.runnables import RunnableConfig


rewrite_prompt_system = """You job is to rewrite an email draft to sound more like {name}.

Here is the email thread:

From: {author}
To: {to}
Subject: {subject}

{email_thread}"""

rewrite_prompt_human = """{name}'s assistant just drafted an email. See above.

It is factually correct, but it may not sound like {name}. \
Your job is to rewrite the email keeping the information the same (do not add anything that is made up!) \
but adjusting the tone. 

{instructions}"""


@registry.with_prompts(
    [
        REWRITE_PROMPT,
    ]
)
async def rewrite(state: State, config: RunnableConfig):
    model = config["configurable"].get("model", "o3-mini")
    llm = ChatOpenAI(model=model, temperature=0)
    prev_message = state["messages"][-1]
    draft = prev_message.tool_calls[0]["args"]["content"]
    system_message = rewrite_prompt_system.format(
        email_thread=state["email"]["page_content"],
        author=state["email"]["from_email"],
        subject=state["email"]["subject"],
        to=state["email"]["to_email"],
        name=config["configurable"]["name"],
    )
    human_message = rewrite_prompt_human.format(
        instructions=registry.prompts[REWRITE_PROMPT.key].value,
        name=config["configurable"]["name"],
    )
    model = llm.with_structured_output(ReWriteEmail)
    messages = [{"role": "system", "content": system_message}] + state['messages'] + [
        {"role": "tool", "content": "Sent for human review", "tool_call_id": prev_message.tool_calls[0]['id']},
        {"role": "user", "content": human_message}
    ]
    response = await model.ainvoke(messages)
    tool_calls = [
        {
            "id": prev_message.tool_calls[0]["id"],
            "name": prev_message.tool_calls[0]["name"],
            "args": {
                **prev_message.tool_calls[0]["args"],
                **{"content": response.rewritten_content},
            },
        }
    ]
    prev_message = {
        "role": "assistant",
        "id": prev_message.id,
        "content": prev_message.content,
        "tool_calls": tool_calls,
    }
    return {"messages": [prev_message]}

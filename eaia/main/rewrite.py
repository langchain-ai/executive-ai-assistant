"""Agent responsible for rewriting the email in a better tone."""

from langchain_openai import ChatOpenAI

from eaia.schemas import State, ReWriteEmail

from eaia.prompt_registry import registry, REWRITE_PROMPT
from langchain_core.runnables import RunnableConfig


rewrite_prompt = """You job is to rewrite an email draft to sound more like {name}.

{name}'s assistant just drafted an email. It is factually correct, but it may not sound like {name}. \
Your job is to rewrite the email keeping the information the same (do not add anything that is made up!) \
but adjusting the tone. 

{instructions}

Here is the assistant's current draft:

<draft>
{draft}
</draft>

Here is the email thread:

From: {author}
To: {to}
Subject: {subject}

{email_thread}"""


@registry.with_prompts(
    [
        REWRITE_PROMPT,
    ]
)
async def rewrite(state: State, config: RunnableConfig):
    model = config["configurable"].get("model", "gpt-4o")
    llm = ChatOpenAI(model=model, temperature=0)
    prev_message = state["messages"][-1]
    draft = prev_message.tool_calls[0]["args"]["content"]
    input_message = rewrite_prompt.format(
        email_thread=state["email"]["page_content"],
        author=state["email"]["from_email"],
        subject=state["email"]["subject"],
        to=state["email"]["to_email"],
        draft=draft,
        instructions=registry.prompts[REWRITE_PROMPT.key].value,
        name=config["configurable"]["name"],
    )
    model = llm.with_structured_output(ReWriteEmail)
    response = await model.ainvoke(input_message)
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

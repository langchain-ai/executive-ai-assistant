from langgraph.store.base import BaseStore
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.types import Command, Send

TONE_INSTRUCTIONS = "Only update the prompt to include instructions on the **style and tone and format** of the response. Do NOT update the prompt to include anything about the actual content - only the style and tone and format. The user sometimes responds differently to different types of people - take that into account, but don't be too specific."
RESPONSE_INSTRUCTIONS = "Only update the prompt to include instructions on the **content** of the response. Do NOT update the prompt to include anything about the tone or style or format of the response."
SCHEDULE_INSTRUCTIONS = "Only update the prompt to include instructions on how to send calendar invites - eg when to send them, what title should be, length, time of day, etc"
BACKGROUND_INSTRUCTIONS = "Only update the propmpt to include pieces of information that are relevant to being the user's assistant. Do not update the instructions to include anything about the tone of emails sent, when to send calendar invites. Examples of good things to include are (but are not limited to): people's emails, addresses, etc."


def get_trajectory_clean(messages):
    response = []
    for m in messages:
        response.append(m.pretty_repr())
    return "\n".join(response)


class ReflectionState(MessagesState):
    feedback: Optional[str]
    prompt_key: str
    assistant_key: str
    instructions: str


class GeneralResponse(TypedDict):
    logic: str
    update_prompt: bool
    new_prompt: str


general_reflection_prompt = """You are helping an AI agent improve. You can do this by changing their system prompt.

These is their current prompt:
<current_prompt>
{current_prompt}
</current_prompt>

Here was the agent's trajectory:
<trajectory>
{trajectory}
</trajectory>

Here is the user's feedback:

<feedback>
{feedback}
</feedback>

Here are instructions for updating the agent's prompt:

<instructions>
{instructions}
</instructions>


Based on this, return an updated prompt

You should return the full prompt, so if there's anything from before that you want to include, make sure to do that. Feel free to override or change anything that seems irrelevant. You do not need to update the prompt - if you don't want to, just return `update_prompt = False` and an empty string for new prompt."""


async def update_general(state: ReflectionState, config, store: BaseStore):
    reflection_model = ChatOpenAI(model="o1", disable_streaming=True)
    # reflection_model = ChatAnthropic(model="claude-3-5-sonnet-latest")
    user_id = config["configurable"]["langgraph_auth_user_id"]
    namespace = (
        user_id,
        state["assistant_key"],
    )
    key = state["prompt_key"]
    result = await store.aget(namespace, key)

    async def get_output(messages, current_prompt, feedback, instructions):
        trajectory = get_trajectory_clean(messages)
        prompt = general_reflection_prompt.format(
            current_prompt=current_prompt,
            trajectory=trajectory,
            feedback=feedback,
            instructions=instructions,
        )
        _output = await reflection_model.with_structured_output(
            GeneralResponse, method="json_schema"
        ).ainvoke(prompt)
        return _output

    output = await get_output(
        state["messages"],
        result.value["data"],
        state["feedback"],
        state["instructions"],
    )
    if output["update_prompt"]:
        await store.aput(namespace, key, {"data": output["new_prompt"]}, index=False)


general_reflection_graph = StateGraph(ReflectionState)
general_reflection_graph.add_node(update_general)
general_reflection_graph.add_edge(START, "update_general")
general_reflection_graph.add_edge("update_general", END)
general_reflection_graph = general_reflection_graph.compile()

MEMORY_TO_UPDATE = {
    "tone": "Instruction about the tone and style and format of the resulting email. Update this if you learn new information about the tone in which the user likes to respond that may be relevant in future emails.",
    "background": "Background information about the user. Update this if you learn new information about the user that may be relevant in future emails",
    "email": "Instructions about the type of content to be included in email. Update this if you learn new information about how the user likes to respond to emails (not the tone, and not information about the user, but specifically about how or when they like to respond to emails) that may be relevant in the future.",
    "calendar": "Instructions about how to send calendar invites (including title, length, time, etc). Update this if you learn new information about how the user likes to schedule events that may be relevant in future emails.",
}
MEMORY_TO_UPDATE_KEYS = {
    "tone": "rewrite_instructions",
    "background": "random_preferences",
    "email": "response_preferences",
    "calendar": "schedule_preferences",
}
MEMORY_TO_UPDATE_INSTRUCTIONS = {
    "tone": TONE_INSTRUCTIONS,
    "background": BACKGROUND_INSTRUCTIONS,
    "email": RESPONSE_INSTRUCTIONS,
    "calendar": SCHEDULE_INSTRUCTIONS,
}

CHOOSE_MEMORY_PROMPT = """You are helping an AI agent improve. You can do this by changing prompts.

Here was the agent's trajectory:
<trajectory>
{trajectory}
</trajectory>

Here is the user's feedback:

<feedback>
{feedback}
</feedback>

These are the different types of prompts that you can update in order to change their behavior:

<types_of_prompts>
{types_of_prompts}
</types_of_prompts>

Please choose the types of prompts that are worth updating based on this trajectory + feedback. Only do this if the feedback seems like it has info relevant to the prompt. You will update the prompts themselves in a separate step. You do not have to update any memory types if you don't want to! Just leave it empty."""


class MultiMemoryInput(MessagesState):
    prompt_types: list[str]
    feedback: str
    assistant_key: str


async def determine_what_to_update(state: MultiMemoryInput):
    reflection_model = ChatOpenAI(model="gpt-4o", disable_streaming=True)
    reflection_model = ChatAnthropic(model="claude-3-5-sonnet-latest")
    trajectory = get_trajectory_clean(state["messages"])
    types_of_prompts = "\n".join(
        [f"`{p_type}`: {MEMORY_TO_UPDATE[p_type]}" for p_type in state["prompt_types"]]
    )
    prompt = CHOOSE_MEMORY_PROMPT.format(
        trajectory=trajectory,
        feedback=state["feedback"],
        types_of_prompts=types_of_prompts,
    )

    class MemoryToUpdate(TypedDict):
        memory_types_to_update: list[str]

    response = reflection_model.with_structured_output(MemoryToUpdate).invoke(prompt)
    sends = []
    for t in response["memory_types_to_update"]:
        _state = {
            "messages": state["messages"],
            "feedback": state["feedback"],
            "prompt_key": MEMORY_TO_UPDATE_KEYS[t],
            "assistant_key": state["assistant_key"],
            "instructions": MEMORY_TO_UPDATE_INSTRUCTIONS[t],
        }
        send = Send("reflection", _state)
        sends.append(send)
    return Command(goto=sends)


# Done so this can run in parallel
async def call_reflection(state: ReflectionState):
    await general_reflection_graph.ainvoke(state)


multi_reflection_graph = StateGraph(MultiMemoryInput)
multi_reflection_graph.add_node(determine_what_to_update)
multi_reflection_graph.add_node("reflection", call_reflection)
multi_reflection_graph.add_edge(START, "determine_what_to_update")
multi_reflection_graph = multi_reflection_graph.compile()

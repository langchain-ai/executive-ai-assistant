import asyncio

from langgraph.graph import MessagesState
from langgraph.store.base import BaseStore
from langmem import (
    AnyMessage,
    Prompt,
    create_multi_prompt_optimizer,
    create_memory_store_enricher,
)
from langgraph.func import task
from langgraph.graph import StateGraph
from eaia.prompt_registry import registry, BACKGROUND_PROMPT


class MultiMemoryInput(MessagesState):
    feedback: str
    assistant_key: str
    prompt_keys: list[str]


optimizer = create_multi_prompt_optimizer(
    "claude-3-5-sonnet-latest", kind="prompt_memory"
)


@task()
async def optimize(messages: list[tuple[list, str]], prompts: list[Prompt]):
    return await optimizer(messages, prompts)


@task()
async def manage_semantic_memory_for_prompt(
    messages: list[AnyMessage],
    feedback: str | None,
    prompt: Prompt,
    assistant_key: str,
):
    prompt_name = prompt.get("name", "")
    instructions = f"""You are managing memory for an autonomous agent. Extract memories and patterns from its experiences that would be valuable for future decisions.
Extract information that captures both what happened and why it's significant. Include sufficient context, relationships, time, etc. about when and how each memory would be relevant to ensure it can be used independently, but exclude irrelevant details.
Avoid duplication. Prefer contextualizing existing memories with new information to creating new ones. Create new ones when new concepts or events are encountered.

The agent you are managing is called \"{prompt_name}\" and has the following instructions:\n\n<agent_instructions>\n{prompt["prompt"]}\n</agent_instructions>"""
    processor = create_memory_store_enricher(
        "claude-3-5-sonnet-latest",
        instructions=instructions,
        schemas=None,
        enable_inserts=True,
        query_model="openai:gpt-4o-mini",
        namespace_prefix=(
            assistant_key,
            "semantic",
            prompt_name,
        ),
    )
    conversation = messages + [
        {
            "role": "user",
            "content": f"Reflect on the above interaction to update your memories. First think about what ought to be deleted, what ought to be merged/consolidated, and what ought to be created. Once you're done thinking, make the required changes.\n\nFeedback from the developer:\n\n{feedback}",
        }
    ]

    await processor(conversation)


async def multi_reflection_node(state: MultiMemoryInput, store: BaseStore):
    assistant_key = state.get("assistant_key") or "default"
    namespace = (assistant_key,)
    prompt_keys = state.get("prompt_keys", [])
    if not prompt_keys:
        return
    memories_to_update = {
        k: v for k, v in registry.registered.items() if k in prompt_keys
    }
    prompt_items = await asyncio.gather(
        *[store.aget(namespace, prompt.key) for prompt in memories_to_update.values()]
    )
    prompts = [
        Prompt(
            name=prompt.key,  # we're just using the key always now
            prompt=prompt_item.value["data"] or "" if prompt_item is not None else "",
            update_instructions=f"{prompt.key}: {prompt.instructions}",
            when_to_update=prompt.when_to_update,
        )
        for prompt, prompt_item in zip(memories_to_update.values(), prompt_items)
    ]
    coros = [
        optimize(
            [(state["messages"], state.get("feedback", ""))],
            prompts,
        )
    ]
    if background_prompt := (
        next((p for p in prompts if p["name"] == BACKGROUND_PROMPT.key), None)
    ):
        coros.append(
            manage_semantic_memory_for_prompt(
                state["messages"],
                state.get("feedback", ""),
                background_prompt,
                assistant_key,
            )
        )

    updated_prompts, *_ = await asyncio.gather(*coros)
    to_save = [
        p for i, p in enumerate(updated_prompts) if prompts[i]["prompt"] != p["prompt"]
    ]
    await asyncio.gather(
        *(
            store.aput(
                namespace,
                p["name"],
                {"data": p["prompt"]},
            )
            for p in to_save
        )
    )


multi_reflection_graph = (
    StateGraph(MultiMemoryInput)
    .add_node(multi_reflection_node)
    .add_edge("__start__", "multi_reflection_node")
    .compile()
)

from typing import NamedTuple, Callable, TypeVar, Any, Sequence
import functools
from contextvars import ContextVar
from langgraph.utils.config import get_store, get_config
from langgraph.store.base import BaseStore
import asyncio


class ConfigurablePrompt(NamedTuple):
    name: str
    key: str
    when_to_update: str
    instructions: str


class ConfiguredPrompt(NamedTuple):
    name: str
    key: str
    when_to_update: str
    instructions: str
    value: str


_used_prompts: ContextVar[dict[str, ConfiguredPrompt] | None] = ContextVar(
    "used_prompts", default=None
)

F = TypeVar("F", bound=Callable)


class Registry:
    __slots__ = ("registered",)

    def __init__(
        self,
        prompts: Sequence[ConfigurablePrompt] | None = None,
    ) -> None:
        self.registered: dict[str, ConfigurablePrompt] = {}
        if prompts is not None:
            self.register(prompts)

    def register(
        self,
        prompts: ConfigurablePrompt | Sequence[ConfigurablePrompt],
    ) -> list[str]:
        keys = []
        if isinstance(prompts, dict | ConfigurablePrompt):
            prompts = [prompts]

        for prompt in prompts:
            if isinstance(prompt, str):
                keys.append(prompt)
            else:
                if isinstance(prompt, dict):
                    prompt = ConfigurablePrompt(**prompt)
                keys.append(prompt.key)
                self.registered[prompt.key] = prompt
        return keys

    def with_prompts(
        self,
        prompts: str | ConfigurablePrompt | Sequence[ConfigurablePrompt | str],
        /,
    ) -> Callable[[F], F]:
        if isinstance(prompts, str | ConfigurablePrompt | dict):
            prompts = [prompts]
        keys = [prompt if isinstance(prompt, str) else prompt.key for prompt in prompts]
        missing = [key for key in keys if key not in self.registered]
        if missing:
            raise ValueError(f"Prompts {missing} not registered")

        def decorator(func: F) -> F:
            try:
                prompts_: dict[str, ConfigurablePrompt] = {
                    key: self.registered[key] for key in keys
                }
            except KeyError as e:
                raise ValueError(f"Prompt {e.args[0]} never registered")

            async def get_or_set_value(
                store: BaseStore, configurable: dict, namespace: tuple, key: str
            ):
                result = await store.aget(namespace, key)
                if result and "data" in result.value:
                    value = result.value["data"]
                else:
                    await store.aput(
                        namespace, key, {"data": configurable.get(key, "")}
                    )
                    value = configurable[key]
                return value

            @functools.wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                store = get_store()
                configurable = get_config().get("configurable", {})
                namespace = (configurable["assistant_id"],)
                results = await asyncio.gather(
                    *(
                        get_or_set_value(
                            store,
                            configurable,
                            namespace,
                            prompt.key,
                        )
                        for prompt in prompts_.values()
                    )
                )
                prompts = _used_prompts.set(
                    {
                        prompt.key: ConfiguredPrompt(
                            *prompt,
                            value=result,
                        )
                        for result, prompt in zip(results, prompts_.values())
                    }
                )
                try:
                    return await func(*args, **kwargs)
                finally:
                    _used_prompts.reset(prompts)

            return wrapper  # type: ignore

        return decorator

    @property
    def prompts(self) -> dict[str, ConfiguredPrompt]:
        """Get the current prompt from context."""
        current = _used_prompts.get()
        if current is None:
            raise RuntimeError(
                "No prompt context found. Use @registry.with_prompt decorator."
            )
        return current

    def __repr__(self) -> str:
        return f"Registry({self.registered})"


REWRITE_PROMPT = ConfigurablePrompt(
    name="tone",
    key="rewrite_instructions",
    when_to_update=(
        "Only update the prompt to include instructions on the **style and tone and format** of the response."
        " Do NOT update the prompt to include anything about the actual content - only the style and tone and format."
        " the user sometimes responds differently to different types of people - take that into account, but don't be too specific."
    ),
    instructions="Instruction about the tone and style and format of the resulting email. "
    "Update this if you learn new information about the tone in which the user likes to respond that may be relevant in future emails.",
)
BACKGROUND_PROMPT = ConfigurablePrompt(
    name="background",
    key="background_preferences",
    when_to_update=(
        "Only update the prompt to include pieces of information that are relevant to being the user's assistant."
        " Do not update the instructions to include anything about the tone of emails sent, "
        "when to send calendar invites. Examples of good things to include are (but are not limited to):"
        " people's emails, addresses, etc."
    ),
    instructions="Background information about the user or LangChain. Update this if you learn new information about the user that may be relevant in future emails",
)
RESPONSE_PROMPT = ConfigurablePrompt(
    name="email",
    key="response_preferences",
    when_to_update=(
        "Only update the prompt to include instructions on the **content** of the response. Do NOT update the prompt to include anything about the tone or style or format of the response."
    ),
    instructions="Instructions about the type of content to be included in email. Update this if you learn new information about how the user likes to respond to emails (not the tone, and not information about the user, but specifically about how or when he likes to respond to emails) that may be relevant in the future.",
)
CALENDAR_PROMPT = ConfigurablePrompt(
    name="calendar",
    key="schedule_preferences",
    when_to_update=(
        "Only update the prompt to include instructions on how to send calendar invites - eg when to send them, what title should be, length, time of day, etc"
    ),
    instructions="Instructions about how to send calendar invites (including title, length, time, etc). Update this if you learn new information about how the user likes to schedule events that may be relevant in future emails.",
)
registry = Registry(
    [REWRITE_PROMPT, BACKGROUND_PROMPT, RESPONSE_PROMPT, CALENDAR_PROMPT]
)

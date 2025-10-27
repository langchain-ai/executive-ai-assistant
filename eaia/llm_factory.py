"""
LLM Factory Module
Provides a centralized way to create LLM instances based on provider configuration.
Supports OpenAI, Google Gemini, and Anthropic Claude.
"""

import os
from typing import Optional, Any
from langchain_core.language_models.chat_models import BaseChatModel


def get_llm_provider() -> str:
    """
    Get the configured LLM provider from environment variable.

    Returns:
        str: Provider name ('openai', 'gemini', or 'anthropic'). Defaults to 'gemini'.
    """
    return os.getenv("LLM_PROVIDER", "gemini").lower()


def get_llm(
    model: Optional[str] = None,
    temperature: float = 0,
    provider: Optional[str] = None,
    **kwargs: Any
) -> BaseChatModel:
    """
    Create an LLM instance based on the configured provider.

    Args:
        model: Model name. If None, uses provider default.
        temperature: Temperature for generation (0-1).
        provider: Override the default provider ('openai', 'gemini', or 'anthropic').
        **kwargs: Additional provider-specific parameters.

    Returns:
        BaseChatModel: Configured LLM instance.

    Environment Variables:
        LLM_PROVIDER: Default provider to use (default: 'gemini')
        GEMINI_API_KEY or GOOGLE_API_KEY: For Google Gemini
        OPENAI_API_KEY: For OpenAI
        ANTHROPIC_API_KEY: For Anthropic Claude

    Examples:
        >>> # Use default provider (Gemini)
        >>> llm = get_llm()

        >>> # Use specific model
        >>> llm = get_llm(model="gemini-1.5-pro")

        >>> # Override provider
        >>> llm = get_llm(provider="openai", model="gpt-4o")
    """
    if provider is None:
        provider = get_llm_provider()

    if provider == "gemini" or provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        # Map common model names to Gemini equivalents
        model_mapping = {
            "gpt-4o": "gemini-1.5-pro",
            "gpt-4": "gemini-1.5-pro",
            "gpt-3.5-turbo": "gemini-1.5-flash",
            "o1": "gemini-1.5-pro",  # o1 is used for reasoning, map to pro
            "claude-3-5-sonnet-latest": "gemini-1.5-pro",
        }

        if model is None:
            model = "gemini-1.5-pro"
        elif model in model_mapping:
            model = model_mapping[model]

        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            **kwargs
        )

    elif provider == "openai":
        from langchain_openai import ChatOpenAI

        if model is None:
            model = "gpt-4o"

        return ChatOpenAI(
            model=model,
            temperature=temperature,
            **kwargs
        )

    elif provider == "anthropic" or provider == "claude":
        from langchain_anthropic import ChatAnthropic

        if model is None:
            model = "claude-3-5-sonnet-latest"

        return ChatAnthropic(
            model=model,
            temperature=temperature,
            **kwargs
        )

    else:
        raise ValueError(
            f"Unknown LLM provider: {provider}. "
            f"Supported providers: 'gemini', 'openai', 'anthropic'"
        )


def get_reasoning_llm(**kwargs: Any) -> BaseChatModel:
    """
    Get an LLM optimized for reasoning tasks (used in reflection/learning).

    For Gemini: Uses gemini-1.5-pro with thinking mode
    For OpenAI: Uses o1 model
    For Anthropic: Uses claude-3-5-sonnet-latest

    Args:
        **kwargs: Additional provider-specific parameters.

    Returns:
        BaseChatModel: Configured reasoning LLM.
    """
    provider = get_llm_provider()

    if provider == "gemini" or provider == "google":
        # Gemini 1.5 Pro is good for reasoning
        return get_llm(model="gemini-1.5-pro", temperature=0, **kwargs)
    elif provider == "openai":
        # OpenAI o1 is specialized for reasoning
        return get_llm(provider="openai", model="o1", **kwargs)
    elif provider == "anthropic" or provider == "claude":
        # Claude Sonnet is good for reasoning
        return get_llm(provider="anthropic", model="claude-3-5-sonnet-latest", **kwargs)
    else:
        # Fallback to default LLM
        return get_llm(**kwargs)

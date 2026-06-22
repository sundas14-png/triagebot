"""LLM factory.

Builds the chat model from environment configuration. Centralised here so the
router, drafter, and judge all share one consistent, env-driven setup.
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from ..config import MODEL_NAME, OPENAI_BASE_URL, require_api_key


def make_llm(temperature: float = 0.2, streaming: bool = False) -> ChatOpenAI:
    """Return a configured ChatOpenAI instance.

    The API key is read from the environment via ``require_api_key`` and is
    never hard-coded.
    """
    kwargs = {
        "model": MODEL_NAME,
        "temperature": temperature,
        "streaming": streaming,
        "api_key": require_api_key(),
    }
    if OPENAI_BASE_URL:
        kwargs["base_url"] = OPENAI_BASE_URL
    return ChatOpenAI(**kwargs)

"""
STARK — Fast Mode
Direct LLM call with zero orchestration overhead.
Best for: greetings, simple questions, quick lookups.
Target latency: < 3 seconds.
"""
from __future__ import annotations

from muktiverse.llm.ollama import OllamaProvider
from muktiverse.schemas.llm import LLMRequest, LLMMessage
from muktiverse.logging import get_logger

logger = get_logger(__name__)

FAST_SYSTEM_PROMPT = """You are STARK, a sharp and direct AI assistant.
In Fast mode, give concise, accurate responses.
- Skip lengthy preamble or disclaimers.
- Answer directly and confidently.
- Use bullet points for lists, code blocks for code.
- If a question is ambiguous, answer the most likely interpretation.
"""


async def run_fast(
    message: str,
    model: str = "qwen3.5:4b",
    max_tokens: int = 1024,
    temperature: float = 0.7,
) -> str:
    """
    Execute in Fast mode: single direct Ollama call, no agents.

    Args:
        message:     The user's message.
        model:       Ollama model tag.
        max_tokens:  Maximum tokens to generate.
        temperature: Sampling temperature.

    Returns:
        The model's response as a plain string.
    """
    provider = OllamaProvider()

    request = LLMRequest(
        messages=[
            LLMMessage(role="system", content=FAST_SYSTEM_PROMPT),
            LLMMessage(role="user", content=message),
        ],
        model=model,
        provider="ollama",
        max_tokens=max_tokens,
        temperature=temperature,
    )

    logger.debug("fast_mode.calling_ollama", model=model, preview=message[:60])
    response = await provider.complete(request)
    logger.debug("fast_mode.complete", tokens=response.usage.total_tokens, latency=response.latency_ms)

    return response.content

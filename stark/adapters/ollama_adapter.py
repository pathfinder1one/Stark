"""
STARK — Ollama Adapter
Configures MuktiVerse to use Ollama (qwen3.5:4b) as the sole local LLM backend.
"""
from __future__ import annotations

import httpx

from muktiverse import configure, MuktiVerseConfig
from muktiverse.llm.ollama import OllamaProvider
from muktiverse.logging import get_logger

logger = get_logger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
STARK_DEFAULT_MODEL = "qwen3.5:4b"


def configure_ollama(
    model: str = STARK_DEFAULT_MODEL,
    base_url: str = OLLAMA_BASE_URL,
    timeout: int = 600,
) -> MuktiVerseConfig:
    """
    Configure MuktiVerse to route all LLM calls through Ollama.

    This is the single entry point that bootstraps STARK's LLM layer.
    Call this once at startup before creating any engine or agent.

    Args:
        model:    Ollama model tag (default: qwen3.5:4b)
        base_url: Ollama server URL  (default: http://localhost:11434)
        timeout:  Request timeout in seconds

    Returns:
        The active MuktiVerseConfig instance.
    """
    config = configure(
        # Primary provider
        default_provider="ollama",
        ollama_url=base_url,
        ollama_model=model,

        # Orchestrator + Judge also use Ollama
        orchestrator_provider="ollama",
        orchestrator_model=model,
        judge_provider="ollama",
        judge_model=model,

        # No cloud fallbacks in local mode
        openai_api_key="",
        anthropic_api_key="",
        groq_api_key="",
        gemini_api_key="",

        # Vector store in memory (no external DB needed for V1)
        vector_store_backend="memory",
    )

    # Runtime patch OllamaProvider.complete to respect extended timeout (600s)
    # This prevents local inference from being prematurely aborted at 120s without modifying site-packages.
    from muktiverse.schemas.llm import LLMRequest, LLMResponse, LLMUsage
    from muktiverse.llm.selector import ModelSelector, ModelCandidate

    _timeout_val = float(timeout)

    async def _patched_complete(self, request: LLMRequest) -> LLMResponse:
        elapsed = self._timer()
        payload = {
            "model": request.model or self._default_model,
            "messages": self._messages_to_dicts(request.messages),
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }
        if request.tools and "ollama.com" not in self._base_url:
            payload["tools"] = request.tools

        logger.info(f"Ollama complete request to {self._chat_url()} with timeout {_timeout_val}s")
        async with httpx.AsyncClient(timeout=_timeout_val, headers=self._headers, verify=False) as client:
            response = await client.post(self._chat_url(), json=payload)
            response.raise_for_status()
            data = response.json()

        message = data.get("message", {})
        content = message.get("content", "")
        # Fallback to thinking if model thought out loud without final content
        if not content and "thinking" in message:
            content = message["thinking"]

        tool_calls = message.get("tool_calls", [])
        usage = LLMUsage(
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
        )
        return self._build_response(
            content=content,
            model=data.get("model", request.model or self._default_model),
            usage=usage,
            latency_ms=elapsed(),
            tool_calls=tool_calls,
            raw=data,
        )

    OllamaProvider.complete = _patched_complete

    # Enforce only local models in ModelSelector to prevent cloud fallback 404s
    def _local_select_all(self, task_type: str, mode: str = "balanced") -> list[ModelCandidate]:
        return [
            ModelCandidate(
                provider="ollama",
                model=model,
                score=1.0,
                reason="local_stark_configured",
            )
        ]
    ModelSelector.select_all = _local_select_all

    # Replace bloated multi-page SaaS guardrails with concise, high-performance STARK guardrails
    import muktiverse.agents.base as base_mod
    base_mod.GLOBAL_GUARDRAILS = (
        "=== STARK SYSTEM DIRECTIVE ===\n"
        "You are STARK, an elite cognitive AI. Provide rigorous, comprehensive, and exhaustive answers.\n"
        "Structure explanations with clear headings, first-principles logic, and detailed breakdowns.\n"
        "Deliver the final, complete analysis directly without meta-commentary."
    )

    logger.info(
        "stark.ollama_adapter.configured",
        model=model,
        base_url=base_url,
        timeout=_timeout_val,
    )
    return config


async def check_ollama_health(base_url: str = OLLAMA_BASE_URL) -> dict:
    """
    Verify Ollama server is reachable and qwen3.5:4b is available.

    Returns:
        dict with keys: connected (bool), model_available (bool), models (list)
    """
    result = {"connected": False, "model_available": False, "models": []}
    try:
        async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
            resp = await client.get(f"{base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            result["connected"] = True
            result["models"] = [m["name"] for m in data.get("models", [])]
            result["model_available"] = any(
                STARK_DEFAULT_MODEL in m for m in result["models"]
            )
    except Exception as e:
        logger.warning("stark.ollama_adapter.health_check_failed", error=str(e))
    return result

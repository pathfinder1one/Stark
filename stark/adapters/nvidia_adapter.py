"""
STARK — NVIDIA NIM Adapter
Configures MuktiVerse to route LLM calls through NVIDIA's cloud inference (moonshotai/kimi-k3).
"""
from __future__ import annotations

import os
import httpx
from typing import Any

from muktiverse import configure, MuktiVerseConfig
from muktiverse.logging import get_logger

logger = get_logger(__name__)

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_DEFAULT_MODEL = "moonshotai/kimi-k3"
NVIDIA_DEFAULT_KEY = "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"


def configure_nvidia(
    api_key: str | None = None,
    model: str = NVIDIA_DEFAULT_MODEL,
    base_url: str = NVIDIA_BASE_URL,
    timeout: int = 300,
) -> MuktiVerseConfig:
    """
    Configure MuktiVerse to route LLM calls through NVIDIA NIM API.

    Args:
        api_key:  NVIDIA API key (nvapi-...)
        model:    NVIDIA model tag (default: moonshotai/kimi-k3)
        base_url: NVIDIA NIM endpoint (default: https://integrate.api.nvidia.com/v1)
        timeout:  Request timeout in seconds

    Returns:
        The active MuktiVerseConfig instance.
    """
    resolved_key = api_key or os.environ.get("NVIDIA_API_KEY") or NVIDIA_DEFAULT_KEY
    os.environ["NVIDIA_API_KEY"] = resolved_key
    os.environ["NVIDIA_BASE_URL"] = base_url

    config = configure(
        # Primary provider is NVIDIA
        default_provider="nvidia",
        nvidia_api_key=resolved_key,
        nvidia_model=model,

        # Orchestrator + Judge use NVIDIA NIM
        orchestrator_provider="nvidia",
        orchestrator_model=model,
        judge_provider="nvidia",
        judge_model=model,

        # Vector store in memory
        vector_store_backend="memory",
    )

    # Runtime patch ModelSelector to select the active NVIDIA model
    from muktiverse.llm.selector import ModelSelector, ModelCandidate
    def _nvidia_select_all(self, task_type: str, mode: str = "balanced") -> list[ModelCandidate]:
        return [
            ModelCandidate(
                provider="nvidia",
                model=model,
                score=1.0,
                reason="nvidia_stark_configured",
            )
        ]
    ModelSelector.select_all = _nvidia_select_all

    # Ensure clean, high-performance system directives
    import muktiverse.agents.base as base_mod
    base_mod.GLOBAL_GUARDRAILS = (
        "=== STARK SYSTEM DIRECTIVE ===\n"
        "You are STARK, an elite cognitive AI powered by NVIDIA NIM.\n"
        "Provide rigorous, comprehensive, and exhaustive answers.\n"
        "Structure explanations with clear headings, first-principles logic, and detailed breakdowns.\n"
        "Deliver the final, complete analysis directly without meta-commentary."
    )

    logger.info(
        "stark.nvidia_adapter.configured",
        model=model,
        base_url=base_url,
        timeout=timeout,
    )
    return config


async def check_nvidia_health(
    api_key: str | None = None,
    base_url: str = NVIDIA_BASE_URL,
    model: str = NVIDIA_DEFAULT_MODEL,
) -> dict[str, Any]:
    """
    Verify NVIDIA NIM API server is reachable and API key is authorized.

    Returns:
        dict with keys: connected (bool), authorized (bool), model (str), error (str | None)
    """
    resolved_key = api_key or os.environ.get("NVIDIA_API_KEY") or NVIDIA_DEFAULT_KEY
    result = {"connected": False, "authorized": False, "model": model, "error": None}

    headers = {
        "Authorization": f"Bearer {resolved_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            resp = await client.get(f"{base_url.rstrip('/')}/models", headers=headers)
            result["connected"] = True
            if resp.status_code == 200:
                result["authorized"] = True
                models_data = resp.json().get("data", [])
                available_ids = [m.get("id") for m in models_data]
                if model not in available_ids:
                    logger.warning("stark.nvidia_adapter.model_not_in_catalog", model=model)
            else:
                result["error"] = f"HTTP {resp.status_code}: {resp.text[:120]}"
    except Exception as e:
        result["error"] = str(e)
        logger.warning("stark.nvidia_adapter.health_check_failed", error=str(e))

    return result

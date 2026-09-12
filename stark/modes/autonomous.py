"""
STARK — Autonomous Mode
Self-directing agent loop via MuktiVerse's AutonomousOrchestrator.
Best for: open-ended goals, complex tasks requiring self-direction.
No latency target — runs until goal is achieved or max_iterations hit.
"""
from __future__ import annotations

import uuid
from typing import Callable, Awaitable

from muktiverse.orchestrator.core import OrchestratorEngine, OrchestratorRequest
from muktiverse.logging import get_logger

logger = get_logger(__name__)

_engine: OrchestratorEngine | None = None


def _get_engine() -> OrchestratorEngine:
    global _engine
    if _engine is None:
        _engine = OrchestratorEngine()
    return _engine


async def run_autonomous(
    message: str,
    session_id: str | None = None,
    user_id: str = "stark_user",
    model: str = "qwen3.5:4b",
    stream_callback: Callable[[str, str, str], Awaitable[None]] | None = None,
) -> tuple[str, dict]:
    """
    Execute in Autonomous mode: self-directing, full cognitive loop.

    The engine will spawn agents, use tools, re-plan, and iterate
    until the goal is achieved or the max iteration limit is reached.

    Args:
        message:         The high-level goal or instruction.
        session_id:      Conversation session ID.
        user_id:         User identifier.
        model:           Ollama model to use.
        stream_callback: Optional SSE streaming callback.

    Returns:
        Tuple of (answer: str, metadata: dict)
    """
    session_id = session_id or str(uuid.uuid4())
    engine = _get_engine()

    # Autonomous mode always uses thinking mode + judge + full orchestration
    request = OrchestratorRequest(
        user_message=message,
        user_id=user_id,
        conversation_id=session_id,
        model_provider="ollama",
        model_name=model,
        enable_rag=False,
        enable_memory=False,
        enable_judge=True,
        mode="thinking",
    )

    logger.info("autonomous_mode.executing", preview=message[:60])
    response = await engine.process(request, stream_callback=stream_callback)

    metadata = {
        "agents": response.agents_used,
        "tasks_created": response.tasks_created,
        "model": response.model_name,
        "tokens": response.total_tokens,
        "latency_ms": round(response.total_latency_ms, 1),
        "quality_score": response.quality_score,
        "judge_verdict": (
            response.verdict.recommendation if response.verdict else None
        ),
    }

    logger.info(
        "autonomous_mode.complete",
        agents=response.agents_used,
        quality=response.quality_score,
        tokens=response.total_tokens,
    )
    return response.response, metadata

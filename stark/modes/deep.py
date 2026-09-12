"""
STARK — Deep Mode
Full multi-agent DAG execution via MuktiVerse's OrchestratorEngine.
Best for: research, code generation, multi-step complex problems.
Target latency: < 60 seconds.
"""
from __future__ import annotations

import uuid
from muktiverse.orchestrator.core import OrchestratorEngine, OrchestratorRequest
from muktiverse.logging import get_logger

logger = get_logger(__name__)

# Lazy-init singleton so it's only created once
_engine: OrchestratorEngine | None = None


def _get_engine() -> OrchestratorEngine:
    global _engine
    if _engine is None:
        _engine = OrchestratorEngine()
    return _engine


async def run_deep(
    message: str,
    session_id: str | None = None,
    user_id: str = "stark_user",
    model: str = "qwen3.5:4b",
    enable_judge: bool = True,
) -> tuple[str, dict]:
    """
    Execute in Deep mode: full MuktiVerse orchestration pipeline.

    Flow:
      IntentEngine → TaskPlanner → ParallelExecutor → Synthesizer → JudgeAgent

    Args:
        message:      The user's query or instruction.
        session_id:   Conversation session ID.
        user_id:      User identifier.
        model:        Ollama model to use.
        enable_judge: Whether to run JudgeAgent quality evaluation.

    Returns:
        Tuple of (answer: str, metadata: dict)
    """
    session_id = session_id or str(uuid.uuid4())
    engine = _get_engine()

    request = OrchestratorRequest(
        user_message=message,
        user_id=user_id,
        conversation_id=session_id,
        model_provider="ollama",
        model_name=model,
        enable_rag=False,
        enable_memory=False,
        enable_judge=enable_judge,
        mode="thinking",  # MuktiVerse's most capable mode
    )

    logger.info("deep_mode.executing", preview=message[:60])
    response = await engine.process(request)

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
        "deep_mode.complete",
        agents=response.agents_used,
        tokens=response.total_tokens,
        quality=response.quality_score,
    )
    return response.response, metadata

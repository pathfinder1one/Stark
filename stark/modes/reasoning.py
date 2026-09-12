"""
STARK — Reasoning Mode
Chain-of-thought reasoning via MuktiVerse's ReasoningAgent.
Best for: math, logic, comparisons, step-by-step analysis.
Target latency: < 15 seconds.
"""
from __future__ import annotations

import uuid
from muktiverse.agents.reasoning import ReasoningAgent
from muktiverse.agents.base import AgentContext
from muktiverse.logging import get_logger

logger = get_logger(__name__)


async def run_reasoning(
    message: str,
    session_id: str | None = None,
    user_id: str = "stark_user",
    model: str = "qwen3.5:4b",
) -> tuple[str, dict]:
    """
    Execute in Reasoning mode using MuktiVerse's ReasoningAgent.

    Activates chain-of-thought, step-by-step analysis.
    Uses qwen3.5:4b's built-in thinking capability.

    Args:
        message:    The user's query.
        session_id: Conversation session ID.
        user_id:    User identifier.
        model:      Ollama model to use.

    Returns:
        Tuple of (answer: str, metadata: dict)
    """
    session_id = session_id or str(uuid.uuid4())

    context = AgentContext(
        user_id=user_id,
        conversation_id=session_id,
        task_id=str(uuid.uuid4()),
        mode="medium",  # MuktiVerse mode string
    )

    agent = ReasoningAgent()
    logger.info("reasoning_mode.executing", preview=message[:60])

    result = await agent.execute(
        task=message,
        context=context,
        model_provider="ollama",
        model_name=model,
        temperature=0.6,
        max_tokens=4096,
    )

    metadata = {
        "agent": result.agent_name,
        "model": result.model_name,
        "tokens": result.total_tokens,
        "latency_ms": round(result.latency_ms, 1),
        "success": result.success,
    }

    if not result.success:
        logger.warning("reasoning_mode.failed", error=result.error)
        return f"[Reasoning failed: {result.error}]", metadata

    logger.info(
        "reasoning_mode.complete",
        tokens=result.total_tokens,
        latency_ms=round(result.latency_ms, 1),
    )
    return result.content, metadata

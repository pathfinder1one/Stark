"""
STARK — Thinker
The first step in the cognitive loop: executes the agent pipeline
for a given mode and returns a candidate answer.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from muktiverse.agents.base import AgentContext, AgentResult
from muktiverse.agents.reasoning import ReasoningAgent
from muktiverse.agents.research import ResearchAgent
from muktiverse.agents.coding import CoderAgent
from muktiverse.agents.math import MathAgent
from muktiverse.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ThinkResult:
    """Output from the Thinker — a candidate answer ready for verification."""
    content: str
    agents_used: list[str] = field(default_factory=list)
    model: str = "qwen3.5:4b"
    total_tokens: int = 0
    latency_ms: float = 0.0
    success: bool = True
    error: str | None = None


# ── Task-type → Agent mapping ────────────────────────────────────────────────
_TASK_AGENTS = {
    "coding":    CoderAgent,
    "math":      MathAgent,
    "research":  ResearchAgent,
    "reasoning": ReasoningAgent,
}

# MuktiVerse intent capabilities → STARK task type
_CAPABILITY_MAP = {
    "coding":            "coding",
    "math":              "math",
    "scientific":        "math",
    "research":          "research",
    "rag_generation":    "research",
    "reasoning":         "reasoning",
    "planning":          "reasoning",
    "data_analysis":     "research",
}


class Thinker:
    """
    Executes the primary agent(s) for a given task and returns a candidate answer.

    In Fast mode  → direct LLM call (no agent overhead)
    In Reasoning  → ReasoningAgent
    In Deep/Auto  → best-fit specialist agent based on task type
    """

    def __init__(self, model: str = "qwen3.5:4b", provider: str = "ollama") -> None:
        self._model = model
        self._provider = provider

    async def think(
        self,
        message: str,
        mode: str,
        session_id: str | None = None,
        user_id: str = "stark_user",
        capabilities: list[str] | None = None,
        memory_context: str = "",
    ) -> ThinkResult:
        """
        Produce a candidate answer for the given message and mode.

        Args:
            message:        The user query or task.
            mode:           Execution mode (fast / reasoning / deep / autonomous).
            session_id:     Session identifier.
            user_id:        User identifier.
            capabilities:   Detected capabilities from ModeRouter/IntentEngine.
            memory_context: Formatted conversation history context.

        Returns:
            ThinkResult with candidate answer and metadata.
        """
        session_id = session_id or str(uuid.uuid4())

        if mode == "fast":
            return await self._think_fast(message, memory_context=memory_context)

        # Pick agent class based on capabilities or default to ReasoningAgent
        agent_cls = self._pick_agent(capabilities or [])
        return await self._think_with_agent(message, agent_cls, session_id, user_id, mode, memory_context=memory_context)

    # ── Fast path ─────────────────────────────────────────────────────────────

    async def _think_fast(self, message: str, memory_context: str = "") -> ThinkResult:
        """Direct LLM call — no agent overhead."""
        import time
        from muktiverse.llm.registry import get_provider
        from muktiverse.schemas.llm import LLMRequest, LLMMessage

        start = time.perf_counter()
        provider = get_provider(self._provider)

        system_content = "You are STARK, a sharp and direct AI assistant. Answer concisely and accurately."
        if memory_context:
            system_content += f"\n\n{memory_context}"

        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=system_content),
                LLMMessage(role="user", content=message),
            ],
            model=self._model,
            provider=self._provider,
            max_tokens=4096,
            temperature=0.7,
        )
        response = await provider.complete(request)
        latency = (time.perf_counter() - start) * 1000

        content = response.content
        # Guarantee non-empty answer: if content is empty but model thought out loud, use thinking
        if not content and hasattr(response, "raw") and isinstance(response.raw, dict):
            raw_msg = response.raw.get("message", {})
            content = raw_msg.get("thinking", "")

        return ThinkResult(
            content=content,
            agents_used=["direct_llm"],
            model=self._model,
            total_tokens=response.usage.total_tokens,
            latency_ms=round(latency, 1),
        )

    # ── Agent path ────────────────────────────────────────────────────────────

    async def _think_with_agent(
        self,
        message: str,
        agent_cls: type,
        session_id: str,
        user_id: str,
        mode: str,
        memory_context: str = "",
    ) -> ThinkResult:
        """Run a specialist agent and return its output as a ThinkResult."""
        import time
        start = time.perf_counter()

        muktiverse_mode = {"fast": "fast", "reasoning": "medium", "deep": "thinking", "autonomous": "thinking"}.get(mode, "medium")

        context = AgentContext(
            user_id=user_id,
            conversation_id=session_id,
            task_id=str(uuid.uuid4()),
            mode=muktiverse_mode,
            memory_context=memory_context,
        )

        agent = agent_cls()
        logger.info("thinker.agent_executing", agent=agent.name, mode=mode, preview=message[:60])

        result: AgentResult = await agent.execute(
            task=message,
            context=context,
            model_provider=self._provider,
            model_name=self._model,
            temperature=0.6,
            max_tokens=4096,
        )

        latency = (time.perf_counter() - start) * 1000

        if not result.success:
            logger.warning("thinker.agent_failed_falling_back_to_direct_llm", agent=agent.name, error=result.error)
            fallback_res = await self._think_fast(message, memory_context=memory_context)
            fallback_res.agents_used = [agent.name, "direct_llm_fallback"]
            return fallback_res

        logger.info("thinker.complete", agent=agent.name, tokens=result.total_tokens, latency_ms=round(result.latency_ms, 1))
        return ThinkResult(
            content=result.content,
            agents_used=[agent.name],
            model=result.model_name or self._model,
            total_tokens=result.total_tokens,
            latency_ms=round(result.latency_ms, 1),
        )

    # ── Agent picker ──────────────────────────────────────────────────────────

    def _pick_agent(self, capabilities: list[str]) -> type:
        """Select best-fit agent class from capabilities list."""
        for cap in capabilities:
            agent_cls = _TASK_AGENTS.get(_CAPABILITY_MAP.get(cap, ""))
            if agent_cls:
                return agent_cls
        return ReasoningAgent  # Default fallback

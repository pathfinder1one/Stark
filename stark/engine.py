"""
STARK Engine
Bootstraps Ollama, routes to best execution mode,
then runs the full CognitiveLoop (Think->Judge->Revise).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from muktiverse.logging import get_logger

from stark.adapters.ollama_adapter import configure_ollama, check_ollama_health
from stark.routing.mode_router import ModeRouter
from stark.memory.manager import STARKMemory

logger = get_logger(__name__)


# ── Response schema ───────────────────────────────────────────────────────────

@dataclass
class STARKResponse:
    """Unified response returned by the STARK engine."""
    answer: str
    session_id: str
    mode_used: str
    agents_used: list[str] = field(default_factory=list)
    judge_score: float | None = None
    verified: bool = False
    revision_count: int = 0
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    model: str = "qwen3.5:4b"
    metadata: dict[str, Any] = field(default_factory=dict)


# ── STARK Engine ──────────────────────────────────────────────────────────────

class STARKEngine:
    """
    STARK's top-level cognitive engine.

    Usage:
        engine = STARKEngine()
        await engine.startup()
        response = await engine.run("Explain transformers", mode="auto")
    """

    def __init__(
        self,
        model: str | None = None,
        provider: str = "ollama",
        ollama_url: str = "http://localhost:11434",
        nvidia_key: str | None = None,
        max_revisions: int = 2,
        enable_judge: bool = True,
    ) -> None:
        self._provider = provider.lower()
        if self._provider == "nvidia":
            self._model = model or "moonshotai/kimi-k3"
        else:
            self._model = model or "qwen3.5:4b"
        self._ollama_url = ollama_url
        self._nvidia_key = nvidia_key
        self._max_revisions = max_revisions
        self._enable_judge = enable_judge
        self._mode_router: ModeRouter | None = None
        self._cognitive_loop = None
        self._memory = STARKMemory()
        self._ready = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def startup(self) -> None:
        """Bootstrap provider config and verify connectivity."""
        logger.info("stark.engine.starting", provider=self._provider, model=self._model)

        if self._provider == "nvidia":
            from stark.adapters.nvidia_adapter import configure_nvidia, check_nvidia_health
            configure_nvidia(api_key=self._nvidia_key, model=self._model)
            health = await check_nvidia_health(api_key=self._nvidia_key, model=self._model)
            if not health["connected"] or not health["authorized"]:
                raise RuntimeError(
                    f"Cannot authenticate with NVIDIA NIM API: {health.get('error') or 'Authorization failed'}"
                )
            available_models = [self._model]
            log_meta = {"provider": "nvidia", "endpoint": "https://integrate.api.nvidia.com/v1"}
        else:
            configure_ollama(model=self._model, base_url=self._ollama_url)
            health = await check_ollama_health(self._ollama_url)
            if not health["connected"]:
                raise RuntimeError(
                    f"Cannot reach Ollama at {self._ollama_url}. "
                    "Run `ollama serve` and try again."
                )
            if not health["model_available"]:
                raise RuntimeError(
                    f"Model '{self._model}' not found in Ollama. "
                    f"Run: ollama pull {self._model}"
                )
            available_models = health["models"]
            log_meta = {"provider": "ollama", "ollama": self._ollama_url}

        from stark.cognitive.loop import CognitiveLoop
        self._cognitive_loop = CognitiveLoop(
            model=self._model,
            provider=self._provider,
            max_revisions=self._max_revisions,
            enable_judge=self._enable_judge,
        )
        self._mode_router = ModeRouter(use_intent_engine=True)
        self._ready = True

        logger.info(
            "stark.engine.ready",
            model=self._model,
            available_models=available_models,
            judge_enabled=self._enable_judge,
            max_revisions=self._max_revisions,
            **log_meta,
        )

    def is_ready(self) -> bool:
        return self._ready

    # ── Main run method ───────────────────────────────────────────────────────

    async def run(
        self,
        message: str,
        mode: str = "auto",
        session_id: str | None = None,
        user_id: str = "stark_user",
        stream_callback: Callable[[str, str], Awaitable[None]] | None = None,
    ) -> STARKResponse:
        """
        Process a message through STARK: ModeRouter -> CognitiveLoop -> STARKResponse.

        Args:
            message:         The user query.
            mode:            auto | fast | reasoning | deep | autonomous
            session_id:      Conversation ID (auto-generated if None).
            user_id:         User identifier.
            stream_callback: Optional async hook(chunk, agent_name) for streaming.

        Returns:
            STARKResponse with answer, quality scores, and run metadata.
        """
        if not self._ready:
            raise RuntimeError("STARKEngine not started. Call await engine.startup() first.")

        session_id = session_id or str(uuid.uuid4())

        # Resolve mode
        route = await self._mode_router.route(message) if mode == "auto" else None
        resolved_mode = route.mode if route else mode

        logger.info(
            "stark.engine.run",
            session=session_id,
            mode=resolved_mode,
            source=route.source if route else "explicit",
            message_preview=message[:80],
        )

        # Format conversation context from memory
        memory_context = await self._memory.format_context(session_id)

        # Run cognitive loop
        cognitive_result = await self._cognitive_loop.run(
            message=message,
            mode=resolved_mode,
            session_id=session_id,
            user_id=user_id,
            capabilities=None,
            memory_context=memory_context,
            stream_callback=stream_callback,
        )

        # Record exchange into session memory
        await self._memory.add_turn(session_id, message, cognitive_result.answer)

        return STARKResponse(
            answer=cognitive_result.answer,
            session_id=session_id,
            mode_used=resolved_mode,
            agents_used=cognitive_result.agents_used,
            judge_score=cognitive_result.judge_score,
            verified=cognitive_result.verified,
            revision_count=cognitive_result.revision_count,
            total_latency_ms=cognitive_result.total_latency_ms,
            total_tokens=cognitive_result.total_tokens,
            model=self._model,
            metadata={
                "judge_verdict": cognitive_result.judge_verdict,
                "route_source": route.source if route else "explicit",
                "complexity": route.complexity if route else None,
            },
        )

    async def _resolve_mode(self, mode: str, message: str) -> str:
        """Helper kept for test access."""
        if mode != "auto":
            return mode
        route = await self._mode_router.route(message)
        return route.mode

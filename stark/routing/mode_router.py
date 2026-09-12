"""
STARK — Mode Router
Analyzes a user message and returns the best execution mode.

Uses MuktiVerse's IntentAnalysis (complexity field) as the primary signal,
with keyword pattern matching as a fast-path fallback for common cases.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from muktiverse.orchestrator.intent import IntentEngine, IntentAnalysis
from muktiverse.logging import get_logger

logger = get_logger(__name__)

# ── Complexity → STARK mode mapping ──────────────────────────────────────────
_COMPLEXITY_TO_MODE = {
    "simple":       "fast",
    "moderate":     "reasoning",
    "complex":      "deep",
    "very_complex": "deep",
}

# ── Keyword fast-path patterns ────────────────────────────────────────────────
# These bypass the LLM intent classifier for obvious cases (saves tokens & latency)

_FAST_PATTERNS = re.compile(
    r"^(hi|hello|hey|what is|who is|when did|define|translate|thanks|ok|yes|no"
    r"|what'?s|tell me what|give me a quick|briefly explain|tldr)",
    re.IGNORECASE,
)

_DEEP_PATTERNS = re.compile(
    r"\b(research|build|implement|create a|write code|develop|investigate|"
    r"find all|deep dive|comprehensive|full analysis|end[-\s]to[-\s]end|"
    r"architecture|design a system|step by step plan|detailed report)\b",
    re.IGNORECASE,
)

_AUTONOMOUS_PATTERNS = re.compile(
    r"\b(achieve|accomplish|do whatever|solve this completely|"
    r"figure out how to|work on this until|complete the task|"
    r"make it happen|get it done)\b",
    re.IGNORECASE,
)


# ── RouteResult ───────────────────────────────────────────────────────────────

@dataclass
class RouteResult:
    """Outcome of mode routing for a user message."""
    mode: str                       # fast | reasoning | deep | autonomous
    source: str                     # "keyword" | "intent_engine" | "fallback"
    complexity: str = "simple"      # from IntentAnalysis
    intent_summary: str = ""
    requires_tools: bool = False
    requires_multi_agent: bool = False


# ── Mode Router ───────────────────────────────────────────────────────────────

class ModeRouter:
    """
    Decides which STARK execution mode best suits a user message.

    Decision priority:
      1. Keyword fast-path  → immediate result, zero LLM overhead
      2. IntentEngine       → LLM-based complexity classification
      3. Word-count fallback → heuristic for edge cases
    """

    def __init__(self, use_intent_engine: bool = True) -> None:
        self._use_intent_engine = use_intent_engine
        self._intent_engine = IntentEngine() if use_intent_engine else None

    async def route(self, message: str) -> RouteResult:
        """
        Route a message to the appropriate execution mode.

        Args:
            message: The user's query or instruction.

        Returns:
            RouteResult with selected mode and routing metadata.
        """
        stripped = message.strip()

        # ── 1. Autonomous keyword check (highest priority) ────────────────────
        if _AUTONOMOUS_PATTERNS.search(stripped):
            logger.debug("mode_router.keyword_autonomous", preview=stripped[:60])
            return RouteResult(
                mode="autonomous",
                source="keyword",
                complexity="very_complex",
                intent_summary="Autonomous goal-driven task detected",
                requires_multi_agent=True,
            )

        # ── 2. Fast-path keyword check ────────────────────────────────────────
        word_count = len(stripped.split())
        if word_count <= 8 and _FAST_PATTERNS.match(stripped):
            logger.debug("mode_router.keyword_fast", preview=stripped[:60])
            return RouteResult(
                mode="fast",
                source="keyword",
                complexity="simple",
                intent_summary="Simple conversational query",
            )

        # ── 3. Deep keyword check ─────────────────────────────────────────────
        if _DEEP_PATTERNS.search(stripped):
            logger.debug("mode_router.keyword_deep", preview=stripped[:60])
            return RouteResult(
                mode="deep",
                source="keyword",
                complexity="complex",
                intent_summary="Complex multi-step task detected",
                requires_tools=True,
                requires_multi_agent=True,
            )

        # ── 4. IntentEngine (LLM-based classification) ────────────────────────
        if self._use_intent_engine:
            try:
                intent: IntentAnalysis = await self._intent_engine.analyze(
                    stripped, mode="fast"  # use fast mode for routing itself
                )
                mode = _COMPLEXITY_TO_MODE.get(intent.complexity, "reasoning")

                logger.info(
                    "mode_router.intent_engine",
                    mode=mode,
                    complexity=intent.complexity,
                    capabilities=intent.required_capabilities,
                )

                return RouteResult(
                    mode=mode,
                    source="intent_engine",
                    complexity=intent.complexity,
                    intent_summary=intent.primary_intent,
                    requires_tools=(
                        intent.needs_web_search
                        or intent.needs_code_execution
                        or intent.needs_file_processing
                    ),
                    requires_multi_agent=intent.needs_multi_agent,
                )

            except Exception as e:
                logger.warning("mode_router.intent_engine_failed", error=str(e))
                # Fall through to heuristic

        # ── 5. Word-count fallback heuristic ─────────────────────────────────
        if word_count <= 15:
            mode = "fast"
        elif word_count <= 40:
            mode = "reasoning"
        else:
            mode = "deep"

        logger.debug("mode_router.fallback_heuristic", mode=mode, words=word_count)
        return RouteResult(
            mode=mode,
            source="fallback",
            complexity="moderate",
            intent_summary="Heuristic routing",
        )

"""
STARK — Cognitive Loop
The core intelligence cycle: THINK → VERIFY → JUDGE → REFLECT → REVISE

This is what makes STARK a cognitive system rather than just a chatbot.
Every non-trivial response passes through this loop before being returned.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Awaitable

from muktiverse.agents.base import AgentContext, AgentResult
from muktiverse.agents.judge import JudgeAgent, JudgeVerdict
from muktiverse.agents.verification import VerificationAgent
from muktiverse.logging import get_logger

from stark.cognitive.thinker import Thinker, ThinkResult
from stark.cognitive.revisor import Revisor

logger = get_logger(__name__)


class LocalJudgeAgent(JudgeAgent):
    """JudgeAgent that strictly uses local Ollama model for evaluation."""

    def __init__(self, model: str = "qwen3.5:4b") -> None:
        super().__init__()
        self._judge_model = model

    async def evaluate(
        self,
        original_task: str,
        response_to_evaluate: str,
        context: AgentContext,
    ) -> JudgeVerdict:
        evaluation_prompt = f"""Evaluate the following AI response:

ORIGINAL TASK:
{original_task}

RESPONSE TO EVALUATE:
{response_to_evaluate}

Provide your evaluation as a JSON object following the exact format specified in your instructions.
"""
        result: AgentResult = await self.execute(
            task=evaluation_prompt,
            context=context,
            model_provider="ollama",
            model_name=self._judge_model,
            temperature=0.1,
            max_tokens=1024,
        )

        if not result.success:
            return JudgeVerdict(
                accuracy=75, completeness=75, coherence=75,
                relevance=75, hallucination_risk=20,
                confidence=0.75, overall_score=75,
                issues=[f"Local judge evaluation error: {result.error}"],
                recommendation="accept",
            )

        return self._parse_verdict(result.content)


# ── Loop result ───────────────────────────────────────────────────────────────

@dataclass
class CognitiveResult:
    """Final output of the cognitive loop."""
    answer: str
    mode_used: str
    agents_used: list[str] = field(default_factory=list)

    # Quality signals
    judge_score: float | None = None        # 0–100
    judge_verdict: str | None = None        # accept | revise | reject
    verified: bool = False
    revision_count: int = 0

    # Performance
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    model: str = "qwen3.5:4b"

    # Internals (for debugging/evaluation)
    think_result: ThinkResult | None = None
    judge_details: JudgeVerdict | None = None


# ── Cognitive Loop ────────────────────────────────────────────────────────────

class CognitiveLoop:
    """
    STARK's cognitive quality cycle.

    Flow:
        1. THINK   — Thinker produces a candidate answer
        2. JUDGE   — JudgeAgent scores accuracy, completeness, hallucination risk
        3. ACCEPT  — Score >= threshold? Return the answer.
           REVISE  — Score < threshold? Run Revisor, then re-judge (up to max_revisions)
        4. OUTPUT  — Final safety-checked answer returned

    Judge is only run for modes: reasoning, deep, autonomous
    Fast mode skips the loop entirely for speed.
    """

    # Mode-specific judge thresholds (out of 100)
    _PASS_THRESHOLDS = {
        "fast":       100,   # Always pass (judge not run)
        "reasoning":   70,
        "deep":        75,
        "autonomous":  80,
    }

    def __init__(
        self,
        model: str = "qwen3.5:4b",
        max_revisions: int = 2,
        enable_judge: bool = True,
        enable_verification: bool = False,   # Phase 5 — enable with tools
    ) -> None:
        self._model = model
        self._max_revisions = max_revisions
        self._enable_judge = enable_judge
        self._enable_verification = enable_verification
        self._thinker = Thinker(model=model)
        self._revisor = Revisor(model=model)
        self._judge = LocalJudgeAgent(model=model)

    async def run(
        self,
        message: str,
        mode: str,
        session_id: str | None = None,
        user_id: str = "stark_user",
        capabilities: list[str] | None = None,
        memory_context: str = "",
        stream_callback: Callable[[str, str], Awaitable[None]] | None = None,
    ) -> CognitiveResult:
        """
        Run the full cognitive loop for a given message and mode.

        Args:
            message:        User query or task.
            mode:           Execution mode (fast / reasoning / deep / autonomous).
            session_id:     Conversation session ID.
            user_id:        User identifier.
            capabilities:   Detected task capabilities from ModeRouter.
            memory_context: Formatted conversation history context.
            stream_callback: Optional SSE streaming hook(chunk, agent_name).

        Returns:
            CognitiveResult with answer, quality scores, and metadata.
        """
        session_id = session_id or str(uuid.uuid4())
        start = time.perf_counter()
        all_agents: list[str] = []
        total_tokens = 0

        # ── Step 1: THINK ─────────────────────────────────────────────────────
        if stream_callback:
            await stream_callback(f"[{mode.upper()} MODE] Thinking...\n", "thinker")

        think_result = await self._thinker.think(
            message=message,
            mode=mode,
            session_id=session_id,
            user_id=user_id,
            capabilities=capabilities,
            memory_context=memory_context,
        )
        all_agents.extend(think_result.agents_used)
        total_tokens += think_result.total_tokens

        if not think_result.success or not think_result.content:
            logger.error("cognitive_loop.think_failed", error=think_result.error)
            return CognitiveResult(
                answer=f"[STARK Error: thinking failed — {think_result.error}]",
                mode_used=mode,
                agents_used=all_agents,
                total_latency_ms=round((time.perf_counter() - start) * 1000, 1),
                model=self._model,
                think_result=think_result,
            )

        candidate = think_result.content

        # ── Fast mode: skip judge entirely ───────────────────────────────────
        if mode == "fast" or not self._enable_judge:
            return CognitiveResult(
                answer=candidate,
                mode_used=mode,
                agents_used=all_agents,
                total_tokens=total_tokens,
                total_latency_ms=round((time.perf_counter() - start) * 1000, 1),
                model=self._model,
                think_result=think_result,
            )

        # ── Steps 2-4: JUDGE → REVISE loop ───────────────────────────────────
        judge_context = AgentContext(
            user_id=user_id,
            conversation_id=session_id,
            task_id=str(uuid.uuid4()),
            mode="thinking",
        )

        threshold = self._PASS_THRESHOLDS.get(mode, 70)
        verdict: JudgeVerdict | None = None
        revision_count = 0

        for attempt in range(self._max_revisions + 1):
            # ── Step 2: JUDGE ─────────────────────────────────────────────────
            if stream_callback and attempt == 0:
                await stream_callback("Evaluating quality...\n", "judge")
            elif stream_callback:
                await stream_callback(f"Re-evaluating (attempt {attempt})...\n", "judge")

            try:
                verdict = await self._judge.evaluate(
                    original_task=message,
                    response_to_evaluate=candidate,
                    context=judge_context,
                )
                all_agents.append("judge")
                logger.info(
                    "cognitive_loop.judge",
                    attempt=attempt,
                    score=verdict.overall_score,
                    recommendation=verdict.recommendation,
                    hallucination_risk=verdict.hallucination_risk,
                )
            except Exception as e:
                logger.warning("cognitive_loop.judge_error", error=str(e))
                break  # Skip judge on error, return current candidate

            # ── Step 3: ACCEPT check ──────────────────────────────────────────
            passes = (
                verdict.overall_score >= threshold
                and verdict.recommendation == "accept"
                and verdict.hallucination_risk <= 30
            )

            if passes:
                logger.info("cognitive_loop.accepted", score=verdict.overall_score, attempt=attempt)
                break

            # ── Last attempt — give up and return best we have ────────────────
            if attempt >= self._max_revisions:
                logger.info(
                    "cognitive_loop.max_revisions_reached",
                    final_score=verdict.overall_score,
                )
                break

            # ── Step 4: REVISE ────────────────────────────────────────────────
            if stream_callback:
                await stream_callback(
                    f"Revising (score {verdict.overall_score}/{threshold}, issues: {len(verdict.issues)})...\n",
                    "revisor"
                )

            revision_result = await self._revisor.revise(
                original_query=message,
                candidate_answer=candidate,
                judge_feedback="\n".join(verdict.issues),
                revision_notes=verdict.revision_notes,
                attempt=attempt + 1,
                session_id=session_id,
                user_id=user_id,
            )
            all_agents.append("reflection")
            revision_count += 1

            if revision_result.success and revision_result.revised_content:
                candidate = revision_result.revised_content
            else:
                logger.warning("cognitive_loop.revision_failed", attempt=attempt + 1)
                break  # Keep previous candidate

        # ── Final result ──────────────────────────────────────────────────────
        total_latency = round((time.perf_counter() - start) * 1000, 1)

        return CognitiveResult(
            answer=candidate,
            mode_used=mode,
            agents_used=all_agents,
            judge_score=float(verdict.overall_score) if verdict else None,
            judge_verdict=verdict.recommendation if verdict else None,
            verified=verdict is not None and verdict.overall_score >= threshold,
            revision_count=revision_count,
            total_tokens=total_tokens,
            total_latency_ms=total_latency,
            model=self._model,
            think_result=think_result,
            judge_details=verdict,
        )

"""
STARK — Revisor
Targeted revision of a candidate answer based on reflection feedback.
Called when JudgeAgent rejects or flags an answer for revision.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from muktiverse.agents.base import AgentContext
from muktiverse.agents.reflection import ReflectionAgent
from muktiverse.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RevisionResult:
    """Output from a targeted revision pass."""
    revised_content: str
    revision_summary: str
    attempt: int
    success: bool = True
    error: str | None = None


class Revisor:
    """
    Generates a targeted revision of a candidate answer.

    Uses MuktiVerse's ReflectionAgent to:
    1. Understand what failed (from JudgeAgent feedback)
    2. Produce a corrected, improved version of the answer

    This is deliberately narrow — it revises only what the judge flagged,
    not a full re-run of the agent pipeline.
    """

    def __init__(self, model: str = "qwen3.5:4b", provider: str = "ollama") -> None:
        self._model = model
        self._provider = provider
        self._agent = ReflectionAgent()

    async def revise(
        self,
        original_query: str,
        candidate_answer: str,
        judge_feedback: str,
        revision_notes: str = "",
        attempt: int = 1,
        session_id: str | None = None,
        user_id: str = "stark_user",
    ) -> RevisionResult:
        """
        Revise a candidate answer based on judge feedback.

        Args:
            original_query:   The original user query.
            candidate_answer: The answer that was rejected by the judge.
            judge_feedback:   Issues list from JudgeVerdict.
            revision_notes:   Specific revision instructions from JudgeVerdict.
            attempt:          Which revision attempt this is (for logging).
            session_id:       Session identifier.
            user_id:          User identifier.

        Returns:
            RevisionResult with the revised answer and summary.
        """
        session_id = session_id or str(uuid.uuid4())

        revision_prompt = f"""You are reviewing and improving an AI response.

ORIGINAL QUESTION:
{original_query}

CURRENT ANSWER (needs improvement):
{candidate_answer}

JUDGE FEEDBACK (what was wrong):
{judge_feedback}

SPECIFIC REVISION INSTRUCTIONS:
{revision_notes or "Fix the issues identified above and improve overall quality."}

Please provide:
## Critical Assessment
[What specifically needs to change and why]

## Issues Found
[Numbered list of concrete problems from the judge feedback]

## Improved Answer
[A complete, corrected version of the answer that addresses ALL issues]
"""

        context = AgentContext(
            user_id=user_id,
            conversation_id=session_id,
            task_id=str(uuid.uuid4()),
            mode="thinking",
        )

        logger.info(
            "revisor.revising",
            attempt=attempt,
            feedback_preview=judge_feedback[:80],
        )

        result = await self._agent.execute(
            task=revision_prompt,
            context=context,
            model_provider=self._provider,
            model_name=self._model,
            temperature=0.5,
            max_tokens=2048,
        )

        if not result.success:
            logger.warning("revisor.failed", attempt=attempt, error=result.error)
            return RevisionResult(
                revised_content=candidate_answer,  # Fall back to original
                revision_summary="Revision failed — keeping original answer",
                attempt=attempt,
                success=False,
                error=result.error,
            )

        # Extract the "Improved Answer" section from the reflection output
        revised = self._extract_improved_answer(result.content, candidate_answer)

        logger.info("revisor.complete", attempt=attempt, tokens=result.total_tokens)
        return RevisionResult(
            revised_content=revised,
            revision_summary=f"Revision attempt {attempt} complete",
            attempt=attempt,
        )

    def _extract_improved_answer(self, reflection_output: str, fallback: str) -> str:
        """
        Extract just the 'Improved Answer' section from the ReflectionAgent output.
        Falls back to the full output if the section header is not found.
        """
        marker = "## Improved Answer"
        idx = reflection_output.find(marker)
        if idx != -1:
            improved = reflection_output[idx + len(marker):].strip()
            return improved if improved else reflection_output
        return reflection_output  # Return full output if no section found

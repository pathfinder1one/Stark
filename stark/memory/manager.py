"""
STARK — Local Memory Manager
Provides in-memory session history and context retrieval for conversational continuity.
Requires no external Redis or database server — runs 100% locally.
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from muktiverse.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MessageTurn:
    role: str                       # "user" | "assistant" | "system"
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class STARKMemory:
    """
    Session-based conversation memory.

    Maintains a rolling window of message turns per session ID.
    Enables multi-turn context retention across fast, reasoning, and deep modes.
    """

    def __init__(self, max_turns_per_session: int = 20) -> None:
        self._max_turns = max_turns_per_session
        self._sessions: dict[str, list[MessageTurn]] = defaultdict(list)

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a single message turn to the session history."""
        turn = MessageTurn(
            role=role,
            content=content,
            metadata=metadata or {},
        )
        self._sessions[session_id].append(turn)
        # Keep within max window
        if len(self._sessions[session_id]) > self._max_turns:
            self._sessions[session_id] = self._sessions[session_id][-self._max_turns:]
        logger.debug("stark.memory.message_added", session=session_id, role=role, count=len(self._sessions[session_id]))

    async def add_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """Add a complete user-assistant exchange."""
        await self.add_message(session_id, "user", user_message)
        await self.add_message(session_id, "assistant", assistant_message)

    async def get_history(self, session_id: str, limit: int = 10) -> list[MessageTurn]:
        """Return the most recent turns for a session."""
        return self._sessions[session_id][-limit:]

    async def format_context(self, session_id: str, limit: int = 6) -> str:
        """
        Format recent conversation history into a prompt-injectable string.
        Returns empty string if no history exists.
        """
        history = await self.get_history(session_id, limit=limit)
        if not history:
            return ""

        lines = ["=== Recent Conversation Context ==="]
        for turn in history:
            speaker = "User" if turn.role == "user" else "STARK"
            lines.append(f"{speaker}: {turn.content.strip()}")
        return "\n".join(lines)

    async def clear_session(self, session_id: str) -> None:
        """Clear memory for a specific session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("stark.memory.cleared", session=session_id)

    def session_count(self) -> int:
        return len(self._sessions)

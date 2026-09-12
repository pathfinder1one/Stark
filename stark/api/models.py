"""
STARK — API Data Models
Pydantic schemas for the FastAPI endpoints.
"""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="User query or instruction")
    mode: Literal["auto", "fast", "reasoning", "deep", "autonomous"] = Field(
        default="auto", description="Execution mode"
    )
    session_id: str | None = Field(
        default=None, description="Session ID for conversation continuity"
    )
    user_id: str = Field(default="stark_user", description="User identifier")
    stream: bool = Field(default=False, description="Whether to stream response")


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    mode_used: str
    agents_used: list[str] = Field(default_factory=list)
    judge_score: float | None = None
    verified: bool = False
    revision_count: int = 0
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    model: str = "qwen3.5:4b"
    metadata: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str = "ok"
    stark_version: str
    muktiverse_version: str
    ollama_connected: bool
    model: str


class StatusResponse(BaseModel):
    status: str = "running"
    model: str
    active_sessions: int
    uptime_seconds: float

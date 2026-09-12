"""
STARK — FastAPI Server
Exposes REST endpoints for chatting with the local cognitive AI system.
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from muktiverse import __version__ as muktiverse_version
from muktiverse.logging import get_logger

from stark import __version__ as stark_version
from stark.engine import STARKEngine
from stark.api.models import ChatRequest, ChatResponse, HealthResponse, StatusResponse

logger = get_logger(__name__)

# Global STARKEngine instance
engine: STARKEngine | None = None
start_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle."""
    global engine, start_time
    start_time = time.time()
    logger.info("stark.api.starting")
    engine = STARKEngine(model="qwen3.5:4b")
    await engine.startup()
    logger.info("stark.api.ready")
    yield
    logger.info("stark.api.shutdown")


app = FastAPI(
    title="STARK — Local Cognitive AI",
    description="Cognitive AI orchestration layer powered by MuktiVerse and Ollama.",
    version=stark_version,
    lifespan=lifespan,
)

# Enable CORS for web UI / clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check system health, version, and Ollama connection."""
    if not engine or not engine.is_ready():
        raise HTTPException(status_code=503, detail="STARK engine is not ready")

    from stark.adapters.ollama_adapter import check_ollama_health
    h = await check_ollama_health()

    return HealthResponse(
        status="ok" if h["connected"] else "degraded",
        stark_version=stark_version,
        muktiverse_version=muktiverse_version,
        ollama_connected=h["connected"],
        model="qwen3.5:4b",
    )


@app.get("/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    """Return active session count, uptime, and engine status."""
    if not engine:
        raise HTTPException(status_code=503, detail="STARK engine not initialized")

    uptime = time.time() - start_time
    sessions = engine._memory.session_count() if hasattr(engine, "_memory") else 0

    return StatusResponse(
        status="running",
        model="qwen3.5:4b",
        active_sessions=sessions,
        uptime_seconds=round(uptime, 1),
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process a user message through the STARK cognitive loop.
    Supports auto, fast, reasoning, deep, and autonomous modes.
    """
    if not engine or not engine.is_ready():
        raise HTTPException(status_code=503, detail="STARK engine is not ready")

    try:
        resp = await engine.run(
            message=request.message,
            mode=request.mode,
            session_id=request.session_id,
            user_id=request.user_id,
        )

        return ChatResponse(
            answer=resp.answer,
            session_id=resp.session_id,
            mode_used=resp.mode_used,
            agents_used=resp.agents_used,
            judge_score=resp.judge_score,
            verified=resp.verified,
            revision_count=resp.revision_count,
            total_latency_ms=resp.total_latency_ms,
            total_tokens=resp.total_tokens,
            model=resp.model,
            metadata=resp.metadata,
        )
    except Exception as e:
        logger.error("stark.api.chat_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

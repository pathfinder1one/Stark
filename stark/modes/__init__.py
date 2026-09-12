"""
STARK — Modes Package
"""
from stark.modes.fast import run_fast
from stark.modes.reasoning import run_reasoning
from stark.modes.deep import run_deep
from stark.modes.autonomous import run_autonomous

__all__ = ["run_fast", "run_reasoning", "run_deep", "run_autonomous"]

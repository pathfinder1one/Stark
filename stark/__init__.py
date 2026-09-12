"""
STARK — Local Cognitive AI
Entry point: imports, version, and top-level convenience exports.
"""
from stark.engine import STARKEngine, STARKResponse

__version__ = "0.1.0"
__author__ = "Chira"

__all__ = [
    "STARKEngine",
    "STARKResponse",
    "__version__",
]

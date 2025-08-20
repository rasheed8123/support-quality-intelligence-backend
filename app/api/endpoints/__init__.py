"""
API endpoints package.
Contains all FastAPI route handlers for the Support Quality Intelligence system.
"""

from .verification import router as verification_router
from .health import router as health_router

__all__ = [
    "verification_router",
    "health_router"
]

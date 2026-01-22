"""FastAPI routers package."""

from app.routers.auth import router as auth_router
from app.routers.content import router as content_router
from app.routers.resume import router as resume_router
from app.routers.gmail import router as gmail_router

__all__ = ["auth_router", "content_router", "resume_router", "gmail_router"]

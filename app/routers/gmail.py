"""Gmail integration router."""

import logging
import os
from urllib.parse import urlparse
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse

from app.schemas import (
    GmailStatusResponse,
    GmailCreateDraftRequest,
    GmailCreateDraftResponse,
    GmailAuthUrlResponse,
    SuccessResponse,
)
from app.dependencies import get_current_user, get_redis, TokenData
from app.gmail_service import GmailService, GmailOAuthError
from app.redis_manager import RedisManager

logger = logging.getLogger(__name__)

router = APIRouter()


def get_frontend_redirect_url(
    fragment: str = "",
    origin: Optional[str] = None,
    return_to: Optional[str] = None,
) -> str:
    """Get the frontend redirect URL."""
    base = origin or os.environ.get("FRONTEND_ORIGIN") or os.environ.get("PUBLIC_URL") or ""
    base = base.rstrip("/")
    target = base
    if return_to:
        if not return_to.startswith("/"):
            return_to = f"/{return_to}"
        target = f"{target}{return_to}" if target else return_to
    if not target:
        target = "/"
    if fragment:
        target = f"{target}#{fragment}"
    return target


def _resolve_frontend_origin(request: Request) -> Optional[str]:
    origin = request.headers.get("origin")
    if origin:
        parsed = urlparse(origin)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    referer = request.headers.get("referer")
    if referer:
        parsed = urlparse(referer)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    return None


def _normalize_return_to(return_to: Optional[str]) -> Optional[str]:
    if not return_to:
        return None
    candidate = return_to.strip()
    if not candidate:
        return None
    parsed = urlparse(candidate)
    if parsed.scheme or parsed.netloc or candidate.startswith("//"):
        return None
    if not candidate.startswith("/"):
        candidate = f"/{candidate}"
    return candidate


@router.get("/status", response_model=GmailStatusResponse)
async def gmail_status(
    current_user: TokenData = Depends(get_current_user),
):
    """Get Gmail connection status."""
    try:
        service = GmailService(current_user.user_id)
        status = service.get_status()
        return GmailStatusResponse(
            availability=status.get("availability", "unknown"),
            authorized=status.get("authorized", False),
            email=status.get("email"),
        )
    except GmailOAuthError as exc:
        return GmailStatusResponse(
            availability="unavailable",
            authorized=False,
            error=str(exc),
        )


@router.post("/disconnect", response_model=SuccessResponse)
async def gmail_disconnect(
    current_user: TokenData = Depends(get_current_user),
):
    """Disconnect Gmail account."""
    service = GmailService(current_user.user_id)
    service.disconnect()
    return SuccessResponse(success=True)


@router.get("/auth-url", response_model=GmailAuthUrlResponse)
async def gmail_auth_url(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    redis: RedisManager = Depends(get_redis),
    return_to: Optional[str] = Query(None),
):
    """Get Gmail OAuth authorization URL."""
    try:
        service = GmailService(current_user.user_id)
        auth_url, state = service.get_authorization_url()
        
        safe_return_to = _normalize_return_to(return_to)
        origin = _resolve_frontend_origin(request)
        payload = {"state": state, "user_id": current_user.user_id}
        if safe_return_to:
            payload["return_to"] = safe_return_to
        if origin:
            payload["origin"] = origin

        # Store state in Redis for validation
        redis.set(
            f"gmail_oauth_state:{current_user.user_id}",
            payload,
            ttl=600,  # 10 minutes
        )
        
        return GmailAuthUrlResponse(auth_url=auth_url)
    except GmailOAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/oauth2callback")
async def gmail_oauth_callback(
    request: Request,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    redis: RedisManager = Depends(get_redis),
):
    """
    Gmail OAuth callback handler.
    
    Note: This callback is tricky with JWT auth since the user is redirected
    from Google and won't have the JWT in the request. We need to use the
    state parameter to identify the user.
    """
    redirect_origin = None
    redirect_return_to = None
    user_id = None

    if state:
        # Find the user from the state - we need to look up all active states
        # In production, you might want to encode the user_id in the state
        # For now, we'll iterate through recent states
        for key in redis.scan_keys("gmail_oauth_state:*"):
            stored_data = redis.get(key)
            if stored_data and stored_data.get("state") == state:
                user_id = stored_data.get("user_id")
                redirect_origin = stored_data.get("origin")
                redirect_return_to = stored_data.get("return_to")
                redis.delete(key)  # Clean up
                break

    if error:
        return RedirectResponse(
            url=get_frontend_redirect_url(
                "gmail_error",
                origin=redirect_origin,
                return_to=redirect_return_to,
            )
        )

    if not code or not state or not user_id:
        return RedirectResponse(
            url=get_frontend_redirect_url(
                "gmail_invalid_state",
                origin=redirect_origin,
                return_to=redirect_return_to,
            )
        )
    
    try:
        service = GmailService(user_id)
        service.exchange_code_for_tokens(code)
        return RedirectResponse(
            url=get_frontend_redirect_url(
                "gmail_connected",
                origin=redirect_origin,
                return_to=redirect_return_to,
            )
        )
    except GmailOAuthError:
        return RedirectResponse(
            url=get_frontend_redirect_url(
                "gmail_error",
                origin=redirect_origin,
                return_to=redirect_return_to,
            )
        )


@router.post("/create-draft", response_model=GmailCreateDraftResponse)
async def gmail_create_draft(
    payload: GmailCreateDraftRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """Create a Gmail draft."""
    try:
        service = GmailService(current_user.user_id)
        draft = service.create_draft(
            to_email=payload.recipient_email,
            subject=payload.subject,
            body_html=payload.body,
            cc=payload.cc.split(",") if payload.cc else None,
            bcc=payload.bcc.split(",") if payload.bcc else None,
        )
        return GmailCreateDraftResponse(success=True, draft_id=draft.get("id"))
    except GmailOAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to create Gmail draft")
        raise HTTPException(status_code=500, detail="Failed to create draft")

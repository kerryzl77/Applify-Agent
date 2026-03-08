"""Gmail integration router."""

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from urllib.parse import urlencode, urlparse
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
from app.config import get_settings
from app.redis_manager import RedisManager

logger = logging.getLogger(__name__)

router = APIRouter()
STATE_TTL_SECONDS = 600


def _state_signing_key() -> bytes:
    return get_settings().jwt_secret_key.encode("utf-8")


def _encode_oauth_state(
    *,
    user_id: str,
    origin: Optional[str],
    return_to: Optional[str],
) -> str:
    payload = {
        "user_id": user_id,
        "origin": origin,
        "return_to": return_to,
        "exp": int(time.time()) + STATE_TTL_SECONDS,
        "nonce": secrets.token_urlsafe(12),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(_state_signing_key(), payload_bytes, hashlib.sha256).digest()
    return (
        base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
        + "."
        + base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    )


def _decode_oauth_state(state: str) -> Optional[dict]:
    if not state or "." not in state:
        return None

    payload_part, signature_part = state.split(".", 1)
    try:
        payload_bytes = base64.urlsafe_b64decode(payload_part + "=" * (-len(payload_part) % 4))
        signature = base64.urlsafe_b64decode(signature_part + "=" * (-len(signature_part) % 4))
    except Exception:
        return None

    expected_signature = hmac.new(_state_signing_key(), payload_bytes, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected_signature):
        return None

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None

    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < int(time.time()):
        return None

    user_id = payload.get("user_id")
    if not isinstance(user_id, str) or not user_id:
        return None

    origin = payload.get("origin")
    if origin is not None and not isinstance(origin, str):
        return None

    return_to = _normalize_return_to(payload.get("return_to"))
    payload["origin"] = origin
    payload["return_to"] = return_to
    return payload


def get_frontend_redirect_url(
    status: str = "",
    origin: Optional[str] = None,
    return_to: Optional[str] = None,
) -> str:
    """Get the frontend redirect URL."""
    base = origin or os.environ.get("FRONTEND_ORIGIN") or os.environ.get("PUBLIC_URL") or ""
    base = base.rstrip("/")
    callback_path = "/gmail/callback"
    target = f"{base}{callback_path}" if base else callback_path

    params = {}
    if status:
        params["status"] = status
    if return_to:
        params["return_to"] = return_to
    if params:
        target = f"{target}?{urlencode(params)}"
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
        safe_return_to = _normalize_return_to(return_to)
        origin = _resolve_frontend_origin(request)
        state = _encode_oauth_state(
            user_id=current_user.user_id,
            origin=origin,
            return_to=safe_return_to,
        )
        auth_url, _ = service.get_authorization_url(state=state)

        # Backward-compatible best-effort state storage for in-flight redirects;
        # callback validation no longer depends on Redis availability.
        redis.set(
            f"gmail_oauth_state:{current_user.user_id}",
            {
                "state": state,
                "user_id": current_user.user_id,
                "return_to": safe_return_to,
                "origin": origin,
            },
            ttl=STATE_TTL_SECONDS,
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
        decoded_state = _decode_oauth_state(state)
        if decoded_state:
            user_id = decoded_state.get("user_id")
            redirect_origin = decoded_state.get("origin")
            redirect_return_to = decoded_state.get("return_to")
        else:
            # Fallback for states issued before signed-state rollout.
            for key in redis.scan_keys("gmail_oauth_state:*"):
                stored_data = redis.get(key)
                if stored_data and stored_data.get("state") == state:
                    user_id = stored_data.get("user_id")
                    redirect_origin = stored_data.get("origin")
                    redirect_return_to = stored_data.get("return_to")
                    redis.delete(key)
                    break

    if error:
        return RedirectResponse(
            url=get_frontend_redirect_url(
                "error",
                origin=redirect_origin,
                return_to=redirect_return_to,
            )
        )

    if not code or not state or not user_id:
        return RedirectResponse(
            url=get_frontend_redirect_url(
                "invalid_state",
                origin=redirect_origin,
                return_to=redirect_return_to,
            )
        )
    
    try:
        service = GmailService(user_id)
        service.exchange_code_for_tokens(code)
        return RedirectResponse(
            url=get_frontend_redirect_url(
                "connected",
                origin=redirect_origin,
                return_to=redirect_return_to,
            )
        )
    except GmailOAuthError:
        return RedirectResponse(
            url=get_frontend_redirect_url(
                "error",
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

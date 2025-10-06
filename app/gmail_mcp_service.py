import datetime
import logging
import os
from typing import Dict, Optional
from urllib.parse import urlencode

import requests

from database.db_manager import DatabaseManager
logger = logging.getLogger(__name__)
logger = logging.getLogger(__name__)


class GmailMCPService:
    """Service wrapper for interacting with a Gmail MCP server."""

    _SCOPES = "https://www.googleapis.com/auth/gmail.compose https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.readonly"

    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id
        self.server_url = os.getenv("MCP_SERVER_URL", "").rstrip("/")
        self.client_id = os.getenv("GMAIL_CLIENT_ID")
        self.client_secret = os.getenv("GMAIL_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GMAIL_REDIRECT_URI")
        self.db_manager = DatabaseManager()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def check_availability(self) -> Dict[str, Optional[bool]]:
        """Return availability/authentication status for the current user."""

        configured = self._is_configured()
        status = {
            "available": configured,
            "authenticated": False,
            "requires_auth": False,
            "message": None,
        }

        if not configured:
            status.update({
                "message": "Gmail MCP server is not configured. Set MCP_SERVER_URL, GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, and GMAIL_REDIRECT_URI.",
            })
            return status

        if not self.user_id:
            status.update({
                "message": "User context not provided; skipping Gmail authentication lookup.",
                "requires_auth": True,
            })
            return status

        auth_record = self.db_manager.get_gmail_auth(self.user_id)
        authenticated = bool(auth_record and auth_record.get("access_token"))
        status["authenticated"] = authenticated
        status["requires_auth"] = not authenticated

        if not authenticated:
            status["message"] = "Connect your Gmail account to create drafts automatically."

        return status

    def get_auth_url(self, state: Optional[str] = None) -> str:
        """Return the OAuth authorization URL for the Gmail MCP server."""

        self._require_config()

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self._SCOPES,
            "access_type": "offline",
            "prompt": "consent",
        }

        if state:
            params["state"] = state

        authorize_endpoint = f"{self.server_url}/oauth/authorize"
        return f"{authorize_endpoint}?{urlencode(params)}"

    def exchange_code_for_tokens(self, authorization_code: str) -> Dict[str, str]:
        """Exchange authorization code for access & refresh tokens."""

        self._require_config()

        if not authorization_code:
            raise ValueError("Authorization code is required")

        token_endpoint = f"{self.server_url}/oauth/token"
        payload = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        response = requests.post(token_endpoint, data=payload, timeout=20)
        if response.status_code != 200:
            logger.error("Failed to exchange authorization code: %s", response.text)
            raise RuntimeError("Failed to exchange Gmail authorization code")

        token_data = response.json()
        self._persist_tokens(token_data)
        return token_data

    def refresh_access_token(self) -> Optional[str]:
        """Refresh the access token if refresh token is stored."""

        self._require_config()

        auth_record = self._require_auth_record()
        refresh_token = auth_record.get("refresh_token")
        if not refresh_token:
            raise RuntimeError("No refresh token available; re-authorise Gmail")

        token_endpoint = f"{self.server_url}/oauth/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        response = requests.post(token_endpoint, data=payload, timeout=20)
        if response.status_code != 200:
            logger.error("Failed to refresh Gmail access token: %s", response.text)
            raise RuntimeError("Failed to refresh Gmail access token")

        token_data = response.json()
        self._persist_tokens(token_data, allow_refresh_fallback=True)
        return token_data.get("access_token")

    def create_draft(
        self,
        to_email: str,
        subject: str,
        body: str,
        cc: Optional[list] = None,
        bcc: Optional[list] = None,
        is_html: bool = True,
    ) -> Dict[str, Optional[str]]:
        """Create a Gmail draft using the MCP server."""

        self._require_config()
        if not self.user_id:
            raise ValueError("User context is required to create a Gmail draft")

        access_token = self._ensure_active_access_token()

        payload = {
            "to": [to_email],
            "cc": cc or [],
            "bcc": bcc or [],
            "subject": subject,
            "body": body,
            "is_html": is_html,
        }

        draft_endpoint = f"{self.server_url}/gmail/create-draft"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        response = requests.post(draft_endpoint, json=payload, headers=headers, timeout=20)
        if response.status_code != 200:
            logger.error("Failed to create Gmail draft: %s", response.text)
            return {
                "success": False,
                "error": response.json().get("error") if response.headers.get("Content-Type", "").startswith("application/json") else response.text,
            }

        result = response.json()
        return {
            "success": True,
            "draft_id": result.get("draft_id"),
            "message": result.get("message", "Draft created successfully"),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _is_configured(self) -> bool:
        return bool(self.server_url and self.client_id and self.client_secret and self.redirect_uri)

    def _require_config(self) -> None:
        if not self._is_configured():
            raise RuntimeError("Gmail MCP server is not fully configured")

    def _require_auth_record(self) -> Dict[str, any]:
        if not self.user_id:
            raise RuntimeError("User context required")
        record = self.db_manager.get_gmail_auth(self.user_id)
        if not record:
            raise RuntimeError("Gmail account not connected for this user")
        return record

    def _persist_tokens(self, token_data: Dict[str, any], allow_refresh_fallback: bool = False) -> None:
        if not self.user_id:
            logger.warning("Skipping token persistence - no user context available")
            return

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)

        if not access_token:
            raise RuntimeError("Token response missing access_token")

        # When refreshing tokens the refresh token might be omitted.
        if not refresh_token and not allow_refresh_fallback:
            raise RuntimeError("Token response missing refresh_token")

        if allow_refresh_fallback and not refresh_token:
            existing = self.db_manager.get_gmail_auth(self.user_id)
            refresh_token = existing.get("refresh_token") if existing else None

        expiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=int(expires_in))

        self.db_manager.save_gmail_auth(
            user_id=self.user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expiry=expiry,
        )

    def _ensure_active_access_token(self) -> str:
        auth_record = self._require_auth_record()
        access_token = auth_record.get("access_token")
        expiry = auth_record.get("token_expiry")

        if access_token and expiry:
            if isinstance(expiry, str):
                try:
                    expiry = datetime.datetime.fromisoformat(expiry)
                except ValueError:
                    logger.warning("Invalid token expiry format stored; forcing refresh")
                    expiry = datetime.datetime.utcnow()

            # Refresh token if it's due to expire within the next minute
            if expiry <= datetime.datetime.utcnow() + datetime.timedelta(seconds=60):
                logger.info("Gmail access token expired or about to expire; refreshing")
                access_token = self.refresh_access_token()

        if not access_token:
            raise RuntimeError("No Gmail access token available. Please reconnect your Gmail account.")

        return access_token



import base64
import datetime
import json
import logging
import os
from email.mime.text import MIMEText
from typing import Optional, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]
CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    "gcp-oauth.keys.json",
)


class GmailOAuthError(Exception):
    """Custom exception for Gmail OAuth related issues."""


class GmailService:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.db = DatabaseManager()
        self.client_config = self._load_client_config()
        self.redirect_uri = self._determine_redirect_uri()

    def _load_client_config(self) -> dict:
        env_config = os.environ.get("GCP_OAUTH_KEYS")
        if env_config:
            try:
                try:
                    parsed = json.loads(env_config)
                except json.JSONDecodeError:
                    decoded = base64.b64decode(env_config).decode("utf-8")
                    parsed = json.loads(decoded)
                return parsed
            except Exception as exc:
                raise GmailOAuthError("Invalid GCP_OAUTH_KEYS environment value") from exc

        if not os.path.exists(CONFIG_PATH):
            raise GmailOAuthError(
                "Gmail API is not configured. Provide config/gcp-oauth.keys.json or set GCP_OAUTH_KEYS."
            )
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as exc:
            raise GmailOAuthError("Invalid Google OAuth configuration file") from exc

    def _determine_redirect_uri(self) -> str:
        env_redirect = os.environ.get("GMAIL_REDIRECT_URI")
        if env_redirect:
            return env_redirect
        base_url = os.environ.get("APP_BASE_URL", "http://localhost:5000")
        return f"{base_url.rstrip('/')}/api/gmail/oauth2callback"

    def _create_flow(self) -> Flow:
        return Flow.from_client_config(
            self.client_config,
            scopes=SCOPES,
            redirect_uri=self.redirect_uri,
        )

    def get_authorization_url(self) -> Tuple[str, str]:
        flow = self._create_flow()
        auth_url, state = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true",
        )
        return auth_url, state

    def exchange_code_for_tokens(self, code: str) -> None:
        flow = self._create_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials
        profile = self._fetch_user_profile(credentials)
        self._store_credentials(credentials, profile.get("emailAddress"))

    def _fetch_user_profile(self, credentials: Credentials) -> dict:
        service = build("gmail", "v1", credentials=credentials)
        return service.users().getProfile(userId="me").execute()

    def _store_credentials(self, credentials: Credentials, email: Optional[str]) -> None:
        existing = self.db.get_gmail_token(self.user_id)
        refresh_token = credentials.refresh_token or (existing or {}).get("refresh_token")
        if not refresh_token:
            raise GmailOAuthError("Unable to obtain Gmail refresh token")

        expiry = credentials.expiry
        self.db.save_gmail_token(
            self.user_id,
            access_token=credentials.token,
            refresh_token=refresh_token,
            expiry=expiry,
            scope=" ".join(credentials.scopes or []),
            email=email,
        )

    def _load_credentials(self) -> Optional[Credentials]:
        token_record = self.db.get_gmail_token(self.user_id)
        if not token_record:
            return None

        credentials = Credentials(
            token=token_record.get("access_token"),
            refresh_token=token_record.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self._client_id,
            client_secret=self._client_secret,
            scopes=(token_record.get("scope") or "").split(),
        )
        expiry_str = token_record.get("token_expiry")
        if expiry_str:
            try:
                credentials.expiry = datetime.datetime.fromisoformat(expiry_str)
            except ValueError:
                credentials.expiry = None

        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
                self._store_credentials(credentials, token_record.get("email"))
            except Exception as exc:
                # Token refresh can fail for many reasons (revoked, expired, etc.)
                # This is expected - log as INFO and raise for proper handling upstream
                logger.info(f"Gmail token refresh failed for user {self.user_id}: {exc.__class__.__name__}")
                raise GmailOAuthError("Gmail token expired or revoked") from exc

        return credentials

    @property
    def _client_id(self) -> str:
        return self._client_secrets.get("client_id")

    @property
    def _client_secret(self) -> str:
        return self._client_secrets.get("client_secret")

    @property
    def _client_secrets(self) -> dict:
        if "web" in self.client_config:
            return self.client_config["web"]
        if "installed" in self.client_config:
            return self.client_config["installed"]
        raise GmailOAuthError("Unsupported Google OAuth client configuration")

    def get_status(self) -> dict:
        try:
            credentials = self._load_credentials()
        except GmailOAuthError as e:
            # Expected when token expires - handle gracefully without ERROR logs
            logger.info(f"Gmail token invalid/expired for user {self.user_id}, clearing token")
            self.db.delete_gmail_token(self.user_id)
            return {"availability": "configured", "authorized": False}

        if not credentials:
            return {"availability": "configured", "authorized": False}

        token_record = self.db.get_gmail_token(self.user_id) or {}
        return {
            "availability": "authorized",
            "authorized": True,
            "email": token_record.get("email"),
        }

    def disconnect(self) -> None:
        self.db.delete_gmail_token(self.user_id)

    def create_draft(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        cc: Optional[list] = None,
        bcc: Optional[list] = None,
    ) -> dict:
        credentials = self._load_credentials()
        if not credentials:
            raise GmailOAuthError("Gmail account not connected")

        try:
            service = build("gmail", "v1", credentials=credentials)
            message = MIMEText(body_html, "html")
            message["To"] = to_email
            message["Subject"] = subject
            if cc:
                message["Cc"] = ", ".join(cc)
            if bcc:
                message["Bcc"] = ", ".join(bcc)

            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            draft_body = {"message": {"raw": encoded_message}}
            draft = (
                service.users()
                .drafts()
                .create(userId="me", body=draft_body)
                .execute()
            )
            return draft
        except HttpError as exc:
            logger.exception("Gmail API error while creating draft")
            raise GmailOAuthError("Gmail API error") from exc

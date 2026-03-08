"""JWT authentication and security utilities."""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel

from app.config import get_settings


class TokenData(BaseModel):
    """Token payload data."""
    user_id: str
    email: Optional[str] = None
    token_type: str = "access"  # 'access' or 'refresh'


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt or legacy SHA256 hash."""
    if not hashed_password:
        return False
    if hashed_password.startswith("$2"):
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    legacy_hash = hashlib.sha256(plain_password.encode()).hexdigest()
    return legacy_hash == hashed_password


def password_needs_rehash(hashed_password: str) -> bool:
    """Return True when a stored password should be upgraded to bcrypt."""
    if not hashed_password:
        return True
    return not hashed_password.startswith("$2")


def create_access_token(user_id: str, email: str) -> str:
    """Create a JWT access token."""
    settings = get_settings()
    
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "jti": str(uuid.uuid4()),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str, email: str) -> str:
    """Create a JWT refresh token."""
    settings = get_settings()
    
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    
    payload = {
        "sub": user_id,
        "email": email,
        "type": "refresh",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "jti": str(uuid.uuid4()),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_tokens(user_id: str, email: str) -> Tuple[str, str]:
    """Create both access and refresh tokens."""
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id, email)
    return access_token, refresh_token


def decode_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT token."""
    settings = get_settings()
    
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={
                "verify_aud": bool(settings.jwt_audience),
                "verify_iss": bool(settings.jwt_issuer),
            },
        )
        
        user_id = payload.get("sub")
        email = payload.get("email")
        token_type = payload.get("type", "access")
        
        if user_id is None:
            return None
            
        return TokenData(user_id=user_id, email=email, token_type=token_type)
        
    except JWTError:
        return None


def verify_access_token(token: str) -> Optional[TokenData]:
    """Verify an access token and return its data."""
    token_data = decode_token(token)
    
    if token_data is None or token_data.token_type != "access":
        return None
        
    return token_data


def verify_refresh_token(token: str) -> Optional[TokenData]:
    """Verify a refresh token and return its data."""
    token_data = decode_token(token)
    
    if token_data is None or token_data.token_type != "refresh":
        return None
        
    return token_data

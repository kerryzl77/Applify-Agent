"""JWT authentication and security utilities."""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from jose import JWTError, jwt
from pydantic import BaseModel

from app.config import get_settings


class TokenData(BaseModel):
    """Token payload data."""
    user_id: str
    email: Optional[str] = None
    token_type: str = "access"  # 'access' or 'refresh'


def hash_password(password: str) -> str:
    """Hash a password using SHA256 (matching existing db_manager implementation)."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return hash_password(plain_password) == hashed_password


def create_access_token(user_id: str, email: str) -> str:
    """Create a JWT access token."""
    settings = get_settings()
    
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
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
            algorithms=[settings.jwt_algorithm]
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

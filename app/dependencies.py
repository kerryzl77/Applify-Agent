"""Shared FastAPI dependencies."""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.security import verify_access_token, TokenData
from database.db_manager import DatabaseManager
from app.redis_manager import RedisManager

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)


# Singleton instances
_db_manager: Optional[DatabaseManager] = None
_redis_manager: Optional[RedisManager] = None


def get_db() -> DatabaseManager:
    """Get database manager singleton."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def get_redis() -> RedisManager:
    """Get Redis manager singleton."""
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = RedisManager()
    return _redis_manager


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: DatabaseManager = Depends(get_db),
) -> TokenData:
    """
    Dependency to get the current authenticated user from JWT token.
    
    Raises HTTPException 401 if not authenticated.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    token_data = verify_access_token(token)
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Optionally verify user still exists in database
    user = db.get_user_by_id(token_data.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_data


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[TokenData]:
    """
    Dependency to optionally get current user. Returns None if not authenticated.
    """
    if credentials is None:
        return None
    
    token = credentials.credentials
    return verify_access_token(token)

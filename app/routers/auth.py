"""Authentication router with JWT tokens."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas import (
    UserRegister,
    UserLogin,
    Token,
    TokenRefresh,
    UserResponse,
    AuthCheckResponse,
    SuccessResponse,
    ErrorResponse,
)
from app.security import (
    create_tokens,
    verify_refresh_token,
    hash_password,
)
from app.dependencies import get_db, get_current_user, TokenData
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=Token)
async def register(
    user_data: UserRegister,
    db: DatabaseManager = Depends(get_db),
):
    """Register a new user and return JWT tokens."""
    # Validate passwords match
    if user_data.password != user_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )
    
    # Register user
    success, result = db.register_user(user_data.email, user_data.password)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result,
        )
    
    user_id = result
    
    # Create tokens
    access_token, refresh_token = create_tokens(user_id, user_data.email)
    
    logger.info(f"User registered: {user_data.email}")
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: DatabaseManager = Depends(get_db),
):
    """Authenticate user and return JWT tokens."""
    success, result = db.verify_user(credentials.email, credentials.password)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = result
    
    # Create tokens
    access_token, refresh_token = create_tokens(user_id, credentials.email)
    
    logger.info(f"User logged in: {credentials.email}")
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/refresh", response_model=Token)
async def refresh_tokens(
    token_data: TokenRefresh,
    db: DatabaseManager = Depends(get_db),
):
    """Refresh access token using refresh token."""
    # Verify refresh token
    payload = verify_refresh_token(token_data.refresh_token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify user still exists
    user = db.get_user_by_id(payload.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create new tokens
    access_token, refresh_token = create_tokens(payload.user_id, user["email"])
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    current_user: TokenData = Depends(get_current_user),
):
    """
    Logout user.
    
    Note: With stateless JWT, logout is handled client-side by deleting tokens.
    This endpoint exists for API consistency and could be extended to 
    blacklist refresh tokens in Redis if needed.
    """
    logger.info(f"User logged out: {current_user.email}")
    
    return SuccessResponse(success=True, message="Logout successful")


@router.get("/check", response_model=AuthCheckResponse)
async def check_auth(
    current_user: TokenData = Depends(get_current_user),
):
    """Check if user is authenticated."""
    return AuthCheckResponse(
        authenticated=True,
        user_id=current_user.user_id,
        email=current_user.email,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: TokenData = Depends(get_current_user),
):
    """Get current user information."""
    return UserResponse(
        user_id=current_user.user_id,
        email=current_user.email or "",
    )

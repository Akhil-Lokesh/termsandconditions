"""
Authentication endpoints.

Provides user registration, login, and token management with JWT.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import logging

from app.api.deps import get_db, get_current_active_user
from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token
from app.utils.security import (
    get_password_hash,
    verify_password,
    create_access_token,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
    description="Create a new user account with email and password.",
)
async def signup(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    """Register a new user account."""
    logger.info(f"Signup attempt for email: {user_data.email}")

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()

    if existing_user:
        logger.warning(f"Signup failed: Email already registered: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered. Please use a different email or login.",
        )

    # Validate password strength
    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long.",
        )

    try:
        # Create user
        user = User(
            email=user_data.email.lower().strip(),
            hashed_password=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            is_active=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"✓ New user registered: {user.email}")

        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
        )

    except Exception as e:
        logger.error(f"Signup failed: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account.",
        )


@router.post(
    "/login",
    response_model=Token,
    summary="Login",
    description="Login with email and password to receive JWT access token.",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login and receive JWT access token."""
    logger.info(f"Login attempt for email: {form_data.username}")

    # Find user by email
    user = db.query(User).filter(
        User.email == form_data.username.lower().strip()
    ).first()

    # Verify user exists and password is correct
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Login failed: Invalid credentials for {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user account is active
    if not user.is_active:
        logger.warning(f"Login failed: Inactive account: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=access_token_expires,
    )

    logger.info(f"✓ User logged in: {user.email}")

    return Token(
        access_token=access_token,
        token_type="bearer",
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User",
    description="Get current authenticated user's profile.",
)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
):
    """Get current user's profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        created_at=current_user.created_at,
    )

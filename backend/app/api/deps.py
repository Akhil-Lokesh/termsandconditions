"""
API dependencies for dependency injection.

Provides dependency functions for:
- Database session management
- User authentication
- Service instance retrieval (OpenAI, Pinecone, Cache)
"""

import logging
from typing import Generator
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.services.openai_service import OpenAIService
from app.services.pinecone_service import PineconeService
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        token: JWT token
        db: Database session
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user.

    Args:
        current_user: Current user from token

    Returns:
        Active user

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user


# ============================================================================
# Service Dependencies (Week 2)
# ============================================================================


def get_openai_service(request: Request) -> OpenAIService:
    """
    Get OpenAI service instance from app state.

    Args:
        request: FastAPI request object

    Returns:
        OpenAI service instance

    Raises:
        HTTPException: If service not initialized
    """
    service = request.app.state.openai
    if service is None:
        logger.error("OpenAI service not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI service not available",
        )
    return service


def get_pinecone_service(request: Request) -> PineconeService:
    """
    Get Pinecone service instance from app state.

    Args:
        request: FastAPI request object

    Returns:
        Pinecone service instance

    Raises:
        HTTPException: If service not initialized
    """
    service = request.app.state.pinecone
    if service is None:
        logger.error("Pinecone service not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pinecone service not available",
        )
    return service


def get_cache_service(request: Request) -> CacheService:
    """
    Get cache service instance from app state.

    Args:
        request: FastAPI request object

    Returns:
        Cache service instance (or None if not available)
    """
    # Cache is optional - return None if not available
    return request.app.state.cache

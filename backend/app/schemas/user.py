"""User schemas for request/response validation."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(BaseModel):
    """Schema for user creation."""

    email: EmailStr
    password: str = Field(
        ..., min_length=8, description="Password (minimum 8 characters)"
    )
    full_name: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema for user update."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)


class UserResponse(UserBase):
    """Schema for user response."""

    id: str
    is_active: bool
    is_superuser: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """Schema for authentication token."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for token payload data."""

    user_id: Optional[str] = None
    email: Optional[str] = None

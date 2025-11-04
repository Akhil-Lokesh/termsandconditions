"""Clause schemas for request/response validation."""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class ClauseBase(BaseModel):
    """Base clause schema."""

    section: Optional[str] = None
    subsection: Optional[str] = None
    clause_number: Optional[str] = None
    text: str


class ClauseCreate(ClauseBase):
    """Schema for clause creation."""

    document_id: str
    level: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class ClauseResponse(ClauseBase):
    """Schema for clause response."""

    id: str
    document_id: str
    level: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}

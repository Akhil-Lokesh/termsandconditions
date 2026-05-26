"""
Query schemas for API request/response validation.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Query request schema."""

    document_id: str
    question: str = Field(..., min_length=3, max_length=2000)


class Citation(BaseModel):
    """Citation schema for query responses."""

    clause_id: str
    section: str
    text: str
    relevance_score: float


class QueryResponse(BaseModel):
    """Query response schema."""

    question: str
    answer: str
    citations: List[Citation] = []
    confidence: Optional[float] = None  # Confidence score (0.0 - 1.0)
    sources: List[str] = []
    warnings: Optional[List[str]] = []
    related_anomalies: Optional[List[str]] = []

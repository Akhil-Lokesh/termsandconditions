"""
Query schemas for API request/response validation.
"""

from typing import List, Optional
from pydantic import BaseModel


class QueryRequest(BaseModel):
    """Query request schema."""
    document_id: str
    question: str


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
    sources: List[str] = []
    warnings: Optional[List[str]] = []
    related_anomalies: Optional[List[str]] = []

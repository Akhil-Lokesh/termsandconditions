"""Anomaly schemas for request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class AnomalyBase(BaseModel):
    """Base anomaly schema."""
    clause_text: str
    section: Optional[str] = None
    clause_number: Optional[str] = None
    severity: str = Field(..., pattern="^(low|medium|high)$")
    explanation: Optional[str] = None
    prevalence: Optional[float] = Field(None, ge=0.0, le=1.0)
    risk_flags: Optional[List[str]] = None


class AnomalyCreate(AnomalyBase):
    """Schema for anomaly creation."""
    document_id: str


class AnomalyResponse(AnomalyBase):
    """Schema for anomaly response."""
    id: str
    document_id: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class AnomalyListResponse(BaseModel):
    """Schema for list of anomalies."""
    anomalies: List[AnomalyResponse]
    total: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int


class AnomalyStatsResponse(BaseModel):
    """Schema for anomaly statistics."""
    total_anomalies: int
    severity_distribution: Dict[str, int]
    common_risk_flags: List[Dict[str, Any]]
    average_prevalence: float


# Alias for backwards compatibility
AnomalyStats = AnomalyStatsResponse

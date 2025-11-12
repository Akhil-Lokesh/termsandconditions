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

    model_config = {"from_attributes": True}


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


# === Stage 6 Pipeline Schemas ===


class ConfidenceCalibration(BaseModel):
    """Confidence calibration metadata."""

    raw_confidence: float = Field(..., ge=0.0, le=1.0)
    calibrated_confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_tier: str = Field(..., pattern="^(HIGH|MODERATE|LOW)$")
    tier_label: str
    explanation: str
    adjustment: float


class ScoringBreakdown(BaseModel):
    """Scoring breakdown for ranking."""

    severity_weight: float
    confidence: float
    user_relevance: float
    base_score: float
    bonuses: Dict[str, float]
    bonus_total: float


class RankedAnomaly(BaseModel):
    """Anomaly with ranking metadata."""

    clause_number: Optional[str] = None
    clause_text: str
    severity: str
    risk_category: str
    confidence_calibration: ConfidenceCalibration
    detected_indicators: List[Dict[str, Any]]
    explanation: Optional[str] = None
    consumer_impact: Optional[str] = None
    recommendation: Optional[str] = None
    ranking_score: float
    scoring_breakdown: ScoringBreakdown
    is_compound_risk: Optional[bool] = False
    compound_risk_type: Optional[str] = None
    compound_risk_name: Optional[str] = None


class CompoundRisk(BaseModel):
    """Compound risk pattern."""

    compound_risk_type: str
    name: str
    description: str
    compound_severity: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    related_clauses: List[str]
    consumer_impact: str
    recommendation: str


class TopCategory(BaseModel):
    """Top risk category."""

    category: str
    count: int


class RankingMetadata(BaseModel):
    """Ranking metadata."""

    total_detected: int
    total_shown: int
    total_suppressed: int
    suppression_rate: float = Field(..., ge=0.0, le=1.0)
    avg_score: float
    top_score: float
    top_categories: List[TopCategory]
    alert_budget_applied: bool
    user_preferences_applied: bool


class PipelinePerformance(BaseModel):
    """Pipeline performance metrics."""

    stage1_detections: int
    stage2_filtered: int
    stage3_clustered: int
    stage4_compounds: int
    stage5_calibrated: int
    stage6_ranked: int
    total_clauses_analyzed: int
    total_processing_time_ms: float


class AnomalyReportResponse(BaseModel):
    """Complete anomaly report from 6-stage pipeline."""

    document_id: str
    company_name: Optional[str] = None
    analysis_date: str
    overall_risk_score: float = Field(..., ge=1.0, le=10.0)
    high_severity_alerts: List[RankedAnomaly]
    medium_severity_alerts: List[RankedAnomaly]
    low_severity_alerts: List[RankedAnomaly]
    suppressed_alerts_count: int
    total_anomalies_detected: int
    total_alerts_shown: int
    compound_risks: List[CompoundRisk]
    ranking_metadata: RankingMetadata
    pipeline_performance: PipelinePerformance


# === Feedback Schemas ===


class FeedbackRequest(BaseModel):
    """Request schema for user feedback."""

    user_action: str = Field(
        ...,
        pattern="^(helpful|dismiss|not_applicable|acted_on)$",
        description="User action: helpful, dismiss, not_applicable, acted_on"
    )
    feedback_text: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional text feedback from user"
    )
    confidence_at_detection: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score when anomaly was shown"
    )


class FeedbackStats(BaseModel):
    """Feedback collection statistics."""

    buffer_size: int
    buffer_capacity: int
    buffer_progress: float = Field(..., ge=0.0, le=1.0)
    total_feedback_collected: int
    retrain_count: int
    last_retrain_date: Optional[str] = None
    dismissal_rate: float = Field(..., ge=0.0, le=1.0)
    accuracy: float = Field(..., ge=0.0, le=1.0)
    dismissal_threshold: float
    calibrator_fitted: bool


class FeedbackResponse(BaseModel):
    """Response schema for feedback submission."""

    success: bool
    message: str
    feedback_stats: FeedbackStats


# === Performance Metrics Schemas ===


class PerformanceMetrics(BaseModel):
    """System performance metrics."""

    total_documents_analyzed: int
    total_anomalies_detected: int
    total_feedback_collected: int
    false_positive_rate: float = Field(..., ge=0.0, le=1.0)
    dismissal_rate: float = Field(..., ge=0.0, le=1.0)
    average_alerts_per_document: float
    expected_calibration_error: Optional[float] = Field(None, ge=0.0, le=1.0)
    calibrator_fitted: bool
    retrain_count: int
    last_retrain_date: Optional[str] = None
    avg_processing_time_ms: float
    pipeline_health_status: str = Field(
        ...,
        pattern="^(healthy|warning|critical)$"
    )

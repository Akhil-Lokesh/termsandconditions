"""Anomaly schemas for request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# =============================================================================
# INVERTED FUNNEL ENUMS (mirror constants.py for API responses)
# =============================================================================

class ThreatLevelEnum(str, Enum):
    """Threat level based on consumer harm potential."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class CommonnessLevelEnum(str, Enum):
    """How common a pattern is across T&Cs."""
    UNIVERSAL = "universal"
    VERY_COMMON = "very_common"
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    VERY_RARE = "very_rare"


class DisplayCategoryEnum(str, Enum):
    """Display category for UI presentation."""
    UNUSUAL_DANGEROUS = "unusual_dangerous"    # Red - Rare + High threat
    COMMON_DANGEROUS = "common_dangerous"      # Orange - Common + High threat
    UNUSUAL_MINOR = "unusual_minor"            # Yellow - Rare + Low threat
    STANDARD_TERMS = "standard_terms"          # Gray - Common + Low threat


# =============================================================================
# INVERTED FUNNEL RESPONSE SCHEMAS
# =============================================================================

class InvertedFunnelAnomaly(BaseModel):
    """
    Single anomaly from the inverted funnel system.

    Contains full context: detection info, commonness, threat level,
    and user importance score.
    """
    # Basic identification
    clause_number: Optional[str] = None
    clause_text: str
    section: Optional[str] = None

    # Detection info (Layer 1)
    detected_patterns: List[str] = Field(default_factory=list)
    detection_method: str = "pattern"
    raw_confidence: float = Field(0.0, ge=0.0, le=1.0)

    # Commonness info (Layer 2)
    commonness_level: CommonnessLevelEnum = CommonnessLevelEnum.COMMON
    commonness_percentage: float = Field(50.0, ge=0.0, le=100.0)
    industry_commonness: Optional[CommonnessLevelEnum] = None

    # Threat info (Layer 3)
    threat_level: ThreatLevelEnum = ThreatLevelEnum.MEDIUM
    threat_score: float = Field(5.0, ge=0.0, le=10.0)
    why_threatening: str = ""

    # Combined ranking (Layer 4)
    user_importance_score: float = Field(0.0, ge=0.0)
    display_category: DisplayCategoryEnum = DisplayCategoryEnum.STANDARD_TERMS

    # Legacy compatibility
    severity: str = Field("medium", pattern="^(low|medium|high|critical)$")
    risk_score: float = Field(5.0, ge=0.0, le=10.0)

    model_config = {"from_attributes": True}


class InvertedFunnelCategorySummary(BaseModel):
    """Summary of anomalies by display category."""
    unusual_dangerous_count: int = 0
    common_dangerous_count: int = 0
    unusual_minor_count: int = 0
    standard_terms_count: int = 0


class InvertedFunnelReport(BaseModel):
    """
    Complete report from the inverted funnel detection system.

    Anomalies are sorted by user_importance_score (highest first).
    """
    document_id: str
    company_name: Optional[str] = None
    analysis_date: str

    # Overall metrics
    overall_risk_score: float = Field(..., ge=1.0, le=10.0)
    total_clauses_analyzed: int
    total_anomalies_detected: int

    # Anomalies by display category (sorted by importance within each)
    unusual_dangerous: List[InvertedFunnelAnomaly] = Field(
        default_factory=list,
        description="Rare + High/Critical threat - RED FLAG items"
    )
    common_dangerous: List[InvertedFunnelAnomaly] = Field(
        default_factory=list,
        description="Common + High/Critical threat - Know the risk"
    )
    unusual_minor: List[InvertedFunnelAnomaly] = Field(
        default_factory=list,
        description="Rare + Low threat - FYI items"
    )
    standard_terms: List[InvertedFunnelAnomaly] = Field(
        default_factory=list,
        description="Common + Low threat - Expand to see"
    )

    # Category summary
    category_summary: InvertedFunnelCategorySummary

    # Threat level distribution
    threat_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Count by threat level (critical, high, medium, low, info)"
    )

    # Commonness distribution
    commonness_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Count by commonness level"
    )

    # Top patterns detected
    top_patterns: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Most frequently detected patterns with counts"
    )

    # Legacy compatibility
    high_severity_count: int = 0
    medium_severity_count: int = 0
    low_severity_count: int = 0


# =============================================================================
# ORIGINAL SCHEMAS (kept for backward compatibility)
# =============================================================================

class AnomalyBase(BaseModel):
    """Base anomaly schema."""

    clause_text: str
    section: Optional[str] = None
    clause_number: Optional[str] = None
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    explanation: Optional[str] = None
    consumer_impact: Optional[str] = None
    recommendation: Optional[str] = None
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
    critical_risk_count: int = 0
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int


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
    section: Optional[str] = None
    severity: str
    risk_category: str
    prevalence: Optional[float] = Field(None, ge=0.0, le=1.0)
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
    stage2_passed: int
    stage2_filtered_out: int
    stage3_clustered: int
    stage4_compounds: int
    stage5_calibrated: int
    stage6_ranked: int
    total_clauses_analyzed: int
    total_processing_time_ms: float


class CompetitorInfo(BaseModel):
    """Information about a competitor for comparison."""

    company_name: str
    avg_risk_score: float = Field(..., ge=1.0, le=10.0)
    notable_issues: List[str]


class CompetitiveBenchmark(BaseModel):
    """Competitive benchmark analysis comparing against industry peers."""

    industry: str
    industry_average_risk: float = Field(..., ge=1.0, le=10.0)
    percentile_rank: int = Field(..., ge=0, le=100, description="0=best, 100=worst")
    risk_comparison: str = Field(..., description="better/similar/worse than average")
    peer_count: int = Field(..., description="Number of peers in comparison")
    better_alternatives: List[CompetitorInfo] = Field(
        default_factory=list,
        description="Competitors with lower risk scores"
    )
    worse_alternatives: List[CompetitorInfo] = Field(
        default_factory=list,
        description="Competitors with higher risk scores"
    )
    unique_risks: List[str] = Field(
        default_factory=list,
        description="Risks unique to this document vs peers"
    )
    missing_protections: List[str] = Field(
        default_factory=list,
        description="Consumer protections this document lacks vs better peers"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Actionable recommendations based on comparison"
    )
    summary: str = Field(..., description="One-sentence summary of competitive position")


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
    competitive_benchmark: Optional[CompetitiveBenchmark] = Field(
        None,
        description="Competitive comparison against industry peers"
    )


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

"""
Analysis Log model for tracking two-stage GPT-5 analysis history.

Tracks every analysis with cost, stage, confidence, and results.
Used for analytics, cost tracking, and quality monitoring.
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base import Base


class AnalysisLog(Base):
    """
    Log of two-stage analysis executions.

    Tracks every analysis for cost monitoring, quality metrics,
    and escalation rate tracking.
    """

    __tablename__ = "analysis_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Analysis execution details
    stage_reached = Column(Integer, nullable=False)  # 1 or 2
    escalated = Column(Boolean, default=False, nullable=False)  # Was Stage 2 called?

    # Stage 1 results
    stage1_confidence = Column(Float, nullable=True)  # 0.0-1.0
    stage1_risk = Column(String, nullable=True)  # low, medium, high
    stage1_cost = Column(Float, nullable=True)  # USD
    stage1_processing_time = Column(Float, nullable=True)  # seconds
    stage1_result = Column(JSON, nullable=True)  # Full Stage 1 response

    # Stage 2 results (if escalated)
    stage2_confidence = Column(Float, nullable=True)  # 0.8-1.0
    stage2_risk = Column(String, nullable=True)  # low, medium, high
    stage2_cost = Column(Float, nullable=True)  # USD
    stage2_processing_time = Column(Float, nullable=True)  # seconds
    stage2_result = Column(JSON, nullable=True)  # Full Stage 2 response

    # Final results
    final_risk = Column(String, nullable=False)  # low, medium, high
    final_confidence = Column(Float, nullable=False)  # 0.0-1.0
    total_cost = Column(Float, nullable=False)  # USD (stage1 + stage2)
    total_processing_time = Column(Float, nullable=False)  # seconds

    # Anomalies detected
    anomaly_count = Column(Integer, default=0)
    high_risk_count = Column(Integer, default=0)
    medium_risk_count = Column(Integer, default=0)
    low_risk_count = Column(Integer, default=0)

    # Metadata
    company_name = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="analysis_logs")
    user = relationship("User", back_populates="analysis_logs")

    def __repr__(self) -> str:
        return (
            f"<AnalysisLog(id={self.id}, doc={self.document_id}, "
            f"stage={self.stage_reached}, cost=${self.total_cost:.6f})>"
        )

    @property
    def cost_efficiency(self) -> float:
        """
        Calculate cost efficiency vs single-stage.

        Returns percentage saved compared to $0.015 single-stage cost.
        """
        SINGLE_STAGE_COST = 0.015
        if self.total_cost == 0:
            return 0.0
        savings = (SINGLE_STAGE_COST - self.total_cost) / SINGLE_STAGE_COST
        return round(savings * 100, 1)

    @property
    def was_stage1_correct(self) -> bool:
        """
        Check if Stage 1 risk assessment matched final (Stage 2).

        Only applicable if escalated to Stage 2.
        """
        if not self.escalated:
            return True  # No Stage 2 to compare
        return self.stage1_risk == self.stage2_risk

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "stage_reached": self.stage_reached,
            "escalated": self.escalated,
            "final_risk": self.final_risk,
            "final_confidence": self.final_confidence,
            "total_cost": self.total_cost,
            "total_processing_time": self.total_processing_time,
            "anomaly_count": self.anomaly_count,
            "cost_efficiency": self.cost_efficiency,
            "created_at": self.created_at.isoformat(),
            "stage1": {
                "confidence": self.stage1_confidence,
                "risk": self.stage1_risk,
                "cost": self.stage1_cost,
                "processing_time": self.stage1_processing_time
            } if self.stage1_confidence is not None else None,
            "stage2": {
                "confidence": self.stage2_confidence,
                "risk": self.stage2_risk,
                "cost": self.stage2_cost,
                "processing_time": self.stage2_processing_time,
                "matched_stage1": self.was_stage1_correct
            } if self.escalated else None
        }

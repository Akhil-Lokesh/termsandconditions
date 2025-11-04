"""Anomaly model for storing detected risky clauses."""

from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base import Base


class Anomaly(Base):
    """Detected anomaly/risky clause in a T&C document."""

    __tablename__ = "anomalies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)
    clause_text = Column(Text, nullable=False)
    section = Column(String, nullable=True)
    clause_number = Column(String, nullable=True)
    severity = Column(String, nullable=False)  # low, medium, high
    explanation = Column(Text, nullable=True)
    consumer_impact = Column(Text, nullable=True)  # How this affects consumers
    recommendation = Column(Text, nullable=True)  # What users should know
    risk_category = Column(String, nullable=True)  # liability, payment, privacy, etc.
    prevalence = Column(Float, nullable=True)  # 0.0-1.0
    detected_indicators = Column(
        JSON, nullable=True
    )  # List of detected risk indicators
    risk_flags = Column(
        JSON, nullable=True
    )  # Legacy field - now using detected_indicators
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="anomalies")

    def __repr__(self) -> str:
        return (
            f"<Anomaly(id={self.id}, severity={self.severity}, section={self.section})>"
        )

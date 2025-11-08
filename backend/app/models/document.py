"""Document model for storing T&C documents."""

from typing import Optional
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base import Base


class Document(Base):
    """T&C Document model."""

    __tablename__ = "documents"

    # Type hints for IDE support (SQLAlchemy creates these at runtime)
    id: str
    user_id: str
    filename: str
    text: Optional[str]
    document_metadata: Optional[dict]
    page_count: Optional[int]
    clause_count: Optional[int]
    anomaly_count: Optional[int]
    risk_score: Optional[float]
    risk_level: Optional[str]
    processing_status: str
    created_at: datetime
    updated_at: datetime

    # Column definitions
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    text = Column(Text, nullable=True)  # Full extracted text
    document_metadata = Column(
        JSON, nullable=True
    )  # Company, jurisdiction, effective_date, etc.
    page_count = Column(Integer, nullable=True)
    clause_count = Column(Integer, nullable=True)
    anomaly_count = Column(Integer, default=0, nullable=True)
    risk_score = Column(Float, nullable=True)  # Overall risk score (1-10)
    risk_level = Column(String, nullable=True)  # Low, Medium, High
    processing_status = Column(
        String, default="processing"
    )  # processing, completed, failed, anomaly_detection_failed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="documents")
    clauses = relationship(
        "Clause", back_populates="document", cascade="all, delete-orphan"
    )
    anomalies = relationship(
        "Anomaly", back_populates="document", cascade="all, delete-orphan"
    )
    analysis_logs = relationship(
        "AnalysisLog", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename={self.filename}, status={self.processing_status})>"

"""FeedbackEvent model for persisting user feedback on anomaly detections.

Stores user feedback events to disk so they survive server restarts. Rows are
hydrated into the ActiveLearningManager's in-memory buffer at startup (when the
ACTIVE_LEARNING_PERSIST feature flag is enabled), and marked processed once
consumed.
"""

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Index
from datetime import datetime, timezone
import uuid

from app.db.base import Base


class FeedbackEvent(Base):
    """Persisted user-feedback event for anomaly detections.

    Each row records one user action on one anomaly. Rows are inserted by
    ``ActiveLearningManager.collect_feedback`` (write-through) and consumed at
    startup by ``ActiveLearningManager.hydrate_from_db`` which marks each row
    with ``processed_at`` once it has been loaded into the in-memory buffer.

    Valid ``user_action`` values:
        - "agree"          User agreed with the detection
        - "disagree"       User disagreed with the detection
        - "dismiss"        User dismissed the anomaly
        - "wrong_severity" User indicated the severity was wrong
        - "wrong_category" User indicated the category was wrong
    """

    __tablename__ = "feedback_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    anomaly_id = Column(String(36), nullable=False)
    document_id = Column(String(36), nullable=True)
    user_action = Column(String(20), nullable=False)
    original_severity = Column(String(20), nullable=True)
    suggested_severity = Column(String(20), nullable=True)
    confidence_score = Column(Float, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    processed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Composite index for the startup hydration query:
        #   SELECT * FROM feedback_events WHERE processed_at IS NULL ORDER BY created_at DESC
        Index(
            "ix_feedback_events_processed_at_created_at",
            "processed_at",
            "created_at",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<FeedbackEvent(id={self.id}, anomaly_id={self.anomaly_id}, "
            f"action={self.user_action}, processed={self.processed_at is not None})>"
        )

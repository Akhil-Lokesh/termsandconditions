"""Database models for the T&C Analysis System."""

from app.models.user import User
from app.models.document import Document
from app.models.clause import Clause
from app.models.anomaly import Anomaly
from app.models.feedback_event import FeedbackEvent

# NOTE: AnalysisLog (the old two-stage-pipeline log) was removed in the
# simple-engineering cleanup — it was never written or read, and its
# model/DB-column drift caused a delete-cascade 500. See the schema-reconcile
# migration for dropping the orphaned analysis_logs table.

__all__ = ["User", "Document", "Clause", "Anomaly", "FeedbackEvent"]

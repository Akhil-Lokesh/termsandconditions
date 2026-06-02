"""Reconcile model<->DB schema drift.

Brings the live database in line with the current models after the
simple-engineering refactor:

  * CREATE ``feedback_events`` if it is missing. The model + write path exist
    (POST /anomalies/{id}/feedback, GET /anomalies/performance) but the table was
    never created on some environments, so those endpoints 500.
  * DROP the vestigial tables left over from the deleted two-stage / 6-stage
    pipeline (``analysis_logs`` and the "advanced anomaly detection" tables).
    Their models were removed, so without this drop ``alembic revision
    --autogenerate`` would keep proposing DROP TABLE for them.

Every step is guarded with an inspector check, so this migration is safe to run
regardless of which of the drifted tables already exist.

Revision ID: f1a2b3c4d5e6_reconcile
Revises: e3f7a9_risk_title
"""

from alembic import op
import sqlalchemy as sa


revision = "f1a2b3c4d5e6_reconcile"
down_revision = "e3f7a9_risk_title"
branch_labels = None
depends_on = None


# Vestigial tables whose models were removed in the simple-engineering cleanup.
_VESTIGIAL_TABLES = [
    "analysis_logs",
    "compound_risks",
    "calibration_feedback",
    "active_learning_queue",
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    # 1. Create feedback_events if absent (matches app/models/feedback_event.py).
    if "feedback_events" not in existing:
        op.create_table(
            "feedback_events",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("anomaly_id", sa.String(length=36), nullable=False),
            sa.Column("document_id", sa.String(length=36), nullable=True),
            sa.Column("user_action", sa.String(length=20), nullable=False),
            sa.Column("original_severity", sa.String(length=20), nullable=True),
            sa.Column("suggested_severity", sa.String(length=20), nullable=True),
            sa.Column("confidence_score", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(
            "ix_feedback_events_processed_at_created_at",
            "feedback_events",
            ["processed_at", "created_at"],
        )

    # 2. Drop vestigial tables if present.
    for table in _VESTIGIAL_TABLES:
        if table in existing:
            op.drop_table(table)


def downgrade() -> None:
    # Reversal is intentionally minimal: drop feedback_events. The vestigial
    # tables are not recreated (their models no longer exist).
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "feedback_events" in set(inspector.get_table_names()):
        op.drop_table("feedback_events")

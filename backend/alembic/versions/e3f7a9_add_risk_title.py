"""Add risk_title column to anomalies table.

Stores the 5-8 word concrete title produced by the LLM detector (e.g.,
"Perpetual, irrevocable content license") so the frontend can render
lawyer-style summaries instead of a generic "Risk Detected" placeholder.

Revision ID: e3f7a9_risk_title
Revises: d2a4b5_feedback_event
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e3f7a9_risk_title"
down_revision = "d2a4b5_feedback_event"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "anomalies",
        sa.Column("risk_title", sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("anomalies", "risk_title")

"""add feedback_events table for persistent active-learning storage

Revision ID: d2a4b5_feedback_event
Revises: c1f2d3e4f5a6
Create Date: 2026-05-14 04:45:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2a4b5_feedback_event'
down_revision: Union[str, None] = 'c1f2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create feedback_events table + composite index for startup hydration."""
    op.create_table(
        'feedback_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('anomaly_id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=True),
        sa.Column('user_action', sa.String(length=20), nullable=False),
        sa.Column('original_severity', sa.String(length=20), nullable=True),
        sa.Column('suggested_severity', sa.String(length=20), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_feedback_events_processed_at_created_at',
        'feedback_events',
        ['processed_at', 'created_at'],
        unique=False,
    )


def downgrade() -> None:
    """Drop feedback_events table + index."""
    op.drop_index(
        'ix_feedback_events_processed_at_created_at',
        table_name='feedback_events',
    )
    op.drop_table('feedback_events')

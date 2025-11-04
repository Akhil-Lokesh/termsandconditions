"""add risk assessment fields

Revision ID: add_risk_fields_001
Revises:
Create Date: 2024-11-01

Adds risk_score and risk_level fields to documents table.
Adds consumer_impact, recommendation, risk_category, and detected_indicators to anomalies table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_risk_fields_001'
down_revision: Union[str, None] = '7944cf3e216b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add risk assessment fields."""

    # Add fields to documents table
    op.add_column('documents', sa.Column('risk_score', sa.Float(), nullable=True))
    op.add_column('documents', sa.Column('risk_level', sa.String(), nullable=True))

    # Add fields to anomalies table
    op.add_column('anomalies', sa.Column('consumer_impact', sa.Text(), nullable=True))
    op.add_column('anomalies', sa.Column('recommendation', sa.Text(), nullable=True))
    op.add_column('anomalies', sa.Column('risk_category', sa.String(), nullable=True))
    op.add_column('anomalies', sa.Column('detected_indicators', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove risk assessment fields."""

    # Remove from anomalies table
    op.drop_column('anomalies', 'detected_indicators')
    op.drop_column('anomalies', 'risk_category')
    op.drop_column('anomalies', 'recommendation')
    op.drop_column('anomalies', 'consumer_impact')

    # Remove from documents table
    op.drop_column('documents', 'risk_level')
    op.drop_column('documents', 'risk_score')

"""Merge dual heads and add composite index on anomalies.

Revision ID: c1f2d3e4f5a6
Revises: add_analysis_logs_002, b8e4d92f1a3c
Create Date: 2026-05-13 00:00:00.000000
"""
from typing import Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c1f2d3e4f5a6'
down_revision: Union[str, tuple] = ('add_analysis_logs_002', 'b8e4d92f1a3c')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Composite index for the common query pattern: anomalies by document + severity
    op.create_index(
        'ix_anomalies_document_id_severity',
        'anomalies',
        ['document_id', 'severity'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_anomalies_document_id_severity', table_name='anomalies')

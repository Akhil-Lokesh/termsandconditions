"""add analysis logs table for two-stage tracking

Revision ID: add_analysis_logs_002
Revises: add_risk_fields_001
Create Date: 2024-11-01

Creates analysis_logs table for tracking GPT-5 two-stage analysis.
Tracks cost, escalation, confidence, and results for analytics.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_analysis_logs_002'
down_revision: Union[str, None] = 'add_risk_fields_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create analysis_logs table."""
    op.create_table(
        'analysis_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('document_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),

        # Analysis execution
        sa.Column('stage_reached', sa.Integer(), nullable=False),
        sa.Column('escalated', sa.Boolean(), nullable=False, server_default='false'),

        # Stage 1 results
        sa.Column('stage1_confidence', sa.Float(), nullable=True),
        sa.Column('stage1_risk', sa.String(), nullable=True),
        sa.Column('stage1_cost', sa.Float(), nullable=True),
        sa.Column('stage1_processing_time', sa.Float(), nullable=True),
        sa.Column('stage1_result', sa.JSON(), nullable=True),

        # Stage 2 results
        sa.Column('stage2_confidence', sa.Float(), nullable=True),
        sa.Column('stage2_risk', sa.String(), nullable=True),
        sa.Column('stage2_cost', sa.Float(), nullable=True),
        sa.Column('stage2_processing_time', sa.Float(), nullable=True),
        sa.Column('stage2_result', sa.JSON(), nullable=True),

        # Final results
        sa.Column('final_risk', sa.String(), nullable=False),
        sa.Column('final_confidence', sa.Float(), nullable=False),
        sa.Column('total_cost', sa.Float(), nullable=False),
        sa.Column('total_processing_time', sa.Float(), nullable=False),

        # Anomaly counts
        sa.Column('anomaly_count', sa.Integer(), server_default='0'),
        sa.Column('high_risk_count', sa.Integer(), server_default='0'),
        sa.Column('medium_risk_count', sa.Integer(), server_default='0'),
        sa.Column('low_risk_count', sa.Integer(), server_default='0'),

        # Metadata
        sa.Column('company_name', sa.String(), nullable=True),
        sa.Column('industry', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),

        # Primary key and foreign keys
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

    # Create indexes for common queries
    op.create_index('ix_analysis_logs_document_id', 'analysis_logs', ['document_id'])
    op.create_index('ix_analysis_logs_user_id', 'analysis_logs', ['user_id'])
    op.create_index('ix_analysis_logs_created_at', 'analysis_logs', ['created_at'])
    op.create_index('ix_analysis_logs_stage_reached', 'analysis_logs', ['stage_reached'])
    op.create_index('ix_analysis_logs_escalated', 'analysis_logs', ['escalated'])


def downgrade() -> None:
    """Drop analysis_logs table."""
    op.drop_index('ix_analysis_logs_escalated', table_name='analysis_logs')
    op.drop_index('ix_analysis_logs_stage_reached', table_name='analysis_logs')
    op.drop_index('ix_analysis_logs_created_at', table_name='analysis_logs')
    op.drop_index('ix_analysis_logs_user_id', table_name='analysis_logs')
    op.drop_index('ix_analysis_logs_document_id', table_name='analysis_logs')
    op.drop_table('analysis_logs')

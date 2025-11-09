"""add advanced anomaly detection tables

Revision ID: b8e4d92f1a3c
Revises: add_risk_fields_001
Create Date: 2025-11-09 10:30:00.000000

Adds compound_risks, calibration_feedback, and active_learning_queue tables.
Updates anomalies table with additional fields for advanced anomaly detection.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b8e4d92f1a3c'
down_revision: Union[str, None] = 'add_risk_fields_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add advanced anomaly detection tables and fields."""

    # 1. Create compound_risks table
    op.create_table(
        'compound_risks',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('document_id', sa.String(), nullable=False),
        sa.Column('pattern_id', sa.String(length=50), nullable=False),
        sa.Column('pattern_name', sa.String(length=200), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('risk_multiplier', sa.Float(), nullable=True),
        sa.Column('combined_score', sa.Float(), nullable=True),
        sa.Column('component_clause_ids', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('recommendation', sa.JSON(), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_compound_risks_document_id'), 'compound_risks', ['document_id'], unique=False)
    op.create_index(op.f('ix_compound_risks_pattern_id'), 'compound_risks', ['pattern_id'], unique=False)

    # 2. Create calibration_feedback table
    op.create_table(
        'calibration_feedback',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('anomaly_id', sa.String(), nullable=False),
        sa.Column('predicted_confidence', sa.Float(), nullable=False),
        sa.Column('was_correct', sa.Boolean(), nullable=False),
        sa.Column('user_action', sa.String(length=50), nullable=True),
        sa.Column('document_industry', sa.String(length=50), nullable=True),
        sa.Column('anomaly_category', sa.String(length=100), nullable=True),
        sa.Column('feedback_date', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['anomaly_id'], ['anomalies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_calibration_feedback_was_correct'), 'calibration_feedback', ['was_correct'], unique=False)
    op.create_index(op.f('ix_calibration_feedback_feedback_date'), 'calibration_feedback', ['feedback_date'], unique=False)
    op.create_index(op.f('ix_calibration_feedback_anomaly_id'), 'calibration_feedback', ['anomaly_id'], unique=False)

    # 3. Create active_learning_queue table
    op.create_table(
        'active_learning_queue',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('anomaly_id', sa.String(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('uncertainty_score', sa.Float(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('labeled_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['anomaly_id'], ['anomalies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_active_learning_queue_status'), 'active_learning_queue', ['status'], unique=False)
    op.create_index(op.f('ix_active_learning_queue_priority'), 'active_learning_queue', ['priority'], unique=False)
    op.create_index(op.f('ix_active_learning_queue_anomaly_id'), 'active_learning_queue', ['anomaly_id'], unique=False)
    op.create_index(
        'ix_active_learning_queue_status_priority',
        'active_learning_queue',
        ['status', 'priority'],
        unique=False
    )

    # 4. Update anomalies table with new fields
    op.add_column('anomalies', sa.Column('detection_stage', sa.Integer(), nullable=True))
    op.add_column('anomalies', sa.Column('anomaly_type', sa.String(length=50), nullable=True))
    op.add_column('anomalies', sa.Column('raw_confidence', sa.Float(), nullable=True))
    op.add_column('anomalies', sa.Column('confidence_tier', sa.String(length=20), nullable=True))
    op.add_column('anomalies', sa.Column('final_score', sa.Float(), nullable=True))
    op.add_column('anomalies', sa.Column('industry', sa.String(length=50), nullable=True))
    op.add_column('anomalies', sa.Column('service_type', sa.String(length=50), nullable=True))
    # Note: prevalence already exists from initial migration, but we'll keep for safety
    op.add_column('anomalies', sa.Column('is_common', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('anomalies', sa.Column('is_compound', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('anomalies', sa.Column('is_recent_change', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('anomalies', sa.Column('is_suppressed', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('anomalies', sa.Column('user_action', sa.String(length=50), nullable=True))

    # Add indexes for frequently queried fields
    op.create_index(op.f('ix_anomalies_anomaly_type'), 'anomalies', ['anomaly_type'], unique=False)
    op.create_index(op.f('ix_anomalies_confidence_tier'), 'anomalies', ['confidence_tier'], unique=False)
    op.create_index(op.f('ix_anomalies_industry'), 'anomalies', ['industry'], unique=False)
    op.create_index(op.f('ix_anomalies_is_compound'), 'anomalies', ['is_compound'], unique=False)
    op.create_index(op.f('ix_anomalies_is_suppressed'), 'anomalies', ['is_suppressed'], unique=False)


def downgrade() -> None:
    """Remove advanced anomaly detection tables and fields."""

    # Drop indexes from anomalies table
    op.drop_index(op.f('ix_anomalies_is_suppressed'), table_name='anomalies')
    op.drop_index(op.f('ix_anomalies_is_compound'), table_name='anomalies')
    op.drop_index(op.f('ix_anomalies_industry'), table_name='anomalies')
    op.drop_index(op.f('ix_anomalies_confidence_tier'), table_name='anomalies')
    op.drop_index(op.f('ix_anomalies_anomaly_type'), table_name='anomalies')

    # Drop new columns from anomalies table
    op.drop_column('anomalies', 'user_action')
    op.drop_column('anomalies', 'is_suppressed')
    op.drop_column('anomalies', 'is_recent_change')
    op.drop_column('anomalies', 'is_compound')
    op.drop_column('anomalies', 'is_common')
    op.drop_column('anomalies', 'service_type')
    op.drop_column('anomalies', 'industry')
    op.drop_column('anomalies', 'final_score')
    op.drop_column('anomalies', 'confidence_tier')
    op.drop_column('anomalies', 'raw_confidence')
    op.drop_column('anomalies', 'anomaly_type')
    op.drop_column('anomalies', 'detection_stage')

    # Drop active_learning_queue table
    op.drop_index('ix_active_learning_queue_status_priority', table_name='active_learning_queue')
    op.drop_index(op.f('ix_active_learning_queue_anomaly_id'), table_name='active_learning_queue')
    op.drop_index(op.f('ix_active_learning_queue_priority'), table_name='active_learning_queue')
    op.drop_index(op.f('ix_active_learning_queue_status'), table_name='active_learning_queue')
    op.drop_table('active_learning_queue')

    # Drop calibration_feedback table
    op.drop_index(op.f('ix_calibration_feedback_anomaly_id'), table_name='calibration_feedback')
    op.drop_index(op.f('ix_calibration_feedback_feedback_date'), table_name='calibration_feedback')
    op.drop_index(op.f('ix_calibration_feedback_was_correct'), table_name='calibration_feedback')
    op.drop_table('calibration_feedback')

    # Drop compound_risks table
    op.drop_index(op.f('ix_compound_risks_pattern_id'), table_name='compound_risks')
    op.drop_index(op.f('ix_compound_risks_document_id'), table_name='compound_risks')
    op.drop_table('compound_risks')

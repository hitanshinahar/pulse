"""Phase 1B Recovery Intelligence

Revision ID: fa259d74a0b6
Revises: ebd1cc05f5de
Create Date: 2026-08-30 22:22:22.898369

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'fa259d74a0b6'
down_revision: Union[str, None] = 'ebd1cc05f5de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # recovery_action_definitions
    op.create_table('recovery_action_definitions',
        sa.Column('action_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('requires_outstanding_balance', sa.Boolean(), nullable=False),
        sa.Column('requires_customer_information', sa.Boolean(), nullable=False),
        sa.Column('external_provider', sa.String(), nullable=True),
        sa.Column('capability', sa.String(), nullable=False),
        sa.Column('risk_level', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('action_id')
    )

    # recovery_feature_snapshots
    op.create_table('recovery_feature_snapshots',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('obligation_id', sa.UUID(), nullable=False),
        sa.Column('feature_schema_version', sa.Integer(), nullable=False),
        sa.Column('features', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['obligation_id'], ['financial_obligations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # recovery_training_examples
    op.create_table('recovery_training_examples',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('dataset_version', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('features', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('candidate_action', sa.String(), nullable=False),
        sa.Column('outcome', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['candidate_action'], ['recovery_action_definitions.action_id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # recovery_model_versions
    op.create_table('recovery_model_versions',
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('dataset_version', sa.Integer(), nullable=False),
        sa.Column('feature_schema_version', sa.Integer(), nullable=False),
        sa.Column('algorithm', sa.String(), nullable=False),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('artifact_uri', sa.String(), nullable=False),
        sa.Column('artifact_checksum', sa.String(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('version')
    )

    # recovery_decisions
    op.create_table('recovery_decisions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('obligation_id', sa.UUID(), nullable=False),
        sa.Column('state_version', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('baseline_probability', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('action_probability', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('incremental_probability', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('expected_incremental_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('model_version', sa.String(), nullable=False),
        sa.Column('feature_schema_version', sa.Integer(), nullable=False),
        sa.Column('llm_diagnosis', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['action'], ['recovery_action_definitions.action_id'], ),
        sa.ForeignKeyConstraint(['model_version'], ['recovery_model_versions.version'], ),
        sa.ForeignKeyConstraint(['obligation_id'], ['financial_obligations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('recovery_decisions')
    op.drop_table('recovery_model_versions')
    op.drop_table('recovery_training_examples')
    op.drop_table('recovery_feature_snapshots')
    op.drop_table('recovery_action_definitions')

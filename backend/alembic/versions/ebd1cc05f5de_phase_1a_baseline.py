"""Phase 1A baseline

Revision ID: ebd1cc05f5de
Revises: 
Create Date: 2026-08-30 22:20:01.899040

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ebd1cc05f5de'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # financial_obligations
    op.create_table('financial_obligations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('merchant_reference', sa.String(), nullable=True),
        sa.Column('razorpay_order_id', sa.String(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('satisfied_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('outstanding_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('state_version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_financial_obligations_merchant_reference'), 'financial_obligations', ['merchant_reference'], unique=False)
    op.create_index(op.f('ix_financial_obligations_razorpay_order_id'), 'financial_obligations', ['razorpay_order_id'], unique=True)

    # razorpay_events
    op.create_table('razorpay_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('razorpay_event_id', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('raw_payload', sa.Text(), nullable=False),
        sa.Column('parsed_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_msg', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_razorpay_events_event_type'), 'razorpay_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_razorpay_events_razorpay_event_id'), 'razorpay_events', ['razorpay_event_id'], unique=True)
    op.create_index(op.f('ix_razorpay_events_status'), 'razorpay_events', ['status'], unique=False)

    # obligation_state_transitions
    op.create_table('obligation_state_transitions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('obligation_id', sa.UUID(), nullable=False),
        sa.Column('previous_state', sa.String(), nullable=False),
        sa.Column('new_state', sa.String(), nullable=False),
        sa.Column('previous_version', sa.Integer(), nullable=False),
        sa.Column('new_version', sa.Integer(), nullable=False),
        sa.Column('triggering_event_id', sa.UUID(), nullable=True),
        sa.Column('reason', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['obligation_id'], ['financial_obligations.id'], ),
        sa.ForeignKeyConstraint(['triggering_event_id'], ['razorpay_events.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # payment_attempts
    op.create_table('payment_attempts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('razorpay_payment_id', sa.String(), nullable=False),
        sa.Column('razorpay_order_id', sa.String(), nullable=False),
        sa.Column('obligation_id', sa.UUID(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('payment_method', sa.String(), nullable=True),
        sa.Column('razorpay_status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('latest_event_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['obligation_id'], ['financial_obligations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payment_attempts_razorpay_order_id'), 'payment_attempts', ['razorpay_order_id'], unique=False)
    op.create_index(op.f('ix_payment_attempts_razorpay_payment_id'), 'payment_attempts', ['razorpay_payment_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_payment_attempts_razorpay_payment_id'), table_name='payment_attempts')
    op.drop_index(op.f('ix_payment_attempts_razorpay_order_id'), table_name='payment_attempts')
    op.drop_table('payment_attempts')
    op.drop_table('obligation_state_transitions')
    op.drop_index(op.f('ix_razorpay_events_status'), table_name='razorpay_events')
    op.drop_index(op.f('ix_razorpay_events_razorpay_event_id'), table_name='razorpay_events')
    op.drop_index(op.f('ix_razorpay_events_event_type'), table_name='razorpay_events')
    op.drop_table('razorpay_events')
    op.drop_index(op.f('ix_financial_obligations_razorpay_order_id'), table_name='financial_obligations')
    op.drop_index(op.f('ix_financial_obligations_merchant_reference'), table_name='financial_obligations')
    op.drop_table('financial_obligations')

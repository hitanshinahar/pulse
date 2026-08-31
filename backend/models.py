import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, Numeric, ForeignKey, Enum, JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.orm import relationship
from backend.database import Base

# Dialect-agnostic UUID
class UUID(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def __init__(self, as_uuid=False):
        super(UUID, self).__init__(32)
        self.as_uuid = as_uuid

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                return "%.32x" % value.int

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value


class RazorpayEvent(Base):
    __tablename__ = "razorpay_events"

    # UUID primary key for internal uniqueness
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Unique event ID provided by Razorpay (from the x-razorpay-event-id header)
    razorpay_event_id = Column(String, unique=True, index=True, nullable=False)

    # Type of event (e.g., payment.captured)
    event_type = Column(String, index=True, nullable=False)

    # Store the raw, unmodified payload string (important for audit and debugging)
    raw_payload = Column(Text, nullable=False)

    # Store parsed JSON for structured querying later
    parsed_payload = Column(JSON().with_variant(JSONB, 'postgresql'), nullable=False)

    # Status of the event: RECEIVED, PROCESSING, PROCESSED, FAILED
    status = Column(String, default="RECEIVED", index=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Store error messages if processing fails
    error_msg = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "id": str(self.id),
            "razorpay_event_id": self.razorpay_event_id,
            "event_type": self.event_type,
            "parsed_payload": self.parsed_payload,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "error_msg": self.error_msg
        }

class FinancialObligation(Base):
    __tablename__ = "financial_obligations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_reference = Column(String, index=True, nullable=True)
    razorpay_order_id = Column(String, index=True, unique=True, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    satisfied_amount = Column(Numeric(12, 2), default=0, nullable=False)
    outstanding_amount = Column(Numeric(12, 2), nullable=False)
    
    # UNRESOLVED, RECOVERY_ELIGIBLE, AMBIGUOUS, PARTIALLY_SATISFIED, SATISFIED, OVER_COLLECTED, ESCALATED, CLOSED
    status = Column(String, nullable=False, default="UNRESOLVED")
    state_version = Column(Integer, default=1, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    payment_attempts = relationship("PaymentAttempt", back_populates="obligation")
    state_transitions = relationship("ObligationStateTransition", back_populates="obligation")

class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    razorpay_payment_id = Column(String, unique=True, index=True, nullable=False)
    razorpay_order_id = Column(String, index=True, nullable=False)
    obligation_id = Column(UUID(as_uuid=True), ForeignKey("financial_obligations.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    payment_method = Column(String, nullable=True)
    razorpay_status = Column(String, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    latest_event_at = Column(DateTime(timezone=True), nullable=True)

    obligation = relationship("FinancialObligation", back_populates="payment_attempts")

class ObligationStateTransition(Base):
    __tablename__ = "obligation_state_transitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    obligation_id = Column(UUID(as_uuid=True), ForeignKey("financial_obligations.id"), nullable=False)
    previous_state = Column(String, nullable=False)
    new_state = Column(String, nullable=False)
    previous_version = Column(Integer, nullable=False)
    new_version = Column(Integer, nullable=False)
    triggering_event_id = Column(UUID(as_uuid=True), ForeignKey("razorpay_events.id"), nullable=True)
    reason = Column(String, nullable=False)
    source = Column(String, nullable=False) # 'razorpay_webhook', 'razorpay_api', etc.
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    obligation = relationship("FinancialObligation", back_populates="state_transitions")
    triggering_event = relationship("RazorpayEvent")

class RecoveryActionDefinition(Base):
    __tablename__ = "recovery_action_definitions"

    action_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    requires_outstanding_balance = Column(Boolean, default=True, nullable=False)
    requires_customer_information = Column(Boolean, default=False, nullable=False)
    external_provider = Column(String, nullable=True)
    capability = Column(String, nullable=False)
    risk_level = Column(String, nullable=False)

class RecoveryFeatureSnapshot(Base):
    __tablename__ = "recovery_feature_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    obligation_id = Column(UUID(as_uuid=True), ForeignKey("financial_obligations.id"), nullable=False)
    feature_schema_version = Column(Integer, nullable=False)
    features = Column(JSON().with_variant(JSONB, 'postgresql'), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    obligation = relationship("FinancialObligation")

class RecoveryTrainingExample(Base):
    __tablename__ = "recovery_training_examples"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_version = Column(Integer, nullable=False)
    source = Column(String, nullable=False) # 'synthetic' or 'real_test_mode'
    features = Column(JSON().with_variant(JSONB, 'postgresql'), nullable=False)
    candidate_action = Column(String, ForeignKey("recovery_action_definitions.action_id"), nullable=False)
    outcome = Column(Integer, nullable=False) # 1 or 0 (success/fail)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class RecoveryModelVersion(Base):
    __tablename__ = "recovery_model_versions"

    version = Column(String, primary_key=True)
    dataset_version = Column(Integer, nullable=False)
    feature_schema_version = Column(Integer, nullable=False)
    algorithm = Column(String, nullable=False)
    metrics = Column(JSON().with_variant(JSONB, 'postgresql'), nullable=False)
    artifact_uri = Column(String, nullable=False)
    artifact_checksum = Column(String, nullable=False)
    active = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class RecoveryDecision(Base):
    __tablename__ = "recovery_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    obligation_id = Column(UUID(as_uuid=True), ForeignKey("financial_obligations.id"), nullable=False)
    state_version = Column(Integer, nullable=False)
    action = Column(String, ForeignKey("recovery_action_definitions.action_id"), nullable=False)
    baseline_probability = Column(Numeric(5, 4), nullable=False)
    action_probability = Column(Numeric(5, 4), nullable=False)
    incremental_probability = Column(Numeric(5, 4), nullable=False)
    expected_incremental_amount = Column(Numeric(12, 2), nullable=False)
    model_version = Column(String, ForeignKey("recovery_model_versions.version"), nullable=False)
    feature_schema_version = Column(Integer, nullable=False)
    llm_diagnosis = Column(JSON().with_variant(JSONB, 'postgresql'), nullable=False)
    evidence = Column(JSON().with_variant(JSONB, 'postgresql'), nullable=False)
    status = Column(String, nullable=False) # PROPOSED, APPROVED, BLOCKED, EXECUTED, EXPIRED, OUTCOME_RECORDED
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    obligation = relationship("FinancialObligation")


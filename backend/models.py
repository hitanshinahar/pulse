import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID
from backend.database import Base

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
    parsed_payload = Column(JSONB, nullable=False)

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

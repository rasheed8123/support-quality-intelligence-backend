from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Float, Boolean, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    alert_type = Column(String(50))  # 'sla_breach', 'high_priority_pending', 'factual_error', 'negative_sentiment', 'aging_query'
    severity = Column(String(20))    # 'critical', 'warning', 'info'
    email_id = Column(String(255), ForeignKey("email.email_identifier", ondelete="CASCADE"))
    title = Column(String(255))
    description = Column(Text)

    # Alert metadata
    triggered_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(100), nullable=True)

    # Alert context
    priority_level = Column(String(20))  # 'high', 'medium', 'low'
    threshold_value = Column(Float)      # Time elapsed, score, etc.
    current_value = Column(Float)        # Actual value that triggered alert

    # Notification tracking
    email_notification_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime, nullable=True)
    notification_retry_count = Column(Integer, default=0)

    # Legacy compatibility
    created_at = Column(DateTime, default=datetime.utcnow)  # Keep for backward compatibility
    type = Column(String(50))  # Keep for backward compatibility, will be synced with alert_type

    # Relationships
    email = relationship("Email", back_populates="alerts")

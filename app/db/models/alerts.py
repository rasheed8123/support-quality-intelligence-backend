from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from app.db.base import Base
from datetime import datetime
import enum

class AlertType(enum.Enum):
    SLA_BREACH = "sla_breach"
    HIGH_PRIORITY = "high_priority"
    NEGATIVE_TONE = "negative_tone"

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(AlertType))
    email_id = Column(Integer, ForeignKey("emails.id"))
    message = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

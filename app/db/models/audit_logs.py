from sqlalchemy import Column, String, DateTime, Text, Integer, JSON
from app.db.base import Base
from datetime import datetime

class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id = Column(Integer, primary_key=True)
    event_type = Column(Text)
    payload = Column(JSON)  # Use JSON instead of JSONB for MySQL compatibility
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

from sqlalchemy import Column, String, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base
from datetime import datetime

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    log_id = Column(Integer, primary_key=True)
    event_type = Column(Text)
    payload = Column(JSONB)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

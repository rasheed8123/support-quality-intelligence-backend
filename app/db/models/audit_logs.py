from sqlalchemy import Column, Integer, String, DateTime, JSON
from app.db.base import Base
from datetime import datetime

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String)
    user_id = Column(String)
    details = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

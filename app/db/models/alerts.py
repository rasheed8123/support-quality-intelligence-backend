from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True)
    type = Column(String(50))  # 'sla_breach', 'high_priority_pending', 'incorrect_fact', 'negative_tone'
    email_id = Column(Text, ForeignKey("email.email_identifier", ondelete="CASCADE"))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    email = relationship("Email", back_populates="alerts")

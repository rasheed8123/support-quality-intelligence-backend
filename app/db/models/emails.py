from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime

class Email(Base):
    __tablename__ = "email"

    id = Column(Integer, primary_key=True)
    email_identifier = Column(String(255), nullable=False, unique=True, index=True)  # Added index for MySQL FK compatibility
    is_inbound = Column(Boolean, nullable=False)
    thread_id = Column(String(255), nullable=False)
    subject = Column(Text, nullable=True)  # Email subject line
    body = Column(Text, nullable=True)     # Email body content
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    inbound_analysis = relationship("InboundEmailAnalysis", back_populates="email", uselist=False)
    outbound_analysis = relationship("OutboundEmailAnalysis", back_populates="email", uselist=False)
    alerts = relationship("Alert", back_populates="email")

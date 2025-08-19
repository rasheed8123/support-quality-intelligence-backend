from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Boolean, Text, Integer
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime

class InboundEmailAnalysis(Base):
    __tablename__ = "inbound_email_analysis"
    
    id = Column(Integer, primary_key=True)
    email_id = Column(Text, ForeignKey("email.email_identifier", ondelete="CASCADE"))
    from_email = Column(Text, nullable=False)
    type = Column(String(20))  # 'spam', 'query', 'information'
    priority = Column(String(20))  # 'high', 'medium', 'low'
    category = Column(Text)
    responded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    email = relationship("Email", back_populates="inbound_analysis")

class OutboundEmailAnalysis(Base):
    __tablename__ = "outbound_email_analysis"
    
    id = Column(Integer, primary_key=True)
    email_id = Column(Text, ForeignKey("email.email_identifier", ondelete="CASCADE"))
    type = Column(String(20))  # 'query', 'information'
    factual_accuracy = Column(Float)
    guideline_compliance = Column(Float)
    completeness = Column(Float)
    tone = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    email = relationship("Email", back_populates="outbound_analysis")

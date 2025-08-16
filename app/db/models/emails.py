from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime

class Email(Base):
    __tablename__ = "emails"
    
    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(String, unique=True, index=True)
    thread_id = Column(Integer, ForeignKey("threads.id"))
    subject = Column(String)
    sender = Column(String)
    recipients = Column(String)
    content = Column(Text)
    received_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    thread = relationship("Thread", back_populates="emails")
    predictions = relationship("EmailPrediction", back_populates="email")

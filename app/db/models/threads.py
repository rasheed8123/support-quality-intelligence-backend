from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime

class Thread(Base):
    __tablename__ = "threads"
    
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    emails = relationship("Email", back_populates="thread")

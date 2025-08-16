from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime

class EmailPrediction(Base):
    __tablename__ = "email_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"))
    priority_score = Column(Float)
    subcategory = Column(String)
    intent = Column(String)
    tone = Column(String)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    email = relationship("Email", back_populates="predictions")

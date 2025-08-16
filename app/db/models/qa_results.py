from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Float
from app.db.base import Base
from datetime import datetime

class QAResult(Base):
    __tablename__ = "qa_results"
    
    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"))
    question = Column(String)
    answer = Column(String)
    source_documents = Column(JSON)
    confidence_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

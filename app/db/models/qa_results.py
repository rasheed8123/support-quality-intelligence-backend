from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Text, Integer
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base
from datetime import datetime

class QAResult(Base):
    __tablename__ = "qa_results"
    
    id = Column(Integer, primary_key=True)
    email_id = Column(Text, ForeignKey("email.email_identifier", ondelete="CASCADE"))
    question = Column(Text)
    answer = Column(Text)
    source_documents = Column(JSONB)
    confidence_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

from sqlalchemy import Column, Integer, String, DateTime, JSON
from app.db.base import Base
from datetime import datetime

class DailyReport(Base):
    __tablename__ = "daily_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, unique=True, index=True)
    metrics = Column(JSON)  # Store daily statistics
    insights = Column(JSON)  # Store generated insights
    created_at = Column(DateTime, default=datetime.utcnow)

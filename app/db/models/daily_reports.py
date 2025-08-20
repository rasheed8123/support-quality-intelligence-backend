from sqlalchemy import Column, Integer, Date, Float
from db.base import Base

class DailyReport(Base):
    __tablename__ = "daily_reports"
    
    report_date = Column(Date, primary_key=True)
    total_emails = Column(Integer)
    queries_count = Column(Integer)
    info_count = Column(Integer)
    spam_count = Column(Integer)
    high_priority_count = Column(Integer)
    medium_priority_count = Column(Integer)
    low_priority_count = Column(Integer)
    responded_count = Column(Integer)
    pending_count = Column(Integer)
    avg_response_time = Column(Float)
    tone_score_avg = Column(Float)
    factual_accuracy_avg = Column(Float)
    guidelines_score_avg = Column(Float)
    alerts_count = Column(Integer)

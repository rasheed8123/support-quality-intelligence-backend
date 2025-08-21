from sqlalchemy import Column, Integer, Date, Float, DateTime, JSON
from datetime import datetime
from app.db.base import Base

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

    # Enhanced metrics for comprehensive reporting
    high_priority_responded = Column(Integer, default=0)
    high_priority_pending = Column(Integer, default=0)
    medium_priority_responded = Column(Integer, default=0)
    medium_priority_pending = Column(Integer, default=0)
    low_priority_responded = Column(Integer, default=0)
    low_priority_pending = Column(Integer, default=0)

    # Response rate metrics
    overall_response_rate = Column(Float, default=0.0)
    high_priority_response_rate = Column(Float, default=0.0)
    medium_priority_response_rate = Column(Float, default=0.0)
    low_priority_response_rate = Column(Float, default=0.0)

    # Overdue tracking
    overdue_24hrs_count = Column(Integer, default=0)
    overdue_48hrs_count = Column(Integer, default=0)

    # Error detection
    factual_errors_detected = Column(Integer, default=0)
    tone_violations_count = Column(Integer, default=0)

    # Top issues by priority (JSON fields)
    high_priority_top_issues = Column(JSON)
    medium_priority_top_issues = Column(JSON)
    low_priority_top_issues = Column(JSON)

    # Alert counts by severity
    critical_alerts_count = Column(Integer, default=0)
    warning_alerts_count = Column(Integer, default=0)
    error_alerts_count = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

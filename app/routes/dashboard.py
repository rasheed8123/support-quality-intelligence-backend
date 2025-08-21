"""
Dashboard API endpoints for frontend
"""

from datetime import datetime, date, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case, or_, desc
from pydantic import BaseModel

from app.db.session import get_db
from app.db.models.emails import Email
from app.db.models.email_analysis import InboundEmailAnalysis, OutboundEmailAnalysis
from app.db.models.alerts import Alert

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class DashboardDetailsResponse(BaseModel):
    """Dashboard details response model"""
    date: str
    total_emails: int
    queries_count: int
    info_count: int
    spam_count: int
    high_priority_count: int
    medium_priority_count: int
    low_priority_count: int
    responded_count: int
    pending_count: int
    avg_response_time: Optional[float]
    tone_score_avg: Optional[float]
    factual_accuracy_avg: Optional[float]
    guidelines_score_avg: Optional[float]
    alerts_count: int


class EmailItem(BaseModel):
    """Email item model for list response"""
    email_id: str
    from_email: str
    subject: Optional[str]
    body: Optional[str]
    type: str
    priority: str
    category: str
    responded: bool
    created_at: datetime
    updated_at: Optional[datetime]


class EmailsListResponse(BaseModel):
    """Emails list response with pagination"""
    total: int
    page: int
    limit: int
    total_pages: int
    date: str
    emails: List[EmailItem]


@router.get("/details", response_model=DashboardDetailsResponse)
async def get_dashboard_details(
    selected_date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format, defaults to today"),
    db: Session = Depends(get_db)
):
    """
    Get dashboard details for selected date (default: today)
    
    Returns comprehensive metrics including:
    - Email counts by type and priority
    - Response metrics
    - Quality scores
    - Alert counts
    """
    
    # Parse date or use today
    if selected_date:
        try:
            target_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()
    
    # Date range for the selected day
    start_datetime = datetime.combine(target_date, datetime.min.time())
    end_datetime = datetime.combine(target_date, datetime.max.time())
    
    # Get inbound email statistics
    inbound_stats = db.query(
        func.count(Email.id).label('total_emails'),
        func.sum(case((InboundEmailAnalysis.type == 'query', 1), else_=0)).label('queries_count'),
        func.sum(case((InboundEmailAnalysis.type == 'information', 1), else_=0)).label('info_count'),
        func.sum(case((InboundEmailAnalysis.type == 'spam', 1), else_=0)).label('spam_count'),
        func.sum(case((InboundEmailAnalysis.priority.like('%High%'), 1), else_=0)).label('high_priority_count'),
        func.sum(case((InboundEmailAnalysis.priority.like('%Medium%'), 1), else_=0)).label('medium_priority_count'),
        func.sum(case((InboundEmailAnalysis.priority.like('%Low%'), 1), else_=0)).label('low_priority_count'),
        func.sum(case((InboundEmailAnalysis.responded == True, 1), else_=0)).label('responded_count'),
        func.sum(case((InboundEmailAnalysis.responded == False, 1), else_=0)).label('pending_count')
    ).join(
        InboundEmailAnalysis, Email.email_identifier == InboundEmailAnalysis.email_id
    ).filter(
        and_(
            Email.is_inbound == True,
            Email.created_at >= start_datetime,
            Email.created_at <= end_datetime
        )
    ).first()
    
    # Get outbound email quality metrics
    outbound_stats = db.query(
        func.avg(OutboundEmailAnalysis.factual_accuracy).label('factual_accuracy_avg'),
        func.avg(OutboundEmailAnalysis.guideline_compliance).label('guidelines_score_avg'),
        func.avg(
            case(
                (OutboundEmailAnalysis.tone == 'professional', 10),
                (OutboundEmailAnalysis.tone == 'friendly', 8),
                (OutboundEmailAnalysis.tone == 'neutral', 6),
                (OutboundEmailAnalysis.tone == 'poor', 3),
                else_=5
            )
        ).label('tone_score_avg')
    ).join(
        Email, Email.email_identifier == OutboundEmailAnalysis.email_id
    ).filter(
        and_(
            Email.is_inbound == False,
            Email.created_at >= start_datetime,
            Email.created_at <= end_datetime
        )
    ).first()
    
    # Calculate average response time (simplified - would need response timestamps in real implementation)
    # For now, using a placeholder calculation
    avg_response_time = 4.2  # Hours - placeholder
    
    # Get alerts count for the day (active alerts = not resolved)
    alerts_count = db.query(func.count(Alert.id)).filter(
        and_(
            Alert.created_at >= start_datetime,
            Alert.created_at <= end_datetime,
            Alert.resolved_at.is_(None)  # Active alerts are those not resolved
        )
    ).scalar() or 0
    
    # Handle None values from aggregations
    total_emails = inbound_stats.total_emails or 0
    queries_count = inbound_stats.queries_count or 0
    info_count = inbound_stats.info_count or 0
    spam_count = inbound_stats.spam_count or 0
    high_priority_count = inbound_stats.high_priority_count or 0
    medium_priority_count = inbound_stats.medium_priority_count or 0
    low_priority_count = inbound_stats.low_priority_count or 0
    responded_count = inbound_stats.responded_count or 0
    pending_count = inbound_stats.pending_count or 0
    
    # Quality metrics (convert to percentages and handle None)
    factual_accuracy_avg = (outbound_stats.factual_accuracy_avg * 100) if outbound_stats.factual_accuracy_avg else None
    guidelines_score_avg = (outbound_stats.guidelines_score_avg * 100) if outbound_stats.guidelines_score_avg else None
    tone_score_avg = outbound_stats.tone_score_avg if outbound_stats.tone_score_avg else None
    
    return DashboardDetailsResponse(
        date=target_date.isoformat(),
        total_emails=total_emails,
        queries_count=queries_count,
        info_count=info_count,
        spam_count=spam_count,
        high_priority_count=high_priority_count,
        medium_priority_count=medium_priority_count,
        low_priority_count=low_priority_count,
        responded_count=responded_count,
        pending_count=pending_count,
        avg_response_time=avg_response_time,
        tone_score_avg=tone_score_avg,
        factual_accuracy_avg=factual_accuracy_avg,
        guidelines_score_avg=guidelines_score_avg,
        alerts_count=alerts_count
    )


@router.get("/emails", response_model=EmailsListResponse)
async def get_emails(
    selected_date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format, defaults to today"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in subject and body"),
    priority: Optional[str] = Query(None, description="Filter by priority: high, medium, low"),
    category: Optional[str] = Query(None, description="Filter by category"),
    responded: Optional[bool] = Query(None, description="Filter by response status"),
    db: Session = Depends(get_db)
):
    """
    Get all inbound emails by date with analysis data

    Returns paginated list of inbound emails joined with their analysis data.
    Includes search functionality and filtering options.
    """

    # Parse date or use today
    if selected_date:
        try:
            target_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()

    # Date range for the selected day
    start_datetime = datetime.combine(target_date, datetime.min.time())
    end_datetime = datetime.combine(target_date, datetime.max.time())

    # Base query - join emails with inbound analysis
    base_query = db.query(
        Email.email_identifier.label('email_id'),
        InboundEmailAnalysis.from_email,
        Email.subject,
        Email.body,
        InboundEmailAnalysis.type,
        InboundEmailAnalysis.priority,
        InboundEmailAnalysis.category,
        InboundEmailAnalysis.responded,
        Email.created_at,
        InboundEmailAnalysis.created_at.label('updated_at')
    ).join(
        InboundEmailAnalysis, Email.email_identifier == InboundEmailAnalysis.email_id
    ).filter(
        and_(
            Email.is_inbound == True,
            Email.created_at >= start_datetime,
            Email.created_at <= end_datetime
        )
    )

    # Apply search filter
    if search:
        search_term = f"%{search}%"
        base_query = base_query.filter(
            or_(
                Email.subject.ilike(search_term),
                Email.body.ilike(search_term),
                InboundEmailAnalysis.from_email.ilike(search_term)
            )
        )

    # Apply priority filter
    if priority:
        if priority.lower() == 'high':
            base_query = base_query.filter(InboundEmailAnalysis.priority.ilike('%High%'))
        elif priority.lower() == 'medium':
            base_query = base_query.filter(InboundEmailAnalysis.priority.ilike('%Medium%'))
        elif priority.lower() == 'low':
            base_query = base_query.filter(InboundEmailAnalysis.priority.ilike('%Low%'))

    # Apply category filter
    if category:
        base_query = base_query.filter(InboundEmailAnalysis.category == category)

    # Apply responded filter
    if responded is not None:
        base_query = base_query.filter(InboundEmailAnalysis.responded == responded)

    # Get total count for pagination
    total = base_query.count()

    # Calculate pagination
    total_pages = (total + limit - 1) // limit  # Ceiling division
    offset = (page - 1) * limit

    # Apply pagination and ordering
    emails_data = base_query.order_by(desc(Email.created_at)).offset(offset).limit(limit).all()

    # Convert to response format
    emails = [
        EmailItem(
            email_id=email.email_id,
            from_email=email.from_email,
            subject=email.subject,
            body=email.body,
            type=email.type,
            priority=email.priority,
            category=email.category,
            responded=email.responded,
            created_at=email.created_at,
            updated_at=email.updated_at
        )
        for email in emails_data
    ]

    return EmailsListResponse(
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
        date=target_date.isoformat(),
        emails=emails
    )

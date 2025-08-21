#!/usr/bin/env python3
"""
Daily Reports API Routes
Provides endpoints for generating and retrieving daily analytics reports.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Path
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
import math

from app.services.analytics.daily_report_generator import (
    generate_daily_report,
    get_admin_report_text,
    scheduled_daily_report_generation
)
# from app.services.scheduler.daily_scheduler import get_scheduler_status, trigger_manual_report
from app.db.session import SessionLocal
from app.db.models.daily_reports import DailyReport

logger = logging.getLogger(__name__)

# Pydantic Models for Request/Response
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, description="Page number (starts from 1)")
    limit: int = Field(10, ge=1, le=100, description="Items per page (max 100)")

class DateRangeParams(BaseModel):
    start_date: date = Field(description="Start date (YYYY-MM-DD)")
    end_date: date = Field(description="End date (YYYY-MM-DD)")

class DailyReportResponse(BaseModel):
    report_date: str
    total_emails: int
    queries_count: int
    info_count: int
    spam_count: int
    high_priority_count: int
    medium_priority_count: int
    low_priority_count: int
    responded_count: int
    pending_count: int
    overall_response_rate: float
    high_priority_response_rate: float
    avg_response_time: float
    tone_score_avg: float
    factual_accuracy_avg: float
    guidelines_score_avg: float
    alerts_count: int
    overdue_24hrs_count: int
    factual_errors_detected: int
    tone_violations_count: int
    created_at: str

class PaginatedReportsResponse(BaseModel):
    success: bool
    data: List[DailyReportResponse]
    pagination: Dict[str, Any]
    summary: Dict[str, Any]

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    message: str
    timestamp: str
    path: str

router = APIRouter(prefix="/reports", tags=["Daily Reports"])

@router.post("/generate/{target_date}")
async def generate_report_for_date(
    target_date: date,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Generate daily report for specific date.
    
    Args:
        target_date: Date to generate report for (YYYY-MM-DD format)
        
    Returns:
        Report generation status and basic metrics
    """
    try:
        logger.info(f"📊 Manual report generation requested for {target_date}")
        
        # Generate report in background
        background_tasks.add_task(generate_daily_report, target_date)
        
        return {
            "success": True,
            "message": f"Daily report generation started for {target_date}",
            "date": str(target_date),
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"❌ Error starting report generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

@router.post("/generate/now")
async def generate_report_now(
    target_date: Optional[date] = Query(None, description="Date to generate report for (defaults to yesterday)")
) -> Dict[str, Any]:
    """
    Generate daily report immediately (synchronous).
    
    Args:
        target_date: Date to generate report for (defaults to yesterday)
        
    Returns:
        Complete report data
    """
    try:
        if not target_date:
            target_date = datetime.utcnow().date() - timedelta(days=1)
            
        logger.info(f"📊 Immediate report generation requested for {target_date}")
        
        result = await generate_daily_report(target_date)
        
        return {
            "success": True,
            "message": f"Daily report generated successfully for {target_date}",
            "date": str(target_date),
            "data": result
        }
        
    except Exception as e:
        logger.error(f"❌ Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

@router.get("/daily/{target_date}")
async def get_daily_report(target_date: date) -> Dict[str, Any]:
    """
    Retrieve daily report for specific date.
    
    Args:
        target_date: Date to retrieve report for (YYYY-MM-DD format)
        
    Returns:
        Daily report data from database
    """
    try:
        logger.info(f"📊 Daily report requested for {target_date}")
        
        db = SessionLocal()
        try:
            # Get report from database
            report = db.query(DailyReport).filter(
                DailyReport.report_date == target_date
            ).first()
            
            if not report:
                raise HTTPException(
                    status_code=404, 
                    detail=f"No daily report found for {target_date}. Generate it first using /reports/generate/{target_date}"
                )
            
            # Convert to dictionary
            report_data = {
                "report_date": str(report.report_date),
                "total_emails": report.total_emails,
                "queries_count": report.queries_count,
                "info_count": report.info_count,
                "spam_count": report.spam_count,
                "high_priority_count": report.high_priority_count,
                "medium_priority_count": report.medium_priority_count,
                "low_priority_count": report.low_priority_count,
                "responded_count": report.responded_count,
                "pending_count": report.pending_count,
                "avg_response_time": report.avg_response_time,
                "tone_score_avg": report.tone_score_avg,
                "factual_accuracy_avg": report.factual_accuracy_avg,
                "guidelines_score_avg": report.guidelines_score_avg,
                "alerts_count": report.alerts_count,
                "created_at": str(report.created_at)
            }
            
            return {
                "success": True,
                "date": str(target_date),
                "data": report_data
            }
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error retrieving daily report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve report: {str(e)}")

@router.get("/admin/{target_date}", response_class=PlainTextResponse)
async def get_admin_report(target_date: date) -> str:
    """
    Get formatted admin report for specific date.
    
    Args:
        target_date: Date to get admin report for (YYYY-MM-DD format)
        
    Returns:
        Formatted admin report text
    """
    try:
        logger.info(f"📋 Admin report requested for {target_date}")
        
        # Check if report exists in database first
        db = SessionLocal()
        try:
            existing_report = db.query(DailyReport).filter(
                DailyReport.report_date == target_date
            ).first()
            
            if not existing_report:
                # Generate report if it doesn't exist
                logger.info(f"📊 Report not found, generating for {target_date}")
                await generate_daily_report(target_date)
        finally:
            db.close()
        
        # Get formatted admin report
        admin_report = await get_admin_report_text(target_date)
        
        return admin_report
        
    except Exception as e:
        logger.error(f"❌ Error getting admin report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get admin report: {str(e)}")

@router.get("/list", response_model=PaginatedReportsResponse)
async def get_reports_paginated(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page (max 100)"),
    start_date: Optional[date] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order: asc or desc")
) -> PaginatedReportsResponse:
    """
    Get paginated daily reports with filtering and sorting.
    Frontend-friendly endpoint with comprehensive pagination support.

    Args:
        page: Page number (starts from 1)
        limit: Items per page (max 100)
        start_date: Optional filter from date
        end_date: Optional filter to date
        sort_order: Sort order (asc/desc)

    Returns:
        Paginated reports with metadata
    """
    try:
        # Validate date range if provided
        if start_date and end_date:
            if start_date > end_date:
                raise HTTPException(status_code=400, detail="Start date must be before end date")

            if (end_date - start_date).days > 365:
                raise HTTPException(status_code=400, detail="Date range cannot exceed 365 days")

        # Default date range: last 30 days if not specified
        if not start_date and not end_date:
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=30)
        elif not start_date:
            start_date = end_date - timedelta(days=30)
        elif not end_date:
            end_date = start_date + timedelta(days=30)

        logger.info(f"📊 Paginated reports requested: page={page}, limit={limit}, range={start_date} to {end_date}")

        db = SessionLocal()
        try:
            # Build query with filters
            query = db.query(DailyReport).filter(
                DailyReport.report_date >= start_date,
                DailyReport.report_date <= end_date
            )

            # Apply sorting
            if sort_order == "asc":
                query = query.order_by(DailyReport.report_date.asc())
            else:
                query = query.order_by(DailyReport.report_date.desc())

            # Get total count for pagination
            total_count = query.count()

            # Calculate pagination
            offset = (page - 1) * limit
            total_pages = math.ceil(total_count / limit) if total_count > 0 else 1

            # Get paginated results
            reports = query.offset(offset).limit(limit).all()

            # Convert to response format
            reports_data = []
            for report in reports:
                reports_data.append(DailyReportResponse(
                    report_date=str(report.report_date),
                    total_emails=report.total_emails or 0,
                    queries_count=report.queries_count or 0,
                    info_count=report.info_count or 0,
                    spam_count=report.spam_count or 0,
                    high_priority_count=report.high_priority_count or 0,
                    medium_priority_count=report.medium_priority_count or 0,
                    low_priority_count=report.low_priority_count or 0,
                    responded_count=report.responded_count or 0,
                    pending_count=report.pending_count or 0,
                    overall_response_rate=report.overall_response_rate or 0.0,
                    high_priority_response_rate=report.high_priority_response_rate or 0.0,
                    avg_response_time=report.avg_response_time or 0.0,
                    tone_score_avg=report.tone_score_avg or 0.0,
                    factual_accuracy_avg=report.factual_accuracy_avg or 0.0,
                    guidelines_score_avg=report.guidelines_score_avg or 0.0,
                    alerts_count=report.alerts_count or 0,
                    overdue_24hrs_count=report.overdue_24hrs_count or 0,
                    factual_errors_detected=report.factual_errors_detected or 0,
                    tone_violations_count=report.tone_violations_count or 0,
                    created_at=str(report.created_at)
                ))

            # Calculate summary statistics
            summary = {
                "total_emails_sum": sum(r.total_emails for r in reports_data),
                "total_queries_sum": sum(r.queries_count for r in reports_data),
                "avg_response_rate": sum(r.overall_response_rate for r in reports_data) / len(reports_data) if reports_data else 0,
                "avg_tone_score": sum(r.tone_score_avg for r in reports_data) / len(reports_data) if reports_data else 0,
                "total_alerts": sum(r.alerts_count for r in reports_data),
                "date_range": {
                    "start": str(start_date),
                    "end": str(end_date),
                    "days": (end_date - start_date).days + 1
                }
            }

            # Pagination metadata
            pagination = {
                "current_page": page,
                "per_page": limit,
                "total_items": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
                "next_page": page + 1 if page < total_pages else None,
                "prev_page": page - 1 if page > 1 else None,
                "start_item": offset + 1 if total_count > 0 else 0,
                "end_item": min(offset + limit, total_count)
            }

            return PaginatedReportsResponse(
                success=True,
                data=reports_data,
                pagination=pagination,
                summary=summary
            )

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting paginated reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get paginated reports: {str(e)}")

@router.get("/range/{start_date}/{end_date}")
async def get_reports_range(
    start_date: date = Path(description="Start date (YYYY-MM-DD)"),
    end_date: date = Path(description="End date (YYYY-MM-DD)")
) -> Dict[str, Any]:
    """
    Legacy endpoint - use /reports/list for new implementations.
    Get daily reports for a date range.

    Args:
        start_date: Start date (YYYY-MM-DD format)
        end_date: End date (YYYY-MM-DD format)

    Returns:
        List of daily reports in the date range
    """
    try:
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="Start date must be before end date")

        if (end_date - start_date).days > 31:
            raise HTTPException(status_code=400, detail="Date range cannot exceed 31 days")

        logger.info(f"📊 Reports range requested: {start_date} to {end_date}")

        db = SessionLocal()
        try:
            reports = db.query(DailyReport).filter(
                DailyReport.report_date >= start_date,
                DailyReport.report_date <= end_date
            ).order_by(DailyReport.report_date.desc()).all()

            reports_data = []
            for report in reports:
                reports_data.append({
                    "report_date": str(report.report_date),
                    "total_emails": report.total_emails or 0,
                    "queries_count": report.queries_count or 0,
                    "responded_count": report.responded_count or 0,
                    "pending_count": report.pending_count or 0,
                    "avg_response_time": report.avg_response_time or 0,
                    "tone_score_avg": report.tone_score_avg or 0,
                    "factual_accuracy_avg": report.factual_accuracy_avg or 0,
                    "alerts_count": report.alerts_count or 0
                })

            return {
                "success": True,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "count": len(reports_data),
                "reports": reports_data
            }

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting reports range: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get reports range: {str(e)}")

@router.get("/health")
async def reports_health_check() -> Dict[str, Any]:
    """
    Health check for reports system.
    
    Returns:
        System health status
    """
    try:
        db = SessionLocal()
        try:
            # Check database connectivity
            latest_report = db.query(DailyReport).order_by(
                DailyReport.report_date.desc()
            ).first()
            
            return {
                "success": True,
                "status": "healthy",
                "database_connected": True,
                "latest_report_date": str(latest_report.report_date) if latest_report else None,
                "total_reports": db.query(DailyReport).count()
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Reports health check failed: {str(e)}")
        return {
            "success": False,
            "status": "unhealthy",
            "database_connected": False,
            "error": str(e)
        }

@router.get("/scheduler/status")
async def get_scheduler_status_endpoint() -> Dict[str, Any]:
    """
    Get current scheduler status and next execution time.

    Returns:
        Scheduler status with IST timezone information
    """
    try:
        logger.info("📊 Scheduler status requested")

        # Temporary placeholder until scheduler is properly installed
        status = {
            "is_running": False,
            "timezone": "Asia/Kolkata (IST)",
            "schedule": "Daily at 8:00 PM IST",
            "next_execution": None,
            "next_execution_ist": None,
            "job_count": 0,
            "scheduler_state": "NOT_INSTALLED",
            "note": "Scheduler dependencies not installed yet"
        }

        return {
            "success": True,
            "scheduler": status,
            "message": "Scheduler status retrieved successfully (placeholder)"
        }

    except Exception as e:
        logger.error(f"❌ Error getting scheduler status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get scheduler status: {str(e)}")

@router.post("/scheduler/trigger")
async def trigger_manual_report_endpoint(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Manually trigger daily report generation (IST timezone aware).

    Returns:
        Manual trigger status
    """
    try:
        logger.info("🔄 Manual report generation triggered via API")

        # Use the existing scheduled_daily_report_generation function
        background_tasks.add_task(scheduled_daily_report_generation)

        return {
            "success": True,
            "message": "Manual daily report generation triggered",
            "status": "processing",
            "timezone": "Asia/Kolkata (IST)"
        }

    except Exception as e:
        logger.error(f"❌ Error triggering manual report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger manual report: {str(e)}")

@router.post("/schedule/run")
async def run_scheduled_report(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Legacy endpoint - use /scheduler/trigger instead.
    Manually trigger scheduled daily report generation.

    Returns:
        Scheduled task status
    """
    try:
        logger.info("🔄 Legacy scheduled report generation triggered")

        # Run scheduled task in background
        background_tasks.add_task(scheduled_daily_report_generation)

        return {
            "success": True,
            "message": "Scheduled daily report generation started (legacy endpoint)",
            "status": "processing",
            "note": "Consider using /reports/scheduler/trigger for new implementations"
        }

    except Exception as e:
        logger.error(f"❌ Error triggering scheduled report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger scheduled report: {str(e)}")

@router.get("/summary/latest")
async def get_latest_report_summary() -> Dict[str, Any]:
    """
    Get summary of the latest daily report for dashboard display.

    Returns:
        Latest report summary with key metrics
    """
    try:
        logger.info("📊 Latest report summary requested")

        db = SessionLocal()
        try:
            # Get the latest report
            latest_report = db.query(DailyReport).order_by(
                DailyReport.report_date.desc()
            ).first()

            if not latest_report:
                return {
                    "success": True,
                    "has_data": False,
                    "message": "No reports available yet",
                    "suggestion": "Generate your first report using /reports/generate/now"
                }

            # Calculate trends (compare with previous day)
            previous_report = db.query(DailyReport).filter(
                DailyReport.report_date < latest_report.report_date
            ).order_by(DailyReport.report_date.desc()).first()

            trends = {}
            if previous_report:
                trends = {
                    "emails_change": (latest_report.total_emails or 0) - (previous_report.total_emails or 0),
                    "response_rate_change": (latest_report.overall_response_rate or 0) - (previous_report.overall_response_rate or 0),
                    "tone_score_change": (latest_report.tone_score_avg or 0) - (previous_report.tone_score_avg or 0),
                    "alerts_change": (latest_report.alerts_count or 0) - (previous_report.alerts_count or 0)
                }

            return {
                "success": True,
                "has_data": True,
                "latest_report": {
                    "date": str(latest_report.report_date),
                    "total_emails": latest_report.total_emails or 0,
                    "queries_count": latest_report.queries_count or 0,
                    "overall_response_rate": latest_report.overall_response_rate or 0,
                    "high_priority_response_rate": latest_report.high_priority_response_rate or 0,
                    "tone_score_avg": latest_report.tone_score_avg or 0,
                    "factual_accuracy_avg": latest_report.factual_accuracy_avg or 0,
                    "alerts_count": latest_report.alerts_count or 0,
                    "overdue_24hrs_count": latest_report.overdue_24hrs_count or 0,
                    "created_at": str(latest_report.created_at)
                },
                "trends": trends,
                "comparison_date": str(previous_report.report_date) if previous_report else None
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Error getting latest report summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get latest report summary: {str(e)}")

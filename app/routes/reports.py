#!/usr/bin/env python3
"""
Daily Reports API Routes
Provides endpoints for generating and retrieving daily analytics reports.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import PlainTextResponse

from app.services.analytics.daily_report_generator import (
    generate_daily_report,
    get_admin_report_text,
    scheduled_daily_report_generation
)
from app.db.session import SessionLocal
from app.db.models.daily_reports import DailyReport

logger = logging.getLogger(__name__)

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

@router.get("/range/{start_date}/{end_date}")
async def get_reports_range(
    start_date: date,
    end_date: date
) -> Dict[str, Any]:
    """
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
                    "total_emails": report.total_emails,
                    "queries_count": report.queries_count,
                    "responded_count": report.responded_count,
                    "pending_count": report.pending_count,
                    "avg_response_time": report.avg_response_time,
                    "tone_score_avg": report.tone_score_avg,
                    "factual_accuracy_avg": report.factual_accuracy_avg,
                    "alerts_count": report.alerts_count
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

@router.post("/schedule/run")
async def run_scheduled_report(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Manually trigger scheduled daily report generation.
    
    Returns:
        Scheduled task status
    """
    try:
        logger.info("🔄 Manual scheduled report generation triggered")
        
        # Run scheduled task in background
        background_tasks.add_task(scheduled_daily_report_generation)
        
        return {
            "success": True,
            "message": "Scheduled daily report generation started",
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"❌ Error triggering scheduled report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger scheduled report: {str(e)}")

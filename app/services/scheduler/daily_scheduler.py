#!/usr/bin/env python3
"""
Daily Report Scheduler - Indian Timezone (IST)
Schedules daily report generation at 8:00 PM IST every day.
"""

import logging
import asyncio
from datetime import datetime, date, timedelta
from typing import Optional
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.asyncio import AsyncIOExecutor

from app.services.analytics.daily_report_generator import scheduled_daily_report_generation
from app.config import settings

logger = logging.getLogger(__name__)

class DailyReportScheduler:
    """
    Scheduler for daily report generation at 8:00 PM IST.
    Handles Indian timezone conversion and error recovery.
    """
    
    def __init__(self):
        """Initialize the scheduler with Indian timezone configuration"""
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.ist_timezone = pytz.timezone('Asia/Kolkata')
        self.is_running = False
        
        # Configure scheduler
        executors = {
            'default': AsyncIOExecutor()
        }
        
        job_defaults = {
            'coalesce': True,  # Combine multiple missed executions into one
            'max_instances': 1,  # Only one instance of the job at a time
            'misfire_grace_time': 3600  # Allow 1 hour grace period for missed jobs
        }
        
        self.scheduler = AsyncIOScheduler(
            executors=executors,
            job_defaults=job_defaults,
            timezone=self.ist_timezone
        )
        
        logger.info("🕐 Daily report scheduler initialized for IST timezone")
    
    async def start_scheduler(self):
        """Start the daily report scheduler"""
        try:
            if self.is_running:
                logger.warning("⚠️ Scheduler is already running")
                return
            
            # Add the daily report job - runs at 8:00 PM IST every day
            self.scheduler.add_job(
                func=self._scheduled_report_wrapper,
                trigger=CronTrigger(
                    hour=20,  # 8:00 PM
                    minute=0,  # At exactly 8:00
                    second=0,
                    timezone=self.ist_timezone
                ),
                id='daily_report_generation',
                name='Daily Report Generation (8:00 PM IST)',
                replace_existing=True
            )
            
            # Start the scheduler
            self.scheduler.start()
            self.is_running = True
            
            # Log next execution time
            next_run = self.scheduler.get_job('daily_report_generation').next_run_time
            logger.info(f"✅ Daily report scheduler started successfully")
            logger.info(f"📅 Next report generation: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
        except Exception as e:
            logger.error(f"❌ Failed to start scheduler: {str(e)}")
            raise
    
    async def stop_scheduler(self):
        """Stop the daily report scheduler"""
        try:
            if not self.is_running:
                logger.warning("⚠️ Scheduler is not running")
                return
            
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("🛑 Daily report scheduler stopped successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to stop scheduler: {str(e)}")
            raise
    
    async def _scheduled_report_wrapper(self):
        """
        Wrapper for scheduled report generation with error handling and logging.
        This runs at 8:00 PM IST every day.
        """
        try:
            # Get current IST time
            ist_now = datetime.now(self.ist_timezone)
            report_date = ist_now.date() - timedelta(days=1)  # Generate report for previous day
            
            logger.info(f"🔄 Starting scheduled daily report generation at {ist_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            logger.info(f"📊 Generating report for date: {report_date}")
            
            # Generate the report
            success = await scheduled_daily_report_generation()
            
            if success:
                logger.info(f"✅ Scheduled daily report generated successfully for {report_date}")
                
                # Log completion time
                completion_time = datetime.now(self.ist_timezone)
                duration = (completion_time - ist_now).total_seconds()
                logger.info(f"⏱️ Report generation completed in {duration:.2f} seconds")
                
            else:
                logger.error(f"❌ Scheduled daily report generation failed for {report_date}")
                
                # TODO: Add notification/alert system here
                # await self._send_failure_alert(report_date)
                
        except Exception as e:
            logger.error(f"❌ Critical error in scheduled report generation: {str(e)}", exc_info=True)
            
            # TODO: Add critical error notification
            # await self._send_critical_error_alert(str(e))
    
    def get_next_execution_time(self) -> Optional[datetime]:
        """Get the next scheduled execution time"""
        try:
            if not self.is_running:
                return None
            
            job = self.scheduler.get_job('daily_report_generation')
            return job.next_run_time if job else None
            
        except Exception as e:
            logger.error(f"❌ Error getting next execution time: {str(e)}")
            return None
    
    def get_scheduler_status(self) -> dict:
        """Get comprehensive scheduler status"""
        try:
            next_run = self.get_next_execution_time()
            
            return {
                "is_running": self.is_running,
                "timezone": "Asia/Kolkata (IST)",
                "schedule": "Daily at 8:00 PM IST",
                "next_execution": next_run.isoformat() if next_run else None,
                "next_execution_ist": next_run.strftime('%Y-%m-%d %H:%M:%S %Z') if next_run else None,
                "job_count": len(self.scheduler.get_jobs()) if self.scheduler else 0,
                "scheduler_state": self.scheduler.state if self.scheduler else "NOT_INITIALIZED"
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting scheduler status: {str(e)}")
            return {
                "is_running": False,
                "error": str(e),
                "timezone": "Asia/Kolkata (IST)",
                "schedule": "Daily at 8:00 PM IST"
            }
    
    async def trigger_manual_execution(self) -> bool:
        """Manually trigger report generation (for testing)"""
        try:
            logger.info("🔄 Manual report generation triggered")
            
            success = await scheduled_daily_report_generation()
            
            if success:
                logger.info("✅ Manual report generation completed successfully")
            else:
                logger.error("❌ Manual report generation failed")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error in manual report generation: {str(e)}")
            return False


# Global scheduler instance
_scheduler_instance: Optional[DailyReportScheduler] = None

def get_scheduler() -> DailyReportScheduler:
    """Get the global scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = DailyReportScheduler()
    return _scheduler_instance

async def start_daily_scheduler():
    """Start the daily report scheduler (called during app startup)"""
    try:
        scheduler = get_scheduler()
        await scheduler.start_scheduler()
        logger.info("🚀 Daily report scheduler service started")
        
    except Exception as e:
        logger.error(f"❌ Failed to start daily scheduler service: {str(e)}")
        raise

async def stop_daily_scheduler():
    """Stop the daily report scheduler (called during app shutdown)"""
    try:
        scheduler = get_scheduler()
        await scheduler.stop_scheduler()
        logger.info("🛑 Daily report scheduler service stopped")
        
    except Exception as e:
        logger.error(f"❌ Failed to stop daily scheduler service: {str(e)}")

def get_scheduler_status() -> dict:
    """Get current scheduler status"""
    try:
        scheduler = get_scheduler()
        return scheduler.get_scheduler_status()
        
    except Exception as e:
        logger.error(f"❌ Error getting scheduler status: {str(e)}")
        return {
            "is_running": False,
            "error": str(e),
            "timezone": "Asia/Kolkata (IST)",
            "schedule": "Daily at 8:00 PM IST"
        }

async def trigger_manual_report() -> bool:
    """Manually trigger report generation"""
    try:
        scheduler = get_scheduler()
        return await scheduler.trigger_manual_execution()
        
    except Exception as e:
        logger.error(f"❌ Error triggering manual report: {str(e)}")
        return False

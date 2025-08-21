"""
Alert Scheduler Service
Handles scheduled monitoring and alert generation for support quality issues.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.services.alerts.alert_service import AlertService

logger = logging.getLogger(__name__)

class AlertScheduler:
    """Background scheduler for alert monitoring"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        
    async def start(self):
        """Start all scheduled alert monitoring jobs"""
        if self.is_running:
            logger.warning("Alert scheduler is already running")
            return
        
        try:
            # SLA Breach Monitoring - Every 15 minutes
            self.scheduler.add_job(
                self._monitor_sla_breaches,
                IntervalTrigger(minutes=15),
                id="sla_breach_monitor",
                replace_existing=True,
                max_instances=1
            )
            
            # Aging Query Detection - Every hour
            self.scheduler.add_job(
                self._monitor_aging_queries,
                IntervalTrigger(hours=1),
                id="aging_query_monitor", 
                replace_existing=True,
                max_instances=1
            )
            
            # Factual Error Detection - Every 30 minutes
            self.scheduler.add_job(
                self._monitor_factual_errors,
                IntervalTrigger(minutes=30),
                id="factual_error_monitor",
                replace_existing=True,
                max_instances=1
            )
            
            # Negative Sentiment Detection - Every 30 minutes
            self.scheduler.add_job(
                self._monitor_negative_sentiment,
                IntervalTrigger(minutes=30),
                id="negative_sentiment_monitor",
                replace_existing=True,
                max_instances=1
            )
            
            # Daily Alert Summary - Every day at 9 AM
            self.scheduler.add_job(
                self._send_daily_alert_summary,
                CronTrigger(hour=9, minute=0),
                id="daily_alert_summary",
                replace_existing=True,
                max_instances=1
            )
            
            # Alert Cleanup - Every day at 2 AM
            self.scheduler.add_job(
                self._cleanup_old_alerts,
                CronTrigger(hour=2, minute=0),
                id="alert_cleanup",
                replace_existing=True,
                max_instances=1
            )
            
            self.scheduler.start()
            self.is_running = True
            
            logger.info("Alert scheduler started successfully with 6 monitoring jobs")
            
        except Exception as e:
            logger.error(f"Failed to start alert scheduler: {e}")
            raise
    
    async def stop(self):
        """Stop the alert scheduler"""
        if not self.is_running:
            return
        
        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("Alert scheduler stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping alert scheduler: {e}")
    
    async def _monitor_sla_breaches(self):
        """Monitor for SLA breaches"""
        try:
            logger.info("🔍 Starting SLA breach monitoring...")
            alerts_created = await AlertService.check_sla_breaches()
            logger.info(f"✅ SLA breach monitoring completed. Created {alerts_created} alerts.")
        except Exception as e:
            logger.error(f"❌ Error in SLA breach monitoring: {e}")
    
    async def _monitor_aging_queries(self):
        """Monitor for aging queries"""
        try:
            logger.info("🔍 Starting aging query monitoring...")
            alerts_created = await AlertService.check_aging_queries()
            logger.info(f"✅ Aging query monitoring completed. Created {alerts_created} alerts.")
        except Exception as e:
            logger.error(f"❌ Error in aging query monitoring: {e}")
    
    async def _monitor_factual_errors(self):
        """Monitor for factual errors in responses"""
        try:
            logger.info("🔍 Starting factual error monitoring...")
            alerts_created = await AlertService.check_factual_errors()
            logger.info(f"✅ Factual error monitoring completed. Created {alerts_created} alerts.")
        except Exception as e:
            logger.error(f"❌ Error in factual error monitoring: {e}")
    
    async def _monitor_negative_sentiment(self):
        """Monitor for negative sentiment in responses"""
        try:
            logger.info("🔍 Starting negative sentiment monitoring...")
            alerts_created = await self._check_negative_sentiment()
            logger.info(f"✅ Negative sentiment monitoring completed. Created {alerts_created} alerts.")
        except Exception as e:
            logger.error(f"❌ Error in negative sentiment monitoring: {e}")
    
    async def _check_negative_sentiment(self) -> int:
        """Check for negative sentiment in recent responses"""
        from app.db.session import SessionLocal
        from app.db.models import OutboundEmailAnalysis, Email, Alert
        from sqlalchemy import and_
        
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            last_check = now - timedelta(hours=1)  # Check last hour
            alerts_created = 0
            
            # Find responses with poor tone scores
            poor_tone_responses = db.query(OutboundEmailAnalysis).join(Email).filter(
                and_(
                    OutboundEmailAnalysis.tone.in_(["poor", "negative", "unprofessional"]),
                    OutboundEmailAnalysis.created_at >= last_check,
                    ~Email.alerts.any(
                        and_(
                            Alert.alert_type == "negative_sentiment",
                            Alert.triggered_at >= last_check
                        )
                    )
                )
            ).all()
            
            # Create negative sentiment alerts
            for response in poor_tone_responses:
                # Convert tone to numeric score for threshold comparison
                tone_score = 0.3 if response.tone == "poor" else 0.4
                
                alert = await AlertService.create_immediate_alert(
                    alert_type="negative_sentiment",
                    email_id=response.email_id,
                    description=f"Negative sentiment detected in response (tone: {response.tone})",
                    current_value=tone_score,
                    threshold_value=0.6,
                    send_notification=False  # Disable email notifications
                )
                
                alerts_created += 1
                logger.info(f"Negative sentiment alert created for email {response.email_id}")
            
            return alerts_created
            
        except Exception as e:
            logger.error(f"Error checking negative sentiment: {e}")
            return 0
        finally:
            db.close()
    
    async def _send_daily_alert_summary(self):
        """Daily alert summary (email notifications disabled)"""
        try:
            logger.info("📊 Daily alert summary - email notifications disabled")
            logger.info("ℹ️ Use API endpoints /alerts/dashboard and /alerts/statistics for alert data")

        except Exception as e:
            logger.error(f"❌ Error in daily summary job: {e}")
    
    async def _cleanup_old_alerts(self):
        """Clean up old resolved alerts"""
        try:
            logger.info("🧹 Starting alert cleanup...")
            
            from app.db.session import SessionLocal
            from app.db.models import Alert
            
            db = SessionLocal()
            try:
                # Delete resolved alerts older than 30 days
                cutoff_date = datetime.utcnow() - timedelta(days=30)
                
                deleted_count = db.query(Alert).filter(
                    and_(
                        Alert.resolved_at.isnot(None),
                        Alert.resolved_at <= cutoff_date
                    )
                ).delete()
                
                db.commit()
                
                logger.info(f"✅ Alert cleanup completed. Deleted {deleted_count} old alerts.")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Error in alert cleanup: {e}")
    
    def get_job_status(self) -> Dict[str, Any]:
        """Get status of all scheduled jobs"""
        if not self.is_running:
            return {"status": "stopped", "jobs": []}
        
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name or job.id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        
        return {
            "status": "running",
            "jobs": jobs,
            "total_jobs": len(jobs)
        }
    
    async def trigger_manual_check(self, check_type: str) -> Dict[str, Any]:
        """Manually trigger a specific type of check"""
        try:
            if check_type == "sla_breach":
                alerts_created = await AlertService.check_sla_breaches()
                return {"success": True, "alerts_created": alerts_created, "type": "SLA Breach"}
            
            elif check_type == "aging_query":
                alerts_created = await AlertService.check_aging_queries()
                return {"success": True, "alerts_created": alerts_created, "type": "Aging Query"}
            
            elif check_type == "factual_error":
                alerts_created = await AlertService.check_factual_errors()
                return {"success": True, "alerts_created": alerts_created, "type": "Factual Error"}
            
            elif check_type == "negative_sentiment":
                alerts_created = await self._check_negative_sentiment()
                return {"success": True, "alerts_created": alerts_created, "type": "Negative Sentiment"}
            
            else:
                return {"success": False, "error": f"Unknown check type: {check_type}"}
                
        except Exception as e:
            logger.error(f"Error in manual check {check_type}: {e}")
            return {"success": False, "error": str(e)}

# Global scheduler instance
alert_scheduler = AlertScheduler()

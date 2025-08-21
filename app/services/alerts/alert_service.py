"""
Real-Time Alert Service
Handles creation, management, and notification of alerts for support quality issues.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.db.session import SessionLocal
from app.db.models import Alert, Email, InboundEmailAnalysis, OutboundEmailAnalysis
from app.services.alerts.email_notifier import EmailNotifier

logger = logging.getLogger(__name__)

class AlertConfiguration:
    """Alert system configuration and thresholds"""
    
    # SLA Thresholds (in hours)
    SLA_THRESHOLDS = {
        "high_priority": 4,      # 4 hours for high priority
        "medium_priority": 8,    # 8 hours for medium priority  
        "low_priority": 24,      # 24 hours for low priority
        "aging_threshold": 24    # 24 hours for aging queries
    }
    
    # Quality Score Thresholds
    QUALITY_THRESHOLDS = {
        "factual_accuracy_min": 0.7,    # Below 70% accuracy
        "sentiment_score_min": 0.6,     # Below 60% sentiment
        "compliance_score_min": 0.8     # Below 80% compliance
    }
    
    # Alert Severity Mapping
    SEVERITY_MAPPING = {
        "sla_breach_high": "critical",
        "sla_breach_medium": "warning", 
        "sla_breach_low": "warning",
        "aging_query": "warning",
        "factual_error": "critical",
        "negative_sentiment": "warning"
    }

class AlertService:
    """Core alert management service"""
    
    @staticmethod
    async def create_immediate_alert(
        alert_type: str,
        email_id: str,
        description: str,
        priority_level: Optional[str] = None,
        current_value: Optional[float] = None,
        threshold_value: Optional[float] = None,
        send_notification: bool = True
    ) -> Alert:
        """
        Create an immediate alert and optionally send notification.
        
        Args:
            alert_type: Type of alert (sla_breach, factual_error, etc.)
            email_id: Associated email identifier
            description: Human-readable alert description
            priority_level: Priority level of the associated email
            current_value: Current metric value that triggered alert
            threshold_value: Threshold that was breached
            send_notification: Whether to send email notification
            
        Returns:
            Created Alert object
        """
        db = SessionLocal()
        try:
            # Determine severity based on alert type and priority
            severity = AlertService._determine_severity(alert_type, priority_level)
            
            # Generate alert title
            title = AlertService._generate_alert_title(alert_type, priority_level, current_value)
            
            # Create alert record
            alert = Alert(
                alert_type=alert_type,
                type=alert_type,  # For backward compatibility
                severity=severity,
                email_id=email_id,
                title=title,
                description=description,
                priority_level=priority_level,
                current_value=current_value,
                threshold_value=threshold_value,
                triggered_at=datetime.utcnow()
            )
            
            db.add(alert)
            db.commit()
            db.refresh(alert)
            
            logger.info(f"Created {severity} alert: {alert_type} for email {email_id}")
            
            # Email notifications disabled - using API-only mode
            # if send_notification:
            #     await AlertService._send_email_notification(alert)
            logger.info(f"Alert {alert.id} created - email notifications disabled, use API endpoints")
            
            return alert
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create alert for email {email_id}: {e}")
            raise
        finally:
            db.close()
    
    @staticmethod
    async def check_sla_breaches():
        """Check for SLA breaches and create alerts"""
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            alerts_created = 0
            
            # Check each priority level
            for priority_key, threshold_hours in AlertConfiguration.SLA_THRESHOLDS.items():
                if priority_key == "aging_threshold":
                    continue
                
                # Extract priority name (high, medium, low)
                priority_name = priority_key.replace("_priority", "")
                threshold_time = now - timedelta(hours=threshold_hours)
                
                # Find unresponded emails past SLA that don't already have SLA breach alerts
                unresponded_emails = db.query(Email).join(InboundEmailAnalysis).filter(
                    and_(
                        or_(
                            InboundEmailAnalysis.priority.like(f"%{priority_name}%"),
                            InboundEmailAnalysis.priority == priority_name
                        ),
                        InboundEmailAnalysis.responded == False,
                        Email.created_at <= threshold_time,
                        ~Email.alerts.any(
                            and_(
                                Alert.alert_type == "sla_breach",
                                Alert.resolved_at.is_(None)
                            )
                        )
                    )
                ).all()
                
                # Create alerts for SLA breaches
                for email in unresponded_emails:
                    hours_elapsed = (now - email.created_at).total_seconds() / 3600
                    
                    alert = await AlertService.create_immediate_alert(
                        alert_type="sla_breach",
                        email_id=email.email_identifier,
                        description=f"{priority_name.title()} priority query unresponded for {hours_elapsed:.1f} hours (SLA: {threshold_hours}h)",
                        priority_level=priority_name,
                        current_value=hours_elapsed,
                        threshold_value=threshold_hours,
                        send_notification=False  # Disable email notifications
                    )
                    
                    alerts_created += 1
                    logger.info(f"SLA breach alert created for {priority_name} priority email {email.email_identifier}")
            
            logger.info(f"SLA breach check completed. Created {alerts_created} alerts.")
            return alerts_created
            
        except Exception as e:
            logger.error(f"Error checking SLA breaches: {e}")
            return 0
        finally:
            db.close()
    
    @staticmethod
    async def check_aging_queries():
        """Check for queries aging beyond 24 hours"""
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            aging_threshold = AlertConfiguration.SLA_THRESHOLDS["aging_threshold"]
            threshold_time = now - timedelta(hours=aging_threshold)
            alerts_created = 0
            
            # Find aging emails without aging alerts
            aging_emails = db.query(Email).join(InboundEmailAnalysis).filter(
                and_(
                    InboundEmailAnalysis.responded == False,
                    Email.created_at <= threshold_time,
                    ~Email.alerts.any(
                        and_(
                            Alert.alert_type == "aging_query",
                            Alert.resolved_at.is_(None)
                        )
                    )
                )
            ).all()
            
            # Create aging alerts
            for email in aging_emails:
                hours_elapsed = (now - email.created_at).total_seconds() / 3600
                
                alert = await AlertService.create_immediate_alert(
                    alert_type="aging_query",
                    email_id=email.email_identifier,
                    description=f"Query aging for {hours_elapsed:.1f} hours without response",
                    current_value=hours_elapsed,
                    threshold_value=aging_threshold,
                    send_notification=False  # Disable email notifications
                )
                
                alerts_created += 1
                logger.info(f"Aging query alert created for email {email.email_identifier}")
            
            logger.info(f"Aging query check completed. Created {alerts_created} alerts.")
            return alerts_created
            
        except Exception as e:
            logger.error(f"Error checking aging queries: {e}")
            return 0
        finally:
            db.close()
    
    @staticmethod
    async def check_factual_errors():
        """Check for factual errors in recent responses"""
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            last_check = now - timedelta(hours=1)  # Check last hour
            alerts_created = 0
            
            # Find outbound emails with low factual accuracy that don't have alerts
            error_responses = db.query(OutboundEmailAnalysis).join(Email).filter(
                and_(
                    OutboundEmailAnalysis.factual_accuracy < AlertConfiguration.QUALITY_THRESHOLDS["factual_accuracy_min"],
                    OutboundEmailAnalysis.factual_accuracy.isnot(None),
                    OutboundEmailAnalysis.created_at >= last_check,
                    ~Email.alerts.any(
                        and_(
                            Alert.alert_type == "factual_error",
                            Alert.triggered_at >= last_check
                        )
                    )
                )
            ).all()
            
            # Create factual error alerts
            for response in error_responses:
                alert = await AlertService.create_immediate_alert(
                    alert_type="factual_error",
                    email_id=response.email_id,
                    description=f"Factual accuracy score {response.factual_accuracy:.2f} below threshold {AlertConfiguration.QUALITY_THRESHOLDS['factual_accuracy_min']}",
                    current_value=response.factual_accuracy,
                    threshold_value=AlertConfiguration.QUALITY_THRESHOLDS["factual_accuracy_min"],
                    send_notification=False  # Disable email notifications
                )
                
                alerts_created += 1
                logger.info(f"Factual error alert created for email {response.email_id}")
            
            logger.info(f"Factual error check completed. Created {alerts_created} alerts.")
            return alerts_created
            
        except Exception as e:
            logger.error(f"Error checking factual errors: {e}")
            return 0
        finally:
            db.close()
    
    @staticmethod
    def _determine_severity(alert_type: str, priority_level: Optional[str] = None) -> str:
        """Determine alert severity based on type and priority"""
        if alert_type == "sla_breach" and priority_level == "high":
            return "critical"
        elif alert_type == "factual_error":
            return "critical"
        elif alert_type in ["negative_sentiment", "aging_query", "sla_breach"]:
            return "warning"
        else:
            return "info"
    
    @staticmethod
    def _generate_alert_title(alert_type: str, priority_level: Optional[str] = None, current_value: Optional[float] = None) -> str:
        """Generate human-readable alert title"""
        if alert_type == "sla_breach":
            return f"SLA Breach: {priority_level.title() if priority_level else 'Unknown'} Priority Query Overdue"
        elif alert_type == "aging_query":
            return f"Aging Query: {current_value:.1f}h Without Response" if current_value else "Query Aging Without Response"
        elif alert_type == "factual_error":
            return f"Factual Error: Low Accuracy Score ({current_value:.2f})" if current_value else "Factual Error Detected"
        elif alert_type == "negative_sentiment":
            return f"Negative Sentiment: Poor Response Tone ({current_value:.2f})" if current_value else "Negative Sentiment Detected"
        else:
            return f"Alert: {alert_type.replace('_', ' ').title()}"
    
    @staticmethod
    async def _send_email_notification(alert: Alert):
        """Send email notification for alert"""
        try:
            success = await EmailNotifier.send_alert_email(alert)
            
            # Update alert with notification status
            db = SessionLocal()
            try:
                db_alert = db.query(Alert).filter(Alert.id == alert.id).first()
                if db_alert:
                    db_alert.email_notification_sent = success
                    db_alert.email_sent_at = datetime.utcnow() if success else None
                    if not success:
                        db_alert.notification_retry_count += 1
                    db.commit()
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to send email notification for alert {alert.id}: {e}")
    
    @staticmethod
    async def acknowledge_alert(alert_id: int, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        db = SessionLocal()
        try:
            alert = db.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                return False
            
            alert.acknowledged_at = datetime.utcnow()
            alert.acknowledged_by = acknowledged_by
            db.commit()
            
            logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
            return False
        finally:
            db.close()
    
    @staticmethod
    async def resolve_alert(alert_id: int) -> bool:
        """Mark an alert as resolved"""
        db = SessionLocal()
        try:
            alert = db.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                return False
            
            alert.resolved_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Alert {alert_id} resolved")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve alert {alert_id}: {e}")
            return False
        finally:
            db.close()

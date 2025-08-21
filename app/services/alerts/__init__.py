"""
Real-Time Alert System Package
Provides comprehensive alert monitoring and notification for support quality issues.
"""

from .alert_service import AlertService, AlertConfiguration
from .alert_scheduler import AlertScheduler, alert_scheduler
from .email_notifier import EmailNotifier
from .alert_summary import AlertSummaryService

__all__ = [
    "AlertService",
    "AlertConfiguration", 
    "AlertScheduler",
    "alert_scheduler",
    "EmailNotifier",
    "AlertSummaryService"
]

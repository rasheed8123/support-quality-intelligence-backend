"""
Alert Summary Service
Generates daily and periodic summaries of alert activity.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.db.session import SessionLocal
from app.db.models import Alert, Email, InboundEmailAnalysis, OutboundEmailAnalysis
from app.services.alerts.email_notifier import EmailNotifier

logger = logging.getLogger(__name__)

class AlertSummaryService:
    """Service for generating alert summaries and reports"""
    
    @staticmethod
    async def generate_daily_summary(target_date: datetime = None) -> bool:
        """
        Generate and send daily alert summary email.
        
        Args:
            target_date: Date to generate summary for (defaults to yesterday)
            
        Returns:
            bool: True if summary was generated and sent successfully
        """
        if target_date is None:
            target_date = datetime.utcnow().date() - timedelta(days=1)
        
        try:
            summary_data = await AlertSummaryService._collect_daily_data(target_date)
            
            if summary_data["total_alerts"] == 0:
                logger.info(f"No alerts to summarize for {target_date}")
                return False
            
            # Send summary email
            success = await AlertSummaryService._send_daily_summary_email(summary_data, target_date)
            
            if success:
                logger.info(f"Daily alert summary sent successfully for {target_date}")
            else:
                logger.error(f"Failed to send daily alert summary for {target_date}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error generating daily alert summary for {target_date}: {e}")
            return False
    
    @staticmethod
    async def _collect_daily_data(target_date) -> Dict[str, Any]:
        """Collect alert data for the specified date"""
        db = SessionLocal()
        try:
            start_time = datetime.combine(target_date, datetime.min.time())
            end_time = start_time + timedelta(days=1)
            
            # Total alerts for the day
            total_alerts = db.query(Alert).filter(
                and_(
                    Alert.triggered_at >= start_time,
                    Alert.triggered_at < end_time
                )
            ).count()
            
            # Alerts by severity
            severity_counts = db.query(
                Alert.severity,
                func.count(Alert.id).label('count')
            ).filter(
                and_(
                    Alert.triggered_at >= start_time,
                    Alert.triggered_at < end_time
                )
            ).group_by(Alert.severity).all()
            
            # Alerts by type
            type_counts = db.query(
                Alert.alert_type,
                func.count(Alert.id).label('count')
            ).filter(
                and_(
                    Alert.triggered_at >= start_time,
                    Alert.triggered_at < end_time
                )
            ).group_by(Alert.alert_type).all()
            
            # Critical unresolved alerts
            critical_unresolved = db.query(Alert).filter(
                and_(
                    Alert.triggered_at >= start_time,
                    Alert.triggered_at < end_time,
                    Alert.severity == "critical",
                    Alert.resolved_at.is_(None)
                )
            ).all()
            
            # Top affected emails (most alerts)
            top_affected_emails = db.query(
                Alert.email_id,
                func.count(Alert.id).label('alert_count')
            ).filter(
                and_(
                    Alert.triggered_at >= start_time,
                    Alert.triggered_at < end_time
                )
            ).group_by(Alert.email_id).order_by(
                func.count(Alert.id).desc()
            ).limit(5).all()
            
            # Resolution statistics
            resolved_count = db.query(Alert).filter(
                and_(
                    Alert.triggered_at >= start_time,
                    Alert.triggered_at < end_time,
                    Alert.resolved_at.isnot(None)
                )
            ).count()
            
            return {
                "total_alerts": total_alerts,
                "severity_counts": {severity: count for severity, count in severity_counts},
                "type_counts": {alert_type: count for alert_type, count in type_counts},
                "critical_unresolved": [
                    {
                        "id": alert.id,
                        "title": alert.title,
                        "email_id": alert.email_id,
                        "triggered_at": alert.triggered_at
                    }
                    for alert in critical_unresolved
                ],
                "top_affected_emails": [
                    {"email_id": email_id, "alert_count": count}
                    for email_id, count in top_affected_emails
                ],
                "resolved_count": resolved_count,
                "resolution_rate": (resolved_count / total_alerts * 100) if total_alerts > 0 else 0
            }
            
        finally:
            db.close()
    
    @staticmethod
    async def _send_daily_summary_email(summary_data: Dict[str, Any], target_date) -> bool:
        """Send daily summary email to administrators"""
        try:
            # Generate email content
            subject = f"📊 Daily Alert Summary - {target_date.strftime('%Y-%m-%d')}"
            html_body = AlertSummaryService._generate_summary_html(summary_data, target_date)
            text_body = AlertSummaryService._generate_summary_text(summary_data, target_date)
            
            # Send to admin recipients
            recipients = ["admin@company.com", "support-manager@company.com"]
            
            success = await EmailNotifier._send_email(
                recipients=recipients,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending daily summary email: {e}")
            return False
    
    @staticmethod
    def _generate_summary_html(summary_data: Dict[str, Any], target_date) -> str:
        """Generate HTML email body for daily summary"""
        
        severity_colors = {
            "critical": "#dc2626",
            "warning": "#d97706", 
            "info": "#2563eb"
        }
        
        # Generate severity breakdown HTML
        severity_html = ""
        for severity, count in summary_data["severity_counts"].items():
            color = severity_colors.get(severity, "#6b7280")
            severity_html += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">
                        <span style="color: {color}; font-weight: bold;">{severity.title()}</span>
                    </td>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">
                        {count}
                    </td>
                </tr>
            """
        
        # Generate alert type breakdown HTML
        type_html = ""
        for alert_type, count in summary_data["type_counts"].items():
            type_html += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">
                        {alert_type.replace('_', ' ').title()}
                    </td>
                    <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">
                        {count}
                    </td>
                </tr>
            """
        
        # Generate critical unresolved alerts HTML
        critical_html = ""
        if summary_data["critical_unresolved"]:
            for alert in summary_data["critical_unresolved"]:
                critical_html += f"""
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">
                            {alert['title']}
                        </td>
                        <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">
                            {alert['email_id']}
                        </td>
                        <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">
                            {alert['triggered_at'].strftime('%H:%M')}
                        </td>
                    </tr>
                """
        else:
            critical_html = """
                <tr>
                    <td colspan="3" style="padding: 8px; text-align: center; color: #10b981;">
                        ✅ No critical unresolved alerts
                    </td>
                </tr>
            """
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Daily Alert Summary</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f9fafb; }}
                .container {{ max-width: 800px; margin: 0 auto; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }}
                .header {{ background-color: #1f2937; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px; }}
                .summary-box {{ background-color: #f3f4f6; border-radius: 8px; padding: 20px; margin: 20px 0; }}
                .metric {{ display: inline-block; margin: 10px 20px; text-align: center; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #1f2937; }}
                .metric-label {{ font-size: 14px; color: #6b7280; }}
                .table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .table th, .table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
                .table th {{ background-color: #f9fafb; font-weight: bold; }}
                .footer {{ background-color: #f9fafb; padding: 20px; text-align: center; color: #6b7280; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Daily Alert Summary</h1>
                    <p>{target_date.strftime('%A, %B %d, %Y')}</p>
                </div>
                
                <div class="content">
                    <div class="summary-box">
                        <div class="metric">
                            <div class="metric-value">{summary_data['total_alerts']}</div>
                            <div class="metric-label">Total Alerts</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{summary_data['resolved_count']}</div>
                            <div class="metric-label">Resolved</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{summary_data['resolution_rate']:.1f}%</div>
                            <div class="metric-label">Resolution Rate</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{len(summary_data['critical_unresolved'])}</div>
                            <div class="metric-label">Critical Unresolved</div>
                        </div>
                    </div>
                    
                    <h3>Alerts by Severity</h3>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Severity</th>
                                <th>Count</th>
                            </tr>
                        </thead>
                        <tbody>
                            {severity_html}
                        </tbody>
                    </table>
                    
                    <h3>Alerts by Type</h3>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Alert Type</th>
                                <th>Count</th>
                            </tr>
                        </thead>
                        <tbody>
                            {type_html}
                        </tbody>
                    </table>
                    
                    <h3>Critical Unresolved Alerts</h3>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Alert</th>
                                <th>Email ID</th>
                                <th>Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            {critical_html}
                        </tbody>
                    </table>
                </div>
                
                <div class="footer">
                    <p>Support Quality Intelligence System - Alert Summary</p>
                    <p>Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_template
    
    @staticmethod
    def _generate_summary_text(summary_data: Dict[str, Any], target_date) -> str:
        """Generate plain text email body for daily summary"""
        
        text_body = f"""
DAILY ALERT SUMMARY
{target_date.strftime('%A, %B %d, %Y')}
{'=' * 50}

OVERVIEW:
- Total Alerts: {summary_data['total_alerts']}
- Resolved: {summary_data['resolved_count']}
- Resolution Rate: {summary_data['resolution_rate']:.1f}%
- Critical Unresolved: {len(summary_data['critical_unresolved'])}

ALERTS BY SEVERITY:
"""
        
        for severity, count in summary_data["severity_counts"].items():
            text_body += f"- {severity.title()}: {count}\n"
        
        text_body += "\nALERTS BY TYPE:\n"
        for alert_type, count in summary_data["type_counts"].items():
            text_body += f"- {alert_type.replace('_', ' ').title()}: {count}\n"
        
        if summary_data["critical_unresolved"]:
            text_body += "\nCRITICAL UNRESOLVED ALERTS:\n"
            for alert in summary_data["critical_unresolved"]:
                text_body += f"- {alert['title']} (Email: {alert['email_id']}, Time: {alert['triggered_at'].strftime('%H:%M')})\n"
        else:
            text_body += "\n✅ No critical unresolved alerts\n"
        
        text_body += f"""

---
Support Quality Intelligence System - Alert Summary
Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
        
        return text_body

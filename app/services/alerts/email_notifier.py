"""
Email Notification Service for Alerts
Handles sending email notifications for various alert types.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Any

from app.config import settings
from app.db.models import Alert

logger = logging.getLogger(__name__)

class EmailNotifier:
    """Email notification service for alerts"""
    
    # Admin email addresses for different alert severities
    NOTIFICATION_RECIPIENTS = {
        "critical": [
            "admin@company.com",
            "support-manager@company.com"
        ],
        "warning": [
            "admin@company.com"
        ],
        "info": [
            "admin@company.com"
        ]
    }
    
    @staticmethod
    async def send_alert_email(alert: Alert) -> bool:
        """
        Send email notification for an alert.
        
        Args:
            alert: Alert object to send notification for
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Get recipients based on severity
            recipients = EmailNotifier.NOTIFICATION_RECIPIENTS.get(alert.severity, ["admin@company.com"])
            
            # Generate email content
            subject = EmailNotifier._generate_email_subject(alert)
            html_body = EmailNotifier._generate_html_body(alert)
            text_body = EmailNotifier._generate_text_body(alert)
            
            # Send email
            success = await EmailNotifier._send_email(
                recipients=recipients,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
            if success:
                logger.info(f"Alert email sent successfully for alert {alert.id}")
            else:
                logger.error(f"Failed to send alert email for alert {alert.id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending alert email for alert {alert.id}: {e}")
            return False
    
    @staticmethod
    def _generate_email_subject(alert: Alert) -> str:
        """Generate email subject for alert"""
        severity_emoji = {
            "critical": "🔴",
            "warning": "⚠️",
            "info": "ℹ️"
        }
        
        emoji = severity_emoji.get(alert.severity, "🚨")
        return f"{emoji} Support Alert: {alert.title}"
    
    @staticmethod
    def _generate_html_body(alert: Alert) -> str:
        """Generate HTML email body for alert"""
        
        # Color scheme based on severity
        color_scheme = {
            "critical": {"bg": "#fee2e2", "border": "#dc2626", "text": "#991b1b"},
            "warning": {"bg": "#fef3c7", "border": "#d97706", "text": "#92400e"},
            "info": {"bg": "#dbeafe", "border": "#2563eb", "text": "#1d4ed8"}
        }
        
        colors = color_scheme.get(alert.severity, color_scheme["info"])
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Support Quality Alert</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f9fafb; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }}
                .header {{ background-color: {colors['border']}; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px; }}
                .alert-box {{ background-color: {colors['bg']}; border-left: 4px solid {colors['border']}; padding: 15px; margin: 20px 0; border-radius: 4px; }}
                .alert-title {{ color: {colors['text']}; font-weight: bold; font-size: 18px; margin-bottom: 10px; }}
                .alert-description {{ color: {colors['text']}; line-height: 1.6; }}
                .details-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .details-table th, .details-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
                .details-table th {{ background-color: #f9fafb; font-weight: bold; }}
                .footer {{ background-color: #f9fafb; padding: 20px; text-align: center; color: #6b7280; font-size: 14px; }}
                .action-button {{ display: inline-block; background-color: {colors['border']}; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 Support Quality Alert</h1>
                    <p>Immediate attention required for support quality issue</p>
                </div>
                
                <div class="content">
                    <div class="alert-box">
                        <div class="alert-title">{alert.title}</div>
                        <div class="alert-description">{alert.description}</div>
                    </div>
                    
                    <table class="details-table">
                        <tr>
                            <th>Alert Type</th>
                            <td>{alert.alert_type.replace('_', ' ').title()}</td>
                        </tr>
                        <tr>
                            <th>Severity</th>
                            <td>{alert.severity.title()}</td>
                        </tr>
                        <tr>
                            <th>Email ID</th>
                            <td>{alert.email_id}</td>
                        </tr>
                        <tr>
                            <th>Triggered At</th>
                            <td>{alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                        </tr>
                        {f'<tr><th>Priority Level</th><td>{alert.priority_level.title()}</td></tr>' if alert.priority_level else ''}
                        {f'<tr><th>Current Value</th><td>{alert.current_value:.2f}</td></tr>' if alert.current_value else ''}
                        {f'<tr><th>Threshold</th><td>{alert.threshold_value:.2f}</td></tr>' if alert.threshold_value else ''}
                    </table>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="http://localhost:3000/alerts" class="action-button">View Alert Dashboard</a>
                    </div>
                    
                    <div style="background-color: #f9fafb; padding: 15px; border-radius: 4px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #374151;">Recommended Actions:</h3>
                        {EmailNotifier._get_recommended_actions(alert)}
                    </div>
                </div>
                
                <div class="footer">
                    <p>This is an automated alert from the Support Quality Intelligence System.</p>
                    <p>Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_template
    
    @staticmethod
    def _generate_text_body(alert: Alert) -> str:
        """Generate plain text email body for alert"""
        
        text_body = f"""
SUPPORT QUALITY ALERT
{'=' * 50}

ALERT: {alert.title}
SEVERITY: {alert.severity.upper()}

DESCRIPTION:
{alert.description}

DETAILS:
- Alert Type: {alert.alert_type.replace('_', ' ').title()}
- Email ID: {alert.email_id}
- Triggered At: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
        
        if alert.priority_level:
            text_body += f"- Priority Level: {alert.priority_level.title()}\n"
        
        if alert.current_value is not None:
            text_body += f"- Current Value: {alert.current_value:.2f}\n"
        
        if alert.threshold_value is not None:
            text_body += f"- Threshold: {alert.threshold_value:.2f}\n"
        
        text_body += f"""

RECOMMENDED ACTIONS:
{EmailNotifier._get_recommended_actions_text(alert)}

---
This is an automated alert from the Support Quality Intelligence System.
Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

View Alert Dashboard: http://localhost:3000/alerts
"""
        
        return text_body
    
    @staticmethod
    def _get_recommended_actions(alert: Alert) -> str:
        """Get HTML formatted recommended actions for alert type"""
        actions = {
            "sla_breach": """
                <ul>
                    <li>Immediately review and respond to the overdue query</li>
                    <li>Check agent workload and availability</li>
                    <li>Consider escalating to senior support staff</li>
                    <li>Review SLA policies if breaches are frequent</li>
                </ul>
            """,
            "aging_query": """
                <ul>
                    <li>Prioritize response to the aging query</li>
                    <li>Check if query requires specialized knowledge</li>
                    <li>Ensure proper query routing and assignment</li>
                    <li>Follow up with customer about delay</li>
                </ul>
            """,
            "factual_error": """
                <ul>
                    <li><strong>URGENT:</strong> Review and correct the response immediately</li>
                    <li>Send corrected information to the customer</li>
                    <li>Update knowledge base if needed</li>
                    <li>Provide additional training to the agent</li>
                </ul>
            """,
            "negative_sentiment": """
                <ul>
                    <li>Review the response tone and content</li>
                    <li>Consider sending a follow-up with improved tone</li>
                    <li>Provide communication training to the agent</li>
                    <li>Check if customer escalation is needed</li>
                </ul>
            """
        }
        
        return actions.get(alert.alert_type, "<ul><li>Review the alert details and take appropriate action</li></ul>")
    
    @staticmethod
    def _get_recommended_actions_text(alert: Alert) -> str:
        """Get plain text recommended actions for alert type"""
        actions = {
            "sla_breach": """
- Immediately review and respond to the overdue query
- Check agent workload and availability  
- Consider escalating to senior support staff
- Review SLA policies if breaches are frequent
            """,
            "aging_query": """
- Prioritize response to the aging query
- Check if query requires specialized knowledge
- Ensure proper query routing and assignment
- Follow up with customer about delay
            """,
            "factual_error": """
- URGENT: Review and correct the response immediately
- Send corrected information to the customer
- Update knowledge base if needed
- Provide additional training to the agent
            """,
            "negative_sentiment": """
- Review the response tone and content
- Consider sending a follow-up with improved tone
- Provide communication training to the agent
- Check if customer escalation is needed
            """
        }
        
        return actions.get(alert.alert_type, "- Review the alert details and take appropriate action")
    
    @staticmethod
    async def _send_email(recipients: List[str], subject: str, html_body: str, text_body: str) -> bool:
        """
        Send email using SMTP.
        
        Args:
            recipients: List of email addresses
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            # Email configuration (you can move these to settings)
            smtp_server = getattr(settings, 'SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = getattr(settings, 'SMTP_PORT', 587)
            smtp_username = getattr(settings, 'SMTP_USERNAME', 'your-email@gmail.com')
            smtp_password = getattr(settings, 'SMTP_PASSWORD', 'your-app-password')
            sender_email = getattr(settings, 'SENDER_EMAIL', smtp_username)
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = ', '.join(recipients)
            
            # Attach text and HTML parts
            text_part = MIMEText(text_body, 'plain')
            html_part = MIMEText(html_body, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {recipients}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipients}: {e}")
            return False

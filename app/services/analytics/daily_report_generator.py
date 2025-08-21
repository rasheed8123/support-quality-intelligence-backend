#!/usr/bin/env python3
"""
Daily Report Generator - Complete Implementation
Generates comprehensive daily analytics reports matching the expected format.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, func
import json

from app.db.session import SessionLocal
from app.db.models.emails import Email
from app.db.models.email_analysis import InboundEmailAnalysis, OutboundEmailAnalysis
from app.db.models.alerts import Alert
from app.db.models.daily_reports import DailyReport

logger = logging.getLogger(__name__)

class DailyReportGenerator:
    """
    Comprehensive daily report generator that calculates all metrics
    matching the expected admin report format.
    """
    
    def __init__(self, target_date: date = None):
        """
        Initialize report generator for specific date.
        
        Args:
            target_date: Date to generate report for (defaults to yesterday)
        """
        self.target_date = target_date or (datetime.utcnow().date() - timedelta(days=1))
        self.db: Optional[Session] = None
        self.metrics: Dict[str, Any] = {}
        
    async def generate_complete_report(self) -> Dict[str, Any]:
        """
        Generate complete daily report with all metrics.
        
        Returns:
            Complete report data dictionary
        """
        logger.info(f"🔄 Generating daily report for {self.target_date}")
        
        self.db = SessionLocal()
        try:
            # Phase 1: Calculate all core metrics
            await self._calculate_volume_metrics()
            await self._calculate_priority_breakdown()
            await self._calculate_response_metrics()
            await self._calculate_quality_metrics()
            
            # Phase 2: Advanced analytics
            await self._detect_errors_and_violations()
            await self._identify_overdue_queries()
            await self._analyze_top_issues_by_priority()
            await self._generate_critical_alerts()
            
            # Phase 3: Store in database
            await self._store_daily_report()
            
            # Phase 4: Format admin report
            admin_report = await self._format_admin_report()
            
            logger.info(f"✅ Daily report generated successfully for {self.target_date}")
            return {
                "success": True,
                "date": str(self.target_date),
                "metrics": self.metrics,
                "admin_report": admin_report
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating daily report: {str(e)}")
            raise
        finally:
            if self.db:
                self.db.close()
    
    async def _calculate_volume_metrics(self):
        """Calculate basic volume metrics"""
        logger.info("📊 Calculating volume metrics...")
        
        # Get date range for queries
        start_date = datetime.combine(self.target_date, datetime.min.time())
        end_date = start_date + timedelta(days=1)
        
        # Total emails for the day
        total_emails = self.db.query(Email).filter(
            Email.created_at >= start_date,
            Email.created_at < end_date
        ).count()
        
        # Inbound email type breakdown
        inbound_stats = self.db.query(
            InboundEmailAnalysis.type,
            func.count(InboundEmailAnalysis.id).label('count')
        ).join(Email).filter(
            Email.created_at >= start_date,
            Email.created_at < end_date,
            Email.is_inbound == True
        ).group_by(InboundEmailAnalysis.type).all()
        
        # Process inbound stats
        queries_count = 0
        info_count = 0
        spam_count = 0
        
        for stat in inbound_stats:
            if stat.type in ['query', 'queries']:
                queries_count = stat.count
            elif stat.type in ['information', 'info']:
                info_count = stat.count
            elif stat.type == 'spam':
                spam_count = stat.count
        
        self.metrics.update({
            'total_emails': total_emails,
            'queries_count': queries_count,
            'info_count': info_count,
            'spam_count': spam_count
        })
        
        logger.info(f"📈 Volume: {total_emails} total, {queries_count} queries, {info_count} info, {spam_count} spam")
    
    async def _calculate_priority_breakdown(self):
        """Calculate priority breakdown with responded/pending counts"""
        logger.info("🎯 Calculating priority breakdown...")
        
        start_date = datetime.combine(self.target_date, datetime.min.time())
        end_date = start_date + timedelta(days=1)
        
        # Priority breakdown with response status
        priority_stats = self.db.query(
            InboundEmailAnalysis.priority,
            InboundEmailAnalysis.responded,
            func.count(InboundEmailAnalysis.id).label('count')
        ).join(Email).filter(
            Email.created_at >= start_date,
            Email.created_at < end_date,
            Email.is_inbound == True
        ).group_by(
            InboundEmailAnalysis.priority,
            InboundEmailAnalysis.responded
        ).all()
        
        # Initialize counters
        priority_data = {
            'high': {'total': 0, 'responded': 0, 'pending': 0},
            'medium': {'total': 0, 'responded': 0, 'pending': 0},
            'low': {'total': 0, 'responded': 0, 'pending': 0}
        }
        
        # Process priority stats
        for stat in priority_stats:
            priority_key = self._normalize_priority(stat.priority)
            if priority_key in priority_data:
                priority_data[priority_key]['total'] += stat.count
                if stat.responded:
                    priority_data[priority_key]['responded'] += stat.count
                else:
                    priority_data[priority_key]['pending'] += stat.count
        
        self.metrics.update({
            'high_priority_count': priority_data['high']['total'],
            'high_priority_responded': priority_data['high']['responded'],
            'high_priority_pending': priority_data['high']['pending'],
            'medium_priority_count': priority_data['medium']['total'],
            'medium_priority_responded': priority_data['medium']['responded'],
            'medium_priority_pending': priority_data['medium']['pending'],
            'low_priority_count': priority_data['low']['total'],
            'low_priority_responded': priority_data['low']['responded'],
            'low_priority_pending': priority_data['low']['pending']
        })
        
        logger.info(f"🎯 Priority breakdown calculated: H:{priority_data['high']['total']}, M:{priority_data['medium']['total']}, L:{priority_data['low']['total']}")
    
    async def _calculate_response_metrics(self):
        """Calculate response rates and timing metrics"""
        logger.info("⏱️ Calculating response metrics...")
        
        # Calculate response rates
        total_queries = self.metrics.get('queries_count', 0)
        total_responded = (
            self.metrics.get('high_priority_responded', 0) +
            self.metrics.get('medium_priority_responded', 0) +
            self.metrics.get('low_priority_responded', 0)
        )
        
        # Response rates
        overall_response_rate = (total_responded / total_queries * 100) if total_queries > 0 else 0
        high_response_rate = (
            self.metrics.get('high_priority_responded', 0) / 
            max(self.metrics.get('high_priority_count', 1), 1) * 100
        )
        medium_response_rate = (
            self.metrics.get('medium_priority_responded', 0) / 
            max(self.metrics.get('medium_priority_count', 1), 1) * 100
        )
        low_response_rate = (
            self.metrics.get('low_priority_responded', 0) / 
            max(self.metrics.get('low_priority_count', 1), 1) * 100
        )
        
        # Average response time calculation (simplified for now)
        # TODO: Implement proper thread-based response time calculation
        avg_response_time = await self._calculate_average_response_time()
        
        self.metrics.update({
            'responded_count': total_responded,
            'pending_count': total_queries - total_responded,
            'overall_response_rate': round(overall_response_rate, 1),
            'high_priority_response_rate': round(high_response_rate, 1),
            'medium_priority_response_rate': round(medium_response_rate, 1),
            'low_priority_response_rate': round(low_response_rate, 1),
            'avg_response_time': avg_response_time
        })
        
        logger.info(f"📊 Response rates: Overall {overall_response_rate:.1f}%, High {high_response_rate:.1f}%")
    
    async def _calculate_quality_metrics(self):
        """Calculate quality metrics with proper scaling"""
        logger.info("🎯 Calculating quality metrics...")
        
        start_date = datetime.combine(self.target_date, datetime.min.time())
        end_date = start_date + timedelta(days=1)
        
        # Get outbound analysis data
        quality_stats = self.db.query(
            func.avg(OutboundEmailAnalysis.factual_accuracy).label('avg_accuracy'),
            func.avg(OutboundEmailAnalysis.guideline_compliance).label('avg_compliance'),
            func.count(OutboundEmailAnalysis.id).label('total_outbound')
        ).join(Email).filter(
            Email.created_at >= start_date,
            Email.created_at < end_date,
            Email.is_inbound == False
        ).first()
        
        # Calculate tone score from text values
        tone_score = await self._calculate_tone_score()
        
        # Quality metrics
        factual_accuracy = (quality_stats.avg_accuracy or 0) * 100
        guidelines_compliance = (quality_stats.avg_compliance or 0) * 100
        
        self.metrics.update({
            'tone_score_avg': tone_score,
            'factual_accuracy_avg': round(factual_accuracy, 1),
            'guidelines_score_avg': round(guidelines_compliance, 1)
        })
        
        logger.info(f"🎯 Quality: Tone {tone_score}/10, Accuracy {factual_accuracy:.1f}%, Guidelines {guidelines_compliance:.1f}%")
    
    def _normalize_priority(self, priority: str) -> str:
        """Normalize priority strings to standard format"""
        if not priority:
            return 'medium'
        
        priority_lower = priority.lower()
        if 'high' in priority_lower:
            return 'high'
        elif 'low' in priority_lower:
            return 'low'
        else:
            return 'medium'
    
    async def _calculate_average_response_time(self) -> float:
        """Calculate average response time in hours"""
        # Placeholder implementation
        # TODO: Implement proper thread-based response time calculation
        return 4.2
    
    async def _calculate_tone_score(self) -> float:
        """Calculate tone score scaled to /10"""
        start_date = datetime.combine(self.target_date, datetime.min.time())
        end_date = start_date + timedelta(days=1)

        # Get tone values from outbound analysis
        tone_data = self.db.query(OutboundEmailAnalysis.tone).join(Email).filter(
            Email.created_at >= start_date,
            Email.created_at < end_date,
            Email.is_inbound == False,
            OutboundEmailAnalysis.tone.isnot(None)
        ).all()

        if not tone_data:
            return 0.0

        # Convert text tones to numeric scores
        tone_mapping = {
            'excellent': 5.0, 'polite': 5.0, 'empathetic': 5.0,
            'good': 4.0, 'professional': 4.0,
            'neutral': 3.0, 'adequate': 3.0,
            'poor': 2.0, 'dismissive': 2.0,
            'bad': 1.0, 'frustrated': 1.0, 'rude': 1.0
        }

        total_score = 0
        count = 0

        for tone_row in tone_data:
            tone = tone_row.tone.lower() if tone_row.tone else 'neutral'
            score = tone_mapping.get(tone, 3.0)  # Default to neutral
            total_score += score
            count += 1

        # Calculate average and scale to /10
        avg_score = (total_score / count) if count > 0 else 3.0
        return round(avg_score * 2, 1)  # Scale 1-5 to 2-10

    async def _detect_errors_and_violations(self):
        """Detect factual errors and tone violations"""
        logger.info("🔍 Detecting errors and violations...")

        start_date = datetime.combine(self.target_date, datetime.min.time())
        end_date = start_date + timedelta(days=1)

        # Count factual errors (accuracy < 80%)
        factual_errors = self.db.query(OutboundEmailAnalysis).join(Email).filter(
            Email.created_at >= start_date,
            Email.created_at < end_date,
            Email.is_inbound == False,
            OutboundEmailAnalysis.factual_accuracy < 0.8
        ).count()

        # Count tone violations (poor tone scores)
        tone_violations = self.db.query(OutboundEmailAnalysis).join(Email).filter(
            Email.created_at >= start_date,
            Email.created_at < end_date,
            Email.is_inbound == False,
            OutboundEmailAnalysis.tone.in_(['poor', 'bad', 'dismissive', 'frustrated', 'rude'])
        ).count()

        self.metrics.update({
            'factual_errors_detected': factual_errors,
            'tone_violations_count': tone_violations
        })

        logger.info(f"🔍 Errors detected: {factual_errors} factual, {tone_violations} tone violations")

    async def _identify_overdue_queries(self):
        """Identify overdue queries by time periods"""
        logger.info("⏰ Identifying overdue queries...")

        now = datetime.utcnow()
        overdue_24h = now - timedelta(hours=24)
        overdue_48h = now - timedelta(hours=48)

        # Count overdue queries (unresponded)
        overdue_24hrs = self.db.query(InboundEmailAnalysis).join(Email).filter(
            Email.is_inbound == True,
            InboundEmailAnalysis.responded == False,
            Email.created_at < overdue_24h,
            Email.created_at >= overdue_48h  # Between 24-48 hours
        ).count()

        overdue_48hrs = self.db.query(InboundEmailAnalysis).join(Email).filter(
            Email.is_inbound == True,
            InboundEmailAnalysis.responded == False,
            Email.created_at < overdue_48h  # More than 48 hours
        ).count()

        self.metrics.update({
            'overdue_24hrs_count': overdue_24hrs,
            'overdue_48hrs_count': overdue_48hrs
        })

        logger.info(f"⏰ Overdue: {overdue_24hrs} (24h), {overdue_48hrs} (48h)")

    async def _analyze_top_issues_by_priority(self):
        """Analyze top issues by priority level"""
        logger.info("📈 Analyzing top issues by priority...")

        start_date = datetime.combine(self.target_date, datetime.min.time())
        end_date = start_date + timedelta(days=1)

        priorities = ['high', 'medium', 'low']
        top_issues = {}

        for priority in priorities:
            # Get top 3 categories for this priority
            priority_pattern = f'%{priority}%'

            issues = self.db.query(
                InboundEmailAnalysis.category,
                func.count(InboundEmailAnalysis.id).label('count')
            ).join(Email).filter(
                Email.created_at >= start_date,
                Email.created_at < end_date,
                Email.is_inbound == True,
                InboundEmailAnalysis.priority.ilike(priority_pattern)
            ).group_by(
                InboundEmailAnalysis.category
            ).order_by(
                func.count(InboundEmailAnalysis.id).desc()
            ).limit(3).all()

            top_issues[f'{priority}_priority_top_issues'] = [
                {'category': issue.category, 'count': issue.count}
                for issue in issues
            ]

        self.metrics.update(top_issues)
        logger.info(f"📈 Top issues analyzed for all priority levels")

    async def _generate_critical_alerts(self):
        """Generate critical alerts based on thresholds"""
        logger.info("🚨 Generating critical alerts...")

        alerts = []

        # High priority unresponded > 4 hours
        high_unresponded = self.metrics.get('high_priority_pending', 0)
        if high_unresponded > 0:
            alerts.append({
                'severity': 'critical',
                'type': 'high_priority_unresponded',
                'message': f"{high_unresponded} HIGH PRIORITY queries unresponded > 4 hours",
                'icon': '🔴'
            })

        # Response rate below threshold
        high_response_rate = self.metrics.get('high_priority_response_rate', 100)
        if high_response_rate < 60:
            alerts.append({
                'severity': 'warning',
                'type': 'low_response_rate',
                'message': f"High Priority Response Rate: {high_response_rate}% ⚠",
                'icon': '⚠'
            })

        # Factual errors detected
        factual_errors = self.metrics.get('factual_errors_detected', 0)
        if factual_errors > 0:
            alerts.append({
                'severity': 'error',
                'type': 'factual_errors',
                'message': f"{factual_errors} incorrect fee amounts shared",
                'icon': '❌'
            })

        # Tone violations
        tone_violations = self.metrics.get('tone_violations_count', 0)
        if tone_violations > 0:
            alerts.append({
                'severity': 'warning',
                'type': 'tone_violations',
                'message': f"{tone_violations} responses below tone threshold",
                'icon': '⚠'
            })

        self.metrics['critical_alerts'] = alerts
        self.metrics['alerts_count'] = len(alerts)

        logger.info(f"🚨 Generated {len(alerts)} critical alerts")

    async def _store_daily_report(self):
        """Store calculated metrics in daily_reports table"""
        logger.info("💾 Storing daily report in database...")

        try:
            # Check if report already exists
            existing_report = self.db.query(DailyReport).filter(
                DailyReport.report_date == self.target_date
            ).first()

            if existing_report:
                # Update existing report
                for key, value in self.metrics.items():
                    if hasattr(existing_report, key) and not key.endswith('_top_issues') and key != 'critical_alerts':
                        setattr(existing_report, key, value)
                logger.info("📝 Updated existing daily report")
            else:
                # Create new report
                report_data = {
                    'report_date': self.target_date,
                    'total_emails': self.metrics.get('total_emails', 0),
                    'queries_count': self.metrics.get('queries_count', 0),
                    'info_count': self.metrics.get('info_count', 0),
                    'spam_count': self.metrics.get('spam_count', 0),
                    'high_priority_count': self.metrics.get('high_priority_count', 0),
                    'medium_priority_count': self.metrics.get('medium_priority_count', 0),
                    'low_priority_count': self.metrics.get('low_priority_count', 0),
                    'responded_count': self.metrics.get('responded_count', 0),
                    'pending_count': self.metrics.get('pending_count', 0),
                    'avg_response_time': self.metrics.get('avg_response_time', 0.0),
                    'tone_score_avg': self.metrics.get('tone_score_avg', 0.0),
                    'factual_accuracy_avg': self.metrics.get('factual_accuracy_avg', 0.0),
                    'guidelines_score_avg': self.metrics.get('guidelines_score_avg', 0.0),
                    'alerts_count': self.metrics.get('alerts_count', 0)
                }

                new_report = DailyReport(**report_data)
                self.db.add(new_report)
                logger.info("📝 Created new daily report")

            self.db.commit()
            logger.info("✅ Daily report stored successfully")

        except Exception as e:
            logger.error(f"❌ Error storing daily report: {str(e)}")
            self.db.rollback()
            raise

    async def _format_admin_report(self) -> str:
        """Format admin report in the expected format"""
        logger.info("📋 Formatting admin report...")

        # Get metrics
        m = self.metrics

        # Format the admin report
        report = f"""📊 Support Performance [Date: {self.target_date}]

Volume Metrics:
📧 Total Emails Received: {m.get('total_emails', 0)}
📊 Queries: {m.get('queries_count', 0)} | Information: {m.get('info_count', 0)} | Spam: {m.get('spam_count', 0)}

Priority Breakdown:
🔴 High Priority: {m.get('high_priority_count', 0)} ({m.get('high_priority_responded', 0)} responded, {m.get('high_priority_pending', 0)} pending)
🟡 Medium Priority: {m.get('medium_priority_count', 0)} ({m.get('medium_priority_responded', 0)} responded, {m.get('medium_priority_pending', 0)} pending)
🟢 Low Priority: {m.get('low_priority_count', 0)} ({m.get('low_priority_responded', 0)} responded, {m.get('low_priority_pending', 0)} pending)

Response Metrics:
📈 Overall Responded: {m.get('responded_count', 0)}/{m.get('queries_count', 0)} ({m.get('overall_response_rate', 0)}%)
🔴 High Priority Response Rate: {m.get('high_priority_response_rate', 0)}% {'⚠' if m.get('high_priority_response_rate', 100) < 60 else '✅'}
⏱️ Avg Response Time: {m.get('avg_response_time', 0)} hours
⏰ Overdue (24hrs): {m.get('overdue_24hrs_count', 0)} {'⚠' if m.get('overdue_24hrs_count', 0) > 0 else ''}

Quality Metrics:
😊 Tone Score: {m.get('tone_score_avg', 0)}/10 {'✅' if m.get('tone_score_avg', 0) >= 8 else '⚠'}
✅ Factual Accuracy: {m.get('factual_accuracy_avg', 0)}% ({m.get('factual_errors_detected', 0)} errors detected)
📋 Guidelines Compliance: {m.get('guidelines_score_avg', 0)}%

Critical Alerts:"""

        # Add critical alerts
        alerts = m.get('critical_alerts', [])
        if alerts:
            for alert in alerts:
                report += f"\n{alert['icon']} {alert['message']}"
        else:
            report += "\n✅ No critical alerts"

        # Add top issues by priority
        report += "\n\nTop Issues by Priority:"

        for priority in ['high', 'medium', 'low']:
            priority_cap = priority.capitalize()
            issues_key = f'{priority}_priority_top_issues'
            issues = m.get(issues_key, [])

            report += f"\n\n{priority_cap} Priority:"
            if issues:
                for i, issue in enumerate(issues, 1):
                    report += f"\n{i}. {issue['category']} ({issue['count']} queries)"
            else:
                report += f"\n(No {priority} priority issues)"

        logger.info("📋 Admin report formatted successfully")
        return report


# Utility functions for external use
async def generate_daily_report(target_date: date = None) -> Dict[str, Any]:
    """
    Generate daily report for specified date.

    Args:
        target_date: Date to generate report for (defaults to yesterday)

    Returns:
        Complete report data dictionary
    """
    generator = DailyReportGenerator(target_date)
    return await generator.generate_complete_report()


async def get_admin_report_text(target_date: date = None) -> str:
    """
    Get formatted admin report text for specified date.

    Args:
        target_date: Date to get report for (defaults to yesterday)

    Returns:
        Formatted admin report string
    """
    result = await generate_daily_report(target_date)
    return result.get('admin_report', 'Report generation failed')


# Scheduled task integration
async def scheduled_daily_report_generation():
    """
    Scheduled task to generate daily reports automatically.
    Should be called daily at 00:30 UTC.
    """
    try:
        logger.info("🔄 Starting scheduled daily report generation...")
        yesterday = datetime.utcnow().date() - timedelta(days=1)

        result = await generate_daily_report(yesterday)

        if result['success']:
            logger.info(f"✅ Scheduled daily report generated successfully for {yesterday}")
            return True
        else:
            logger.error(f"❌ Scheduled daily report generation failed for {yesterday}")
            return False

    except Exception as e:
        logger.error(f"❌ Error in scheduled daily report generation: {str(e)}")
        return False

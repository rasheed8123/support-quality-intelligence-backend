#!/usr/bin/env python3
"""
Monitor Test Results
Check database for email processing results and RAG verification outcomes.
"""

import sys
import os
from datetime import datetime, timedelta
from sqlalchemy import desc

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.db.models import Email, InboundEmailAnalysis, OutboundEmailAnalysis, Alert

def print_section(title):
    """Print formatted section header"""
    print(f"\n{'='*60}")
    print(f"📊 {title}")
    print('='*60)

def check_recent_emails():
    """Check recent email records"""
    print_section("RECENT EMAIL RECORDS")
    
    db = SessionLocal()
    try:
        # Get emails from last 2 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=2)
        recent_emails = db.query(Email).filter(
            Email.created_at >= cutoff_time
        ).order_by(desc(Email.created_at)).all()
        
        print(f"📧 Found {len(recent_emails)} emails in the last 2 hours:")
        
        for email in recent_emails:
            direction = "📥 INBOUND" if email.is_inbound else "📤 OUTBOUND"
            print(f"  {direction} | ID: {email.email_identifier} | Thread: {email.thread_id}")
            print(f"    Created: {email.created_at}")
            
            # Check for analysis
            if email.is_inbound and email.inbound_analysis:
                analysis = email.inbound_analysis
                print(f"    📋 Analysis: {analysis.type} | Priority: {analysis.priority} | Category: {analysis.category}")
                print(f"    📧 From: {analysis.from_email} | Responded: {analysis.responded}")
            
            elif not email.is_inbound and email.outbound_analysis:
                analysis = email.outbound_analysis
                print(f"    📋 Analysis: {analysis.type}")
                print(f"    📊 Scores: Accuracy: {analysis.factual_accuracy:.3f} | Compliance: {analysis.guideline_compliance:.3f} | Completeness: {analysis.completeness:.3f}")
                print(f"    🎭 Tone: {analysis.tone}")
            else:
                print(f"    ⚠️  No analysis found")
            
            print()
        
        return len(recent_emails)
        
    except Exception as e:
        print(f"❌ Error checking emails: {e}")
        return 0
    finally:
        db.close()

def check_inbound_classifications():
    """Check inbound email classifications"""
    print_section("INBOUND EMAIL CLASSIFICATIONS")
    
    db = SessionLocal()
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=2)
        
        # Get classification summary
        analyses = db.query(InboundEmailAnalysis).join(Email).filter(
            Email.created_at >= cutoff_time
        ).all()
        
        if not analyses:
            print("📭 No inbound analyses found")
            return
        
        # Group by type
        type_counts = {}
        priority_counts = {}
        category_counts = {}
        
        for analysis in analyses:
            type_counts[analysis.type] = type_counts.get(analysis.type, 0) + 1
            if analysis.priority:
                priority_counts[analysis.priority] = priority_counts.get(analysis.priority, 0) + 1
            if analysis.category:
                category_counts[analysis.category] = category_counts.get(analysis.category, 0) + 1
        
        print("📊 Classification Summary:")
        print(f"  Types: {type_counts}")
        print(f"  Priorities: {priority_counts}")
        print(f"  Categories: {category_counts}")
        
        # Detailed breakdown
        print("\n📋 Detailed Classifications:")
        for analysis in analyses:
            print(f"  📧 {analysis.email_id}")
            print(f"    From: {analysis.from_email}")
            print(f"    Type: {analysis.type} | Priority: {analysis.priority} | Category: {analysis.category}")
            print(f"    Responded: {analysis.responded}")
            print()
        
    except Exception as e:
        print(f"❌ Error checking classifications: {e}")
    finally:
        db.close()

def check_outbound_rag_results():
    """Check outbound RAG verification results"""
    print_section("OUTBOUND RAG VERIFICATION RESULTS")
    
    db = SessionLocal()
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=2)
        
        analyses = db.query(OutboundEmailAnalysis).join(Email).filter(
            Email.created_at >= cutoff_time
        ).all()
        
        if not analyses:
            print("📭 No outbound analyses found")
            return
        
        print(f"📊 Found {len(analyses)} outbound email analyses:")
        
        total_accuracy = 0
        total_compliance = 0
        total_completeness = 0
        
        for analysis in analyses:
            print(f"\n📧 Email ID: {analysis.email_id}")
            print(f"  📊 Quality Scores:")
            print(f"    Factual Accuracy: {analysis.factual_accuracy:.3f}")
            print(f"    Guideline Compliance: {analysis.guideline_compliance:.3f}")
            print(f"    Completeness: {analysis.completeness:.3f}")
            print(f"  🎭 Tone: {analysis.tone}")
            print(f"  📅 Created: {analysis.created_at}")
            
            total_accuracy += analysis.factual_accuracy
            total_compliance += analysis.guideline_compliance
            total_completeness += analysis.completeness
        
        # Calculate averages
        count = len(analyses)
        print(f"\n📊 AVERAGE SCORES:")
        print(f"  Factual Accuracy: {total_accuracy/count:.3f}")
        print(f"  Guideline Compliance: {total_compliance/count:.3f}")
        print(f"  Completeness: {total_completeness/count:.3f}")
        
    except Exception as e:
        print(f"❌ Error checking RAG results: {e}")
    finally:
        db.close()

def check_alerts():
    """Check recent alerts"""
    print_section("RECENT ALERTS")
    
    db = SessionLocal()
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=2)
        
        alerts = db.query(Alert).filter(
            Alert.triggered_at >= cutoff_time
        ).order_by(desc(Alert.triggered_at)).all()
        
        if not alerts:
            print("🔕 No alerts triggered in the last 2 hours")
            return
        
        print(f"🚨 Found {len(alerts)} alerts:")
        
        for alert in alerts:
            severity_icon = "🔴" if alert.severity == "critical" else "🟡" if alert.severity == "warning" else "🔵"
            print(f"\n{severity_icon} {alert.alert_type.upper()} - {alert.severity.upper()}")
            print(f"  📧 Email: {alert.email_id}")
            print(f"  📋 Title: {alert.title}")
            print(f"  📝 Description: {alert.description}")
            print(f"  📊 Current: {alert.current_value} | Threshold: {alert.threshold_value}")
            print(f"  📅 Triggered: {alert.triggered_at}")
            print(f"  ✅ Acknowledged: {alert.acknowledged_at is not None}")
            print(f"  🔒 Resolved: {alert.resolved_at is not None}")
        
    except Exception as e:
        print(f"❌ Error checking alerts: {e}")
    finally:
        db.close()

def check_test_coverage():
    """Check if all test scenarios were covered"""
    print_section("TEST COVERAGE ANALYSIS")
    
    db = SessionLocal()
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=2)
        
        # Expected scenarios
        expected_scenarios = {
            'spam': 1,
            'high_priority_query': 1,
            'medium_priority_query': 2,
            'low_priority_query': 1,
            'outbound_rag': 4
        }
        
        # Check inbound classifications
        inbound_analyses = db.query(InboundEmailAnalysis).join(Email).filter(
            Email.created_at >= cutoff_time
        ).all()
        
        # Check outbound analyses
        outbound_analyses = db.query(OutboundEmailAnalysis).join(Email).filter(
            Email.created_at >= cutoff_time
        ).all()
        
        print("📊 Test Coverage Summary:")
        print(f"  📥 Inbound emails processed: {len(inbound_analyses)}")
        print(f"  📤 Outbound emails processed: {len(outbound_analyses)}")
        
        # Check specific scenarios
        spam_count = len([a for a in inbound_analyses if a.type == 'spam'])
        high_priority_count = len([a for a in inbound_analyses if a.priority == 'high'])
        medium_priority_count = len([a for a in inbound_analyses if a.priority == 'medium'])
        low_priority_count = len([a for a in inbound_analyses if a.priority == 'low'])
        
        print(f"\n📋 Scenario Coverage:")
        print(f"  🚫 Spam emails: {spam_count}/1 {'✅' if spam_count >= 1 else '❌'}")
        print(f"  🔴 High priority: {high_priority_count}/1 {'✅' if high_priority_count >= 1 else '❌'}")
        print(f"  🟡 Medium priority: {medium_priority_count}/2 {'✅' if medium_priority_count >= 2 else '❌'}")
        print(f"  🟢 Low priority: {low_priority_count}/1 {'✅' if low_priority_count >= 1 else '❌'}")
        print(f"  📤 RAG verifications: {len(outbound_analyses)}/4 {'✅' if len(outbound_analyses) >= 4 else '❌'}")
        
        # Overall coverage
        total_expected = 17  # Total emails we should send
        total_processed = len(inbound_analyses) + len(outbound_analyses)
        coverage_percentage = (total_processed / total_expected) * 100
        
        print(f"\n🎯 Overall Coverage: {total_processed}/{total_expected} ({coverage_percentage:.1f}%)")
        
        if coverage_percentage >= 90:
            print("🎉 Excellent coverage! All major scenarios tested.")
        elif coverage_percentage >= 70:
            print("✅ Good coverage! Most scenarios tested.")
        else:
            print("⚠️ Low coverage. Consider sending more test emails.")
        
    except Exception as e:
        print(f"❌ Error checking coverage: {e}")
    finally:
        db.close()

def main():
    """Run complete monitoring"""
    print("🔍 MONITORING TEST RESULTS")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        email_count = check_recent_emails()
        
        if email_count == 0:
            print("\n⚠️ No recent emails found. Make sure:")
            print("  1. Gmail webhook is registered and working")
            print("  2. Test emails have been sent")
            print("  3. Server is processing emails correctly")
            return
        
        check_inbound_classifications()
        check_outbound_rag_results()
        check_alerts()
        check_test_coverage()
        
        print(f"\n🎉 MONITORING COMPLETED!")
        print(f"📅 Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ Monitoring failed: {e}")

if __name__ == "__main__":
    main()

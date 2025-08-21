#!/usr/bin/env python3
"""
Quick database checker to see what's stored in the tables.
"""

from app.db.session import SessionLocal
from app.db.models.emails import Email
from app.db.models.email_analysis import InboundEmailAnalysis, OutboundEmailAnalysis

def check_database():
    """Check what's in the database tables"""
    db = SessionLocal()
    try:
        print("🔍 DATABASE CONTENTS CHECK")
        print("=" * 50)
        
        # Check emails table
        emails = db.query(Email).order_by(Email.created_at.desc()).limit(5).all()
        print(f"\n📧 EMAILS TABLE ({len(emails)} recent records):")
        for email in emails:
            print(f"   - ID: {email.email_identifier}")
            print(f"     Is Inbound: {email.is_inbound}")
            print(f"     Thread ID: {email.thread_id}")
            print(f"     Created: {email.created_at}")
            print()
        
        # Check inbound analysis table
        inbound_analyses = db.query(InboundEmailAnalysis).order_by(InboundEmailAnalysis.created_at.desc()).limit(5).all()
        print(f"\n📥 INBOUND EMAIL ANALYSIS TABLE ({len(inbound_analyses)} recent records):")
        for analysis in inbound_analyses:
            print(f"   - Email ID: {analysis.email_id}")
            print(f"     From: {analysis.from_email}")
            print(f"     Type: {analysis.type}")
            print(f"     Priority: {analysis.priority}")
            print(f"     Category: {analysis.category}")
            print(f"     Responded: {analysis.responded}")
            print(f"     Created: {analysis.created_at}")
            print()
        
        # Check outbound analysis table
        outbound_analyses = db.query(OutboundEmailAnalysis).order_by(OutboundEmailAnalysis.created_at.desc()).limit(5).all()
        print(f"\n📤 OUTBOUND EMAIL ANALYSIS TABLE ({len(outbound_analyses)} recent records):")
        for analysis in outbound_analyses:
            print(f"   - Email ID: {analysis.email_id}")
            print(f"     Factual Accuracy: {analysis.factual_accuracy}")
            print(f"     Guideline Compliance: {analysis.guideline_compliance}")
            print(f"     Completeness: {analysis.completeness}")
            print(f"     Tone: {analysis.tone}")
            print(f"     Created: {analysis.created_at}")
            print()
        
        print("✅ Database check completed!")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_database()

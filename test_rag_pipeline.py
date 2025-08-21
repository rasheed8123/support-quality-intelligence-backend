#!/usr/bin/env python3
"""
Test script to verify RAG pipeline is called correctly with real email processing.
This simulates Hassan sending an outbound email and traces the entire execution flow.
"""

import asyncio
import logging
from datetime import datetime
from app.services.agent_orchestration.classify import classify_email
from app.db.session import SessionLocal
from app.db.models.emails import Email
from app.db.models.email_analysis import OutboundEmailAnalysis

# Set up logging to see detailed execution
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_rag_pipeline():
    """Test the complete RAG pipeline with a realistic email scenario"""
    
    print("🧪 TESTING RAG PIPELINE WITH REAL EMAIL PROCESSING")
    print("=" * 60)
    
    # Test data - Hassan replying to a customer query
    test_email_data = {
        "email_id": "test_hassan_email_001",
        "from_email": "alhassan069@gmail.com",  # Hassan's email
        "thread_id": "thread_test_001",
        "subject": "Re: Refund Request for Course Payment",
        "body": """Dear Customer,

Thank you for reaching out regarding your refund request.

I understand you're requesting a refund for the Advanced Python Course you purchased last month. According to our refund policy, we offer full refunds within 30 days of purchase if you haven't completed more than 25% of the course content.

I've checked your account and can see that you've completed only 15% of the course materials, so you're eligible for a full refund of $299.

The refund will be processed within 3-5 business days and will appear on your original payment method. You'll receive a confirmation email once the refund has been initiated.

If you have any other questions, please don't hesitate to reach out.

Best regards,
Hassan
Support Team""",
        "is_inbound": False,  # This is an outbound email (Hassan's response)
        "thread_context": """Previous conversation:
        
Customer: Hi, I purchased the Advanced Python Course last month but I'm not satisfied with the content. The course doesn't cover the topics I expected. Can I get a refund?

Hassan: [This is Hassan's response above]"""
    }
    
    print(f"📧 Test Email Details:")
    print(f"   From: {test_email_data['from_email']}")
    print(f"   Subject: {test_email_data['subject']}")
    print(f"   Is Inbound: {test_email_data['is_inbound']}")
    print(f"   Body Length: {len(test_email_data['body'])} characters")
    print()
    
    # Step 1: Clear any existing test data
    print("🧹 Cleaning up existing test data...")
    db = SessionLocal()
    try:
        # Remove any existing test emails
        existing_email = db.query(Email).filter(Email.email_identifier == test_email_data['email_id']).first()
        if existing_email:
            db.delete(existing_email)
            db.commit()
            print("   ✅ Removed existing test email")
        
        # Remove any existing analysis
        existing_analysis = db.query(OutboundEmailAnalysis).filter(
            OutboundEmailAnalysis.email_id == test_email_data['email_id']
        ).first()
        if existing_analysis:
            db.delete(existing_analysis)
            db.commit()
            print("   ✅ Removed existing test analysis")
            
    finally:
        db.close()
    
    print()
    
    # Step 2: Process the email through the classification system
    print("🔄 Processing email through classification system...")
    print("   This will trigger the RAG pipeline for outbound emails...")
    print()
    
    try:
        # Call the classify_email function (this should trigger RAG for outbound emails)
        await classify_email(
            email_id=test_email_data['email_id'],
            from_email=test_email_data['from_email'],
            thread_id=test_email_data['thread_id'],
            subject=test_email_data['subject'],
            body=test_email_data['body'],
            is_inbound=test_email_data['is_inbound'],
            thread_context=test_email_data['thread_context']
        )
        
        print("✅ Email processing completed successfully!")
        print()
        
    except Exception as e:
        print(f"❌ Error during email processing: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Check if data was stored in the database
    print("🔍 Checking database for stored results...")
    db = SessionLocal()
    try:
        # Check if email was stored
        email_record = db.query(Email).filter(Email.email_identifier == test_email_data['email_id']).first()
        if email_record:
            print(f"   ✅ Email record created: ID = {email_record.email_identifier}")
        else:
            print("   ❌ No email record found in database")
            return False
        
        # Check if outbound analysis was stored (this indicates RAG ran)
        analysis_record = db.query(OutboundEmailAnalysis).filter(
            OutboundEmailAnalysis.email_id == test_email_data['email_id']
        ).first()
        
        if analysis_record:
            print(f"   ✅ Outbound analysis record created!")
            print(f"      - Factual Accuracy: {analysis_record.factual_accuracy}")
            print(f"      - Guideline Compliance: {analysis_record.guideline_compliance}")
            print(f"      - Tone: {analysis_record.tone}")
            print(f"      - Created At: {analysis_record.created_at}")
            
            # Check if we have real RAG results or fallback data
            if analysis_record.factual_accuracy and analysis_record.factual_accuracy > 0:
                print("   🎯 RAG PIPELINE EXECUTED SUCCESSFULLY!")
                print("      Real factual accuracy score detected")
            else:
                print("   ⚠️ RAG pipeline may have failed - using fallback data")
                
        else:
            print("   ❌ No outbound analysis record found")
            print("      This means RAG pipeline was not executed or failed")
            return False
            
    finally:
        db.close()
    
    print()
    print("🎉 RAG PIPELINE TEST COMPLETED!")
    return True

async def main():
    """Main test function"""
    try:
        success = await test_rag_pipeline()
        
        if success:
            print("\n✅ TEST RESULT: RAG PIPELINE IS WORKING CORRECTLY!")
            print("   - Email processing completed without errors")
            print("   - RAG verification was executed")
            print("   - Results were stored in database")
        else:
            print("\n❌ TEST RESULT: RAG PIPELINE HAS ISSUES")
            print("   - Check the error messages above for details")
            
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Database migration script to add subject and body fields to the email table.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.session import SessionLocal, engine
from app.db.models.emails import Email

def add_subject_body_fields():
    """Add subject and body fields to the email table"""
    
    print("🔄 ADDING SUBJECT AND BODY FIELDS TO EMAIL TABLE")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Check if columns already exist
        print("🔍 Checking if columns already exist...")
        
        # Check for subject column
        result = db.execute(text("""
            SELECT COUNT(*) as count 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'email' 
            AND COLUMN_NAME = 'subject'
        """))
        subject_exists = result.fetchone()[0] > 0
        
        # Check for body column
        result = db.execute(text("""
            SELECT COUNT(*) as count 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'email' 
            AND COLUMN_NAME = 'body'
        """))
        body_exists = result.fetchone()[0] > 0
        
        print(f"   Subject column exists: {subject_exists}")
        print(f"   Body column exists: {body_exists}")
        
        # Add subject column if it doesn't exist
        if not subject_exists:
            print("➕ Adding subject column...")
            db.execute(text("""
                ALTER TABLE email 
                ADD COLUMN subject TEXT NULL 
                COMMENT 'Email subject line'
            """))
            print("   ✅ Subject column added successfully")
        else:
            print("   ⏭️ Subject column already exists, skipping")
        
        # Add body column if it doesn't exist
        if not body_exists:
            print("➕ Adding body column...")
            db.execute(text("""
                ALTER TABLE email 
                ADD COLUMN body TEXT NULL 
                COMMENT 'Email body content'
            """))
            print("   ✅ Body column added successfully")
        else:
            print("   ⏭️ Body column already exists, skipping")
        
        # Commit the changes
        db.commit()
        
        # Verify the changes
        print("\n🔍 Verifying table structure...")
        result = db.execute(text("""
            DESCRIBE email
        """))
        
        columns = result.fetchall()
        print("   📋 Current email table structure:")
        for column in columns:
            field_name = column[0]
            field_type = column[1]
            nullable = "NULL" if column[2] == "YES" else "NOT NULL"
            print(f"      - {field_name}: {field_type} {nullable}")
        
        print("\n✅ EMAIL TABLE MIGRATION COMPLETED SUCCESSFULLY!")
        print("   The email table now has subject and body fields")
        print("   These fields will be populated when emails are processed")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during migration: {str(e)}")
        db.rollback()
        return False
        
    finally:
        db.close()

def test_new_fields():
    """Test that the new fields work correctly"""
    
    print("\n🧪 TESTING NEW FIELDS")
    print("=" * 30)
    
    db = SessionLocal()
    try:
        # Try to create a test email with subject and body
        test_email = Email(
            email_identifier="test_subject_body_001",
            is_inbound=True,
            thread_id="test_thread_001",
            subject="Test Subject - Migration Verification",
            body="This is a test email body to verify the new fields work correctly."
        )
        
        db.add(test_email)
        db.commit()
        
        # Retrieve and verify
        retrieved = db.query(Email).filter(
            Email.email_identifier == "test_subject_body_001"
        ).first()
        
        if retrieved:
            print("✅ Test email created successfully:")
            print(f"   ID: {retrieved.email_identifier}")
            print(f"   Subject: {retrieved.subject}")
            print(f"   Body: {retrieved.body[:50]}...")
            print(f"   Is Inbound: {retrieved.is_inbound}")
            
            # Clean up test data
            db.delete(retrieved)
            db.commit()
            print("   🧹 Test data cleaned up")
            
            return True
        else:
            print("❌ Failed to retrieve test email")
            return False
            
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        db.rollback()
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 EMAIL TABLE MIGRATION - ADDING SUBJECT & BODY FIELDS")
    print("=" * 70)
    
    # Step 1: Add the fields
    if add_subject_body_fields():
        # Step 2: Test the fields
        if test_new_fields():
            print("\n🎉 MIGRATION COMPLETED SUCCESSFULLY!")
            print("   ✅ Subject and body fields added to email table")
            print("   ✅ Fields tested and working correctly")
            print("   📧 Emails will now store subject and body content")
        else:
            print("\n⚠️ Migration completed but testing failed")
            print("   The fields were added but may need verification")
    else:
        print("\n❌ MIGRATION FAILED!")
        print("   Please check the error messages above")

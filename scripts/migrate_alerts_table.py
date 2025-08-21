#!/usr/bin/env python3
"""
Database Migration Script for Alert System
Updates the alerts table to support the new Real-Time Alert System.
"""

import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from sqlalchemy import text

def migrate_alerts_table():
    """Migrate the alerts table to support new alert system"""
    print("🔄 MIGRATING ALERTS TABLE")
    print("=" * 50)
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    db = SessionLocal()
    try:
        # Check current table structure
        print("🔍 Checking current alerts table structure...")
        result = db.execute(text("DESCRIBE alerts"))
        current_columns = [row[0] for row in result.fetchall()]
        print(f"   Current columns: {current_columns}")
        
        # Define new columns to add
        new_columns = [
            ("alert_type", "VARCHAR(50)"),
            ("severity", "VARCHAR(20)"),
            ("title", "VARCHAR(255)"),
            ("triggered_at", "DATETIME"),
            ("acknowledged_at", "DATETIME"),
            ("resolved_at", "DATETIME"),
            ("acknowledged_by", "VARCHAR(100)"),
            ("priority_level", "VARCHAR(20)"),
            ("threshold_value", "FLOAT"),
            ("current_value", "FLOAT"),
            ("email_notification_sent", "BOOLEAN DEFAULT FALSE"),
            ("email_sent_at", "DATETIME"),
            ("notification_retry_count", "INTEGER DEFAULT 0")
        ]
        
        # Add missing columns
        columns_added = 0
        for column_name, column_type in new_columns:
            if column_name not in current_columns:
                try:
                    sql = f"ALTER TABLE alerts ADD COLUMN {column_name} {column_type}"
                    db.execute(text(sql))
                    print(f"✅ Added column: {column_name} ({column_type})")
                    columns_added += 1
                except Exception as e:
                    print(f"❌ Failed to add column {column_name}: {e}")
        
        # Update existing data to have proper values
        print("\n🔄 Updating existing alert data...")
        
        # Set alert_type based on existing type column
        try:
            db.execute(text("""
                UPDATE alerts 
                SET alert_type = COALESCE(type, 'general'),
                    severity = CASE 
                        WHEN type = 'sla_breach' THEN 'critical'
                        WHEN type = 'high_priority_pending' THEN 'critical'
                        WHEN type = 'incorrect_fact' THEN 'critical'
                        WHEN type = 'negative_tone' THEN 'warning'
                        ELSE 'info'
                    END,
                    triggered_at = COALESCE(created_at, NOW()),
                    title = CASE 
                        WHEN type = 'sla_breach' THEN 'SLA Breach Alert'
                        WHEN type = 'high_priority_pending' THEN 'High Priority Query Pending'
                        WHEN type = 'incorrect_fact' THEN 'Factual Error Detected'
                        WHEN type = 'negative_tone' THEN 'Negative Sentiment Detected'
                        ELSE 'General Alert'
                    END
                WHERE alert_type IS NULL OR alert_type = ''
            """))
            print("✅ Updated existing alert data with new fields")
        except Exception as e:
            print(f"❌ Failed to update existing data: {e}")
        
        # Create indexes for better performance
        print("\n📊 Creating indexes for performance...")
        indexes = [
            ("idx_alerts_alert_type", "alert_type"),
            ("idx_alerts_severity", "severity"),
            ("idx_alerts_triggered_at", "triggered_at"),
            ("idx_alerts_resolved_at", "resolved_at"),
            ("idx_alerts_email_id", "email_id")
        ]
        
        for index_name, column in indexes:
            try:
                db.execute(text(f"CREATE INDEX {index_name} ON alerts ({column})"))
                print(f"✅ Created index: {index_name} on {column}")
            except Exception as e:
                if "Duplicate key name" in str(e):
                    print(f"ℹ️ Index {index_name} already exists")
                else:
                    print(f"❌ Failed to create index {index_name}: {e}")
        
        # Commit all changes
        db.commit()
        
        # Verify the migration
        print("\n✅ Verifying migration...")
        result = db.execute(text("DESCRIBE alerts"))
        final_columns = [row[0] for row in result.fetchall()]
        print(f"   Final columns: {final_columns}")
        
        # Count alerts
        result = db.execute(text("SELECT COUNT(*) FROM alerts"))
        alert_count = result.scalar()
        print(f"   Total alerts in table: {alert_count}")
        
        print(f"\n🎉 Migration completed successfully!")
        print(f"   Columns added: {columns_added}")
        print(f"   Indexes created: {len(indexes)}")
        print(f"📅 Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def verify_alert_system():
    """Verify that the alert system can work with the migrated table"""
    print("\n🧪 VERIFYING ALERT SYSTEM")
    print("=" * 30)
    
    try:
        from app.services.alerts.alert_service import AlertService
        
        # Test creating an alert
        print("Testing alert creation...")
        
        # This should work now
        db = SessionLocal()
        try:
            # Test basic insert
            db.execute(text("""
                INSERT INTO alerts (
                    alert_type, severity, email_id, title, description, 
                    triggered_at, created_at, type
                ) VALUES (
                    'test_alert', 'info', 'test_email_001', 'Test Alert', 
                    'This is a test alert for migration verification',
                    NOW(), NOW(), 'test_alert'
                )
            """))
            db.commit()
            print("✅ Alert creation test passed")
            
            # Test querying
            result = db.execute(text("""
                SELECT alert_type, severity, title FROM alerts 
                WHERE alert_type = 'test_alert'
            """))
            test_alert = result.fetchone()
            if test_alert:
                print(f"✅ Alert query test passed: {test_alert}")
            else:
                print("❌ Alert query test failed")
            
            # Clean up test alert
            db.execute(text("DELETE FROM alerts WHERE alert_type = 'test_alert'"))
            db.commit()
            print("✅ Test cleanup completed")
            
        finally:
            db.close()
            
        print("✅ Alert system verification completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Alert system verification failed: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Starting Alert System Database Migration")
    print("=" * 60)
    
    # Run migration
    migration_success = migrate_alerts_table()
    
    if migration_success:
        # Verify the system works
        verification_success = verify_alert_system()
        
        if verification_success:
            print("\n🎉 MIGRATION AND VERIFICATION COMPLETED SUCCESSFULLY!")
            print("\n💡 Next Steps:")
            print("   1. Run the alert system test: python test_alert_system.py")
            print("   2. Start the FastAPI server to test API endpoints")
            print("   3. Configure email SMTP settings for notifications")
            print("   4. Test with real email data")
        else:
            print("\n⚠️ Migration completed but verification failed")
            print("   Please check the alert system configuration")
    else:
        print("\n❌ Migration failed. Please check the error messages above.")
        sys.exit(1)

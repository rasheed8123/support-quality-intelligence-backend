#!/usr/bin/env python3
"""
Database Table Creation Script
Creates all database tables from SQLAlchemy models.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.config import settings
from app.db.base import Base

# Import all models to register them with Base
from app.db.models.emails import Email
from app.db.models.email_analysis import InboundEmailAnalysis, OutboundEmailAnalysis
from app.db.models.alerts import Alert
from app.db.models.audit_logs import AuditLog
from app.db.models.daily_reports import DailyReport

def create_database_tables():
    """Create all database tables from SQLAlchemy models"""
    
    print("🗄️  Database Table Creation")
    print("=" * 50)
    
    # Get database URL
    database_url = settings.database_url
    print(f"📊 Database URL: {database_url.split('@')[0]}@***")
    
    try:
        # Create engine
        if "mysql" in database_url.lower():
            connect_args = {
                "charset": "utf8mb4",
                "autocommit": False,
            }
        else:
            connect_args = {"check_same_thread": False}
        
        engine = create_engine(
            database_url,
            connect_args=connect_args,
            echo=True  # Show SQL statements
        )
        
        print("🔌 Testing database connection...")
        
        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
        
        print("\n📋 Models to create:")
        for table_name in Base.metadata.tables.keys():
            print(f"   - {table_name}")
        
        print(f"\n🏗️  Creating {len(Base.metadata.tables)} tables...")

        # Drop all tables first (in case of conflicts)
        print("🗑️  Dropping existing tables if they exist...")
        Base.metadata.drop_all(bind=engine)

        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        print("✅ All tables created successfully!")
        
        # Verify tables were created
        print("\n🔍 Verifying table creation...")
        with engine.connect() as connection:
            if "mysql" in database_url.lower():
                result = connection.execute(text("SHOW TABLES"))
                tables = [row[0] for row in result]
            else:
                result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                tables = [row[0] for row in result]
            
            print(f"📊 Found {len(tables)} tables in database:")
            for table in sorted(tables):
                print(f"   ✅ {table}")
        
        print(f"\n🎉 Database initialization complete!")
        print(f"🚀 Ready to process emails!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

if __name__ == '__main__':
    success = create_database_tables()
    if not success:
        sys.exit(1)

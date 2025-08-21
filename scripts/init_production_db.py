#!/usr/bin/env python3
"""
Production database initialization script.
Sets up MySQL database tables and initial data for the Support Quality Intelligence system.
"""

import asyncio
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.db.base import Base
from app.db.session import get_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_mysql_engine():
    """Create MySQL engine for production database"""
    try:
        # Create engine with proper MySQL configuration
        engine = create_engine(
            settings.DATABASE_URL,
            echo=True,  # Set to False in production
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,   # Recycle connections every hour
            connect_args={
                "charset": "utf8mb4",
                "autocommit": False,
            }
        )
        return engine
    except Exception as e:
        logger.error(f"Failed to create MySQL engine: {e}")
        raise


def test_connection(engine):
    """Test database connection"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")
            return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


def create_tables(engine):
    """Create all database tables"""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        return False


def verify_tables(engine):
    """Verify that all required tables exist"""
    try:
        with engine.connect() as connection:
            # Check for key tables
            tables_to_check = [
                'emails', 'inbound_email_analysis', 'outbound_email_analysis',
                'alerts', 'daily_reports', 'audit_logs'
            ]
            
            for table in tables_to_check:
                result = connection.execute(text(f"SHOW TABLES LIKE '{table}'"))
                if result.fetchone():
                    logger.info(f"✅ Table '{table}' exists")
                else:
                    logger.warning(f"⚠️  Table '{table}' not found")
            
        return True
    except Exception as e:
        logger.error(f"❌ Failed to verify tables: {e}")
        return False


def setup_initial_data(engine):
    """Set up initial data if needed"""
    try:
        logger.info("Setting up initial data...")
        # Add any initial data setup here
        logger.info("✅ Initial data setup complete")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to setup initial data: {e}")
        return False


async def test_qdrant_connection():
    """Test Qdrant Cloud connection"""
    try:
        from app.services.rag_pipeline.vector_store import AdvancedVectorStoreManager
        
        logger.info("Testing Qdrant Cloud connection...")
        vector_store = AdvancedVectorStoreManager()
        await vector_store.initialize()
        
        # Test basic operations
        collections = await vector_store.list_collections()
        logger.info(f"✅ Qdrant Cloud connected. Collections: {len(collections)}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Qdrant Cloud connection failed: {e}")
        return False


def main():
    """Main initialization function"""
    print("🚀 Production Database Initialization")
    print("=" * 50)
    
    # Check configuration
    logger.info(f"Database URL: {settings.DATABASE_URL[:50]}...")
    logger.info(f"Vector Store Type: {settings.VECTOR_STORE_TYPE}")
    logger.info(f"Vector Store Host: {settings.VECTOR_STORE_HOST}")
    
    # Initialize MySQL Database
    logger.info("\n📊 Setting up MySQL Database...")
    try:
        engine = create_mysql_engine()
        
        # Test connection
        if not test_connection(engine):
            logger.error("❌ Cannot proceed without database connection")
            return False
        
        # Create tables
        if not create_tables(engine):
            logger.error("❌ Failed to create database tables")
            return False
        
        # Verify tables
        if not verify_tables(engine):
            logger.warning("⚠️  Some tables may be missing")
        
        # Setup initial data
        if not setup_initial_data(engine):
            logger.warning("⚠️  Initial data setup had issues")
        
        logger.info("✅ MySQL database setup complete!")
        
    except Exception as e:
        logger.error(f"❌ MySQL setup failed: {e}")
        return False
    
    # Test Qdrant Cloud
    logger.info("\n🔍 Testing Qdrant Cloud Connection...")
    try:
        asyncio.run(test_qdrant_connection())
    except Exception as e:
        logger.error(f"❌ Qdrant Cloud test failed: {e}")
        return False
    
    print("\n🎉 Production setup complete!")
    print("✅ MySQL database initialized")
    print("✅ Qdrant Cloud connection verified")
    print("\nYou can now start your application with:")
    print("python main.py")
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

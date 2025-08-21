#!/usr/bin/env python3
"""
Create the production database on MySQL server.
This script creates the database if it doesn't exist.
"""

import logging
from sqlalchemy import create_engine, text
from urllib.parse import urlparse, urlunparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration from .env
DB_HOST = "ls-d157091fb9608cc702c3b9a33dec25bca625f14b.cstb7bwkbg8x.ap-south-1.rds.amazonaws.com"
DB_USER = "dbmasteruser"
DB_PASSWORD = "R8AR9z^_y|AP3+jABss?GN8<!|ta4<,f"
DB_NAME = "support_quality_intelligence"


def create_database():
    """Create the database if it doesn't exist"""
    try:
        # Connect to MySQL server without specifying database
        server_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:3306/"
        
        logger.info(f"Connecting to MySQL server at {DB_HOST}...")
        engine = create_engine(
            server_url,
            echo=True,
            pool_pre_ping=True,
            connect_args={
                "charset": "utf8mb4",
                "autocommit": True,  # Enable autocommit for CREATE DATABASE
            }
        )
        
        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info("✅ Connected to MySQL server successfully")
        
        # Create database
        logger.info(f"Creating database '{DB_NAME}'...")
        with engine.connect() as connection:
            # Check if database exists
            result = connection.execute(text(f"SHOW DATABASES LIKE '{DB_NAME}'"))
            if result.fetchone():
                logger.info(f"✅ Database '{DB_NAME}' already exists")
            else:
                # Create database
                connection.execute(text(f"CREATE DATABASE `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                logger.info(f"✅ Database '{DB_NAME}' created successfully")
        
        # Test connection to the new database
        db_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:3306/{DB_NAME}"
        db_engine = create_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
            connect_args={
                "charset": "utf8mb4",
                "autocommit": False,
            }
        )
        
        with db_engine.connect() as connection:
            result = connection.execute(text("SELECT DATABASE()"))
            current_db = result.fetchone()[0]
            logger.info(f"✅ Connected to database: {current_db}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create database: {e}")
        return False


def main():
    """Main function"""
    print("🗄️  MySQL Database Creation")
    print("=" * 40)
    
    if create_database():
        print("\n🎉 Database setup complete!")
        print("✅ Database created and accessible")
        print("\nYou can now run:")
        print("python init_production_db.py")
        return True
    else:
        print("\n❌ Database setup failed!")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

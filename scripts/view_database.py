#!/usr/bin/env python3
"""
Database Viewer Script
View database tables and data directly from VS Code terminal.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.config import settings
import pandas as pd

def view_database():
    """View database tables and data"""
    
    print("🗄️  Database Viewer")
    print("=" * 50)
    
    # Get database URL
    database_url = settings.database_url
    print(f"📊 Database: {database_url.split('@')[1].split('/')[1] if '@' in database_url else 'SQLite'}")
    
    try:
        # Create engine
        if "mysql" in database_url.lower():
            connect_args = {"charset": "utf8mb4", "autocommit": False}
        else:
            connect_args = {"check_same_thread": False}
        
        engine = create_engine(database_url, connect_args=connect_args)
        
        print("🔌 Connecting to database...")
        
        with engine.connect() as connection:
            # Show all tables
            if "mysql" in database_url.lower():
                result = connection.execute(text("SHOW TABLES"))
                tables = [row[0] for row in result]
            else:
                result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                tables = [row[0] for row in result]
            
            print(f"\n📋 Found {len(tables)} tables:")
            for i, table in enumerate(sorted(tables), 1):
                print(f"   {i}. {table}")
            
            # Show data from each table
            for table in sorted(tables):
                print(f"\n📊 Table: {table}")
                print("-" * 40)
                
                try:
                    # Get row count
                    count_result = connection.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    row_count = count_result.fetchone()[0]
                    
                    if row_count == 0:
                        print("   (No data)")
                        continue
                    
                    print(f"   Rows: {row_count}")
                    
                    # Show first 5 rows
                    if row_count > 0:
                        result = connection.execute(text(f"SELECT * FROM {table} LIMIT 5"))
                        rows = result.fetchall()
                        columns = result.keys()
                        
                        if rows:
                            # Create a simple table view
                            print(f"   Columns: {', '.join(columns)}")
                            print("   Sample data:")
                            for i, row in enumerate(rows, 1):
                                row_data = dict(zip(columns, row))
                                print(f"     Row {i}: {row_data}")
                        
                except Exception as e:
                    print(f"   Error reading table: {e}")
        
        print(f"\n✅ Database view complete!")
        
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")

def view_specific_table(table_name: str, limit: int = 10):
    """View specific table data"""
    
    print(f"🔍 Viewing table: {table_name}")
    print("=" * 50)
    
    database_url = settings.database_url
    
    try:
        if "mysql" in database_url.lower():
            connect_args = {"charset": "utf8mb4", "autocommit": False}
        else:
            connect_args = {"check_same_thread": False}
        
        engine = create_engine(database_url, connect_args=connect_args)
        
        with engine.connect() as connection:
            # Get table structure
            if "mysql" in database_url.lower():
                structure_result = connection.execute(text(f"DESCRIBE {table_name}"))
                print("📋 Table Structure:")
                for row in structure_result:
                    print(f"   {row[0]} - {row[1]} ({row[2]})")
            
            # Get data
            result = connection.execute(text(f"SELECT * FROM {table_name} ORDER BY created_at DESC LIMIT {limit}"))
            rows = result.fetchall()
            columns = result.keys()
            
            print(f"\n📊 Data (showing last {min(len(rows), limit)} rows):")
            
            if rows:
                for i, row in enumerate(rows, 1):
                    print(f"\n--- Row {i} ---")
                    for col, val in zip(columns, row):
                        print(f"  {col}: {val}")
            else:
                print("   (No data)")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        table_name = sys.argv[1]
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        view_specific_table(table_name, limit)
    else:
        view_database()
        
        print(f"\n💡 To view specific table:")
        print(f"   python view_database.py email")
        print(f"   python view_database.py inbound_email_analysis 5")

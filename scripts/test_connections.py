#!/usr/bin/env python3
"""
Test script to verify MySQL and Qdrant connections.
Quick verification without running full embedding process.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.core.connections import ConnectionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_connections():
    """Test all production connections"""
    print("🔍 Testing Production Connections")
    print("=" * 40)
    
    # Initialize connection manager
    connection_manager = ConnectionManager()
    
    try:
        # Initialize connections
        print("\n🚀 Initializing connections...")
        results = await connection_manager.initialize_connections()
        
        # Display connection results
        print("\n📊 Connection Status:")
        print("-" * 25)
        
        for service, status in results.items():
            status_icon = "✅" if status else "❌"
            print(f"{status_icon} {service.title()}: {'Connected' if status else 'Failed'}")
        
        # Perform health check
        print("\n🏥 Health Check:")
        print("-" * 20)
        
        health_status = await connection_manager.health_check()
        
        for service, info in health_status.items():
            if service == "overall":
                continue
                
            status = info.get("status", "unknown")
            details = info.get("details", "")
            
            status_icon = "✅" if status == "healthy" else "❌"
            print(f"{status_icon} {service.title()}: {status}")
            if details:
                print(f"   Details: {details}")
        
        # Overall status
        overall_status = health_status.get("overall", "unknown")
        overall_icon = "✅" if overall_status == "healthy" else "⚠️"
        print(f"\n{overall_icon} Overall Status: {overall_status.upper()}")
        
        # Test vector store collections
        if results.get("vector_store", False):
            print("\n📁 Vector Store Collections:")
            print("-" * 30)
            
            try:
                vector_store = connection_manager.get_vector_store()
                collections = await vector_store.list_collections()
                
                for collection in collections:
                    print(f"📂 {collection}")
                
                print(f"\n📊 Total Collections: {len(collections)}")
                
            except Exception as e:
                print(f"❌ Failed to list collections: {e}")
        
        # Close connections
        await connection_manager.close_connections()
        
        # Summary
        all_connected = all(results.values())
        if all_connected:
            print("\n🎉 All connections successful!")
            print("✅ Ready for data embedding")
            return True
        else:
            print("\n⚠️  Some connections failed")
            print("❌ Check configuration and try again")
            return False
            
    except Exception as e:
        logger.error(f"❌ Connection test failed: {e}")
        print(f"\n❌ Connection test failed: {e}")
        return False


async def main():
    """Main test function"""
    success = await test_connections()
    
    if success:
        print("\n🚀 Next Steps:")
        print("- Run: python scripts/embed_data.py")
        print("- Or start the application: python main.py")
    else:
        print("\n🔧 Troubleshooting:")
        print("- Check .env file configuration")
        print("- Verify database and Qdrant credentials")
        print("- Check network connectivity")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)

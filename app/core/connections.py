"""
Production connection manager for MySQL and Qdrant.
Handles initialization and health checks for all external services.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager

from app.config import settings
from app.db.base import Base

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Centralized connection manager for all external services.
    Handles MySQL database and Qdrant vector store connections.
    """
    
    def __init__(self):
        self.db_engine = None
        self.db_session_factory = None
        self.vector_store = None
        self.connections_initialized = False
        
    async def initialize_connections(self) -> Dict[str, bool]:
        """
        Initialize all production connections.
        Called during application startup.
        
        Returns:
            Dict with connection status for each service
        """
        logger.info("🚀 Initializing production connections...")
        
        results = {
            "database": False,
            "vector_store": False
        }
        
        # Initialize MySQL Database
        try:
            results["database"] = await self._initialize_database()
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
        
        # Initialize Qdrant Vector Store
        try:
            results["vector_store"] = await self._initialize_vector_store()
        except Exception as e:
            logger.error(f"❌ Vector store initialization failed: {e}")
        
        self.connections_initialized = all(results.values())
        
        if self.connections_initialized:
            logger.info("✅ All production connections initialized successfully")
        else:
            logger.warning(f"⚠️  Some connections failed: {results}")
        
        return results
    
    async def _initialize_database(self) -> bool:
        """Initialize MySQL database connection"""
        logger.info("📊 Connecting to MySQL database...")
        
        try:
            # Get the appropriate database URL
            database_url = settings.database_url

            # Determine connect_args based on database type
            connect_args = {}
            if "mysql" in database_url.lower():
                connect_args = {
                    "charset": "utf8mb4",
                    "autocommit": False,
                }
            elif "sqlite" in database_url.lower():
                connect_args = {"check_same_thread": False}

            # Create SQLAlchemy engine with production settings
            self.db_engine = create_engine(
                database_url,
                echo=False,  # Set to True for SQL debugging
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=3600,   # Recycle connections every hour
                pool_size=10,        # Connection pool size
                max_overflow=20,     # Max overflow connections
                connect_args=connect_args
            )
            
            # Test connection
            with self.db_engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                logger.info("✅ MySQL database connected successfully")
            
            # Create session factory
            self.db_session_factory = sessionmaker(
                bind=self.db_engine,
                autocommit=False,
                autoflush=False
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ MySQL connection failed: {e}")
            return False
    
    async def _initialize_vector_store(self) -> bool:
        """Initialize Qdrant vector store connection"""
        logger.info("🔍 Connecting to Qdrant vector store...")
        
        try:
            # Import here to avoid circular imports
            from app.services.rag_pipeline.vector_store import AdvancedVectorStoreManager
            
            # Create vector store manager
            self.vector_store = AdvancedVectorStoreManager()
            
            # Initialize collections
            await self.vector_store.initialize()
            
            # Test connection by listing collections
            collections = await self.vector_store.list_collections()
            logger.info(f"✅ Qdrant connected with {len(collections)} collections: {collections}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Qdrant connection failed: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health checks on all connections.
        
        Returns:
            Dict with health status for each service
        """
        health_status = {
            "database": {"status": "unknown", "details": ""},
            "vector_store": {"status": "unknown", "details": ""},
            "overall": "unknown"
        }
        
        # Check database health
        try:
            if self.db_engine:
                with self.db_engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                health_status["database"] = {
                    "status": "healthy", 
                    "details": "Connection active"
                }
            else:
                health_status["database"] = {
                    "status": "unhealthy", 
                    "details": "No database connection"
                }
        except Exception as e:
            health_status["database"] = {
                "status": "unhealthy", 
                "details": str(e)
            }
        
        # Check vector store health
        try:
            if self.vector_store:
                collections = await self.vector_store.list_collections()
                health_status["vector_store"] = {
                    "status": "healthy", 
                    "details": f"{len(collections)} collections available"
                }
            else:
                health_status["vector_store"] = {
                    "status": "unhealthy", 
                    "details": "No vector store connection"
                }
        except Exception as e:
            health_status["vector_store"] = {
                "status": "unhealthy", 
                "details": str(e)
            }
        
        # Overall health
        all_healthy = all(
            service["status"] == "healthy" 
            for service in [health_status["database"], health_status["vector_store"]]
        )
        health_status["overall"] = "healthy" if all_healthy else "degraded"
        
        return health_status
    
    async def close_connections(self):
        """Close all connections gracefully"""
        logger.info("🔌 Closing production connections...")
        
        # Close vector store
        if self.vector_store:
            try:
                await self.vector_store.close()
                logger.info("✅ Vector store connection closed")
            except Exception as e:
                logger.error(f"❌ Error closing vector store: {e}")
        
        # Close database
        if self.db_engine:
            try:
                self.db_engine.dispose()
                logger.info("✅ Database connection closed")
            except Exception as e:
                logger.error(f"❌ Error closing database: {e}")
        
        self.connections_initialized = False
    
    def get_db_session(self):
        """Get database session for dependency injection"""
        if not self.db_session_factory:
            raise RuntimeError("Database not initialized. Call initialize_connections() first.")
        
        return self.db_session_factory()
    
    def get_vector_store(self):
        """Get vector store instance"""
        if not self.vector_store:
            raise RuntimeError("Vector store not initialized. Call initialize_connections() first.")
        
        return self.vector_store


# Global connection manager instance
connection_manager = ConnectionManager()


@asynccontextmanager
async def lifespan_manager(app):
    """
    FastAPI lifespan manager for handling startup and shutdown.
    This replaces the old startup/shutdown event handlers.
    """
    # Startup
    logger.info("🚀 Application starting up...")
    await connection_manager.initialize_connections()

    # Start daily report scheduler (temporarily disabled)
    # try:
    #     from app.services.scheduler.daily_scheduler import start_daily_scheduler
    #     await start_daily_scheduler()
    #     logger.info("📅 Daily report scheduler started successfully")
    # except Exception as e:
    #     logger.error(f"❌ Failed to start daily scheduler: {str(e)}")
    #     # Don't fail startup if scheduler fails

    yield

    # Shutdown
    logger.info("🛑 Application shutting down...")

    # Stop daily report scheduler (temporarily disabled)
    # try:
    #     from app.services.scheduler.daily_scheduler import stop_daily_scheduler
    #     await stop_daily_scheduler()
    #     logger.info("📅 Daily report scheduler stopped successfully")
    # except Exception as e:
    #     logger.error(f"❌ Failed to stop daily scheduler: {str(e)}")

    await connection_manager.close_connections()


# Dependency injection functions
async def get_database():
    """Dependency for getting database session"""
    session = connection_manager.get_db_session()
    try:
        yield session
    finally:
        session.close()


async def get_vector_store():
    """Dependency for getting vector store"""
    return connection_manager.get_vector_store()

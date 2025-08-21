from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time
import logging

from app.config import settings
from app.core.connections import lifespan_manager, connection_manager
from app.webhook.router import router as webhook_router
from app.api.endpoints import verification_router, health_router

# Import existing route modules
from app.routes import classification, email, reports, dashboard

# Import alert system
from app.api.alert_routes import router as alert_router
from app.services.alerts.alert_scheduler import alert_scheduler

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI application with comprehensive configuration and lifespan management
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan_manager  # Handle startup/shutdown connections
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to all responses"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "path": str(request.url.path)
        }
    )

# Include all routers
# RAG System routers
app.include_router(health_router)
app.include_router(verification_router)
app.include_router(webhook_router)

# Existing application routers
app.include_router(classification.router)
app.include_router(email.router)
app.include_router(reports.router)
app.include_router(dashboard.router)

# Alert system router
app.include_router(alert_router)

# Simple health endpoint for basic checks
@app.get("/health", tags=["Health"])
async def simple_health():
    """Simple health check endpoint"""
    return {"ok": True}

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.API_TITLE,
        "version": settings.API_VERSION,
        "description": settings.API_DESCRIPTION,
        "docs_url": "/docs",
        "health_check": "/health",
        "detailed_health": "/health/",
        "connections": {
            "database": "MySQL (AWS RDS)",
            "vector_store": "Qdrant Cloud",
            "status": "Production Ready"
        },
        "endpoints": {
            "rag_verification": "/api/v1/verify-support-response",
            "classification": "/classification",
            "email": "/email",
            "webhooks": "/webhook",
            "reports": "/reports"
        }
    }

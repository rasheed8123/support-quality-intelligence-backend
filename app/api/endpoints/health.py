"""
Health check endpoints for monitoring system status.
Provides comprehensive health information for the RAG pipeline.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any
import time
import psutil
import os
from datetime import datetime

from app.config import settings

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: str
    version: str
    uptime_seconds: float
    system_info: Dict[str, Any]
    services: Dict[str, str]


class DetailedHealthResponse(BaseModel):
    """Detailed health check response"""
    status: str
    timestamp: str
    version: str
    uptime_seconds: float
    system_info: Dict[str, Any]
    services: Dict[str, str]
    configuration: Dict[str, Any]
    performance_metrics: Dict[str, Any]


# Track application start time
_start_time = time.time()


@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        HealthResponse: Basic system health information
    """
    current_time = time.time()
    uptime = current_time - _start_time
    
    # Check system resources
    memory_info = psutil.virtual_memory()
    disk_info = psutil.disk_usage('/')
    
    system_info = {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": memory_info.percent,
        "memory_available_gb": round(memory_info.available / (1024**3), 2),
        "disk_percent": disk_info.percent,
        "disk_free_gb": round(disk_info.free / (1024**3), 2)
    }
    
    # Check service status
    services = {
        "api": "healthy",
        "openai": await _check_openai_connection(),
        "vector_store": await _check_vector_store_connection(),
        "google_drive": await _check_google_drive_connection()
    }
    
    # Determine overall status
    overall_status = "healthy" if all(status == "healthy" for status in services.values()) else "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        version=settings.API_VERSION,
        uptime_seconds=round(uptime, 2),
        system_info=system_info,
        services=services
    )


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """
    Detailed health check with comprehensive system information.
    
    Returns:
        DetailedHealthResponse: Comprehensive system health and configuration
    """
    basic_health = await health_check()
    
    # Additional configuration info (non-sensitive)
    configuration = {
        "api_version": settings.API_VERSION,
        "embedding_model": settings.EMBEDDING_MODEL,
        "vector_store_type": settings.VECTOR_STORE_TYPE,
        "max_concurrent_requests": settings.MAX_CONCURRENT_REQUESTS,
        "request_timeout_seconds": settings.REQUEST_TIMEOUT_SECONDS,
        "caching_enabled": settings.ENABLE_RESPONSE_CACHING,
        "metrics_enabled": settings.ENABLE_METRICS
    }
    
    # Performance metrics
    performance_metrics = {
        "process_id": os.getpid(),
        "thread_count": psutil.Process().num_threads(),
        "open_files": len(psutil.Process().open_files()),
        "connections": len(psutil.Process().connections()),
        "cpu_times": psutil.Process().cpu_times()._asdict()
    }
    
    return DetailedHealthResponse(
        status=basic_health.status,
        timestamp=basic_health.timestamp,
        version=basic_health.version,
        uptime_seconds=basic_health.uptime_seconds,
        system_info=basic_health.system_info,
        services=basic_health.services,
        configuration=configuration,
        performance_metrics=performance_metrics
    )


async def _check_openai_connection() -> str:
    """Check OpenAI API connectivity"""
    try:
        if not settings.OPENAI_API_KEY:
            return "not_configured"
        
        # TODO: Implement actual OpenAI connection check
        # For now, just check if API key is configured
        return "healthy"
    except Exception:
        return "unhealthy"


async def _check_vector_store_connection() -> str:
    """Check vector store connectivity"""
    try:
        # TODO: Implement actual vector store connection check
        # For now, return healthy if configuration exists
        if settings.VECTOR_STORE_TYPE and settings.VECTOR_STORE_HOST:
            return "healthy"
        return "not_configured"
    except Exception:
        return "unhealthy"


async def _check_google_drive_connection() -> str:
    """Check Google Drive API connectivity"""
    try:
        # TODO: Implement actual Google Drive connection check
        # For now, check if service account is configured
        if settings.GOOGLE_SERVICE_ACCOUNT_PROJECT_ID:
            return "healthy"
        return "not_configured"
    except Exception:
        return "unhealthy"


@router.get("/ready")
async def readiness_check():
    """
    Kubernetes-style readiness check.
    
    Returns:
        dict: Simple ready/not ready status
    """
    health = await health_check()
    
    # Consider ready if all critical services are healthy
    critical_services = ["api", "openai"]
    ready = all(health.services.get(service) == "healthy" for service in critical_services)
    
    return {
        "ready": ready,
        "timestamp": health.timestamp
    }


@router.get("/live")
async def liveness_check():
    """
    Kubernetes-style liveness check.
    
    Returns:
        dict: Simple alive status
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat()
    }

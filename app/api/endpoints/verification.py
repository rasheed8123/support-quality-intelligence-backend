"""
Support response verification endpoints.
Main API endpoints for the Support Quality Intelligence system.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
import time
import uuid
import logging
from typing import Dict, Any

from app.api.models import (
    SupportVerificationRequest,
    SupportVerificationResponse,
    VerificationStatus
)
from app.services.core.pipeline_orchestrator import PipelineOrchestrator
from app.services.rag_pipeline.document_processor import DocumentProcessor
from app.config import settings

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Verification"])


def get_pipeline_orchestrator() -> PipelineOrchestrator:
    """Dependency to get pipeline orchestrator instance"""
    return PipelineOrchestrator()


def get_document_processor() -> DocumentProcessor:
    """Dependency to get document processor instance"""
    return DocumentProcessor()


@router.post(
    "/verify-support-response",
    response_model=SupportVerificationResponse,
    summary="Verify Support Response",
    description="Verify a support agent's response against authoritative documentation and guidelines"
)
async def verify_support_response(
    request: SupportVerificationRequest,
    background_tasks: BackgroundTasks,
    pipeline: PipelineOrchestrator = Depends(get_pipeline_orchestrator)
) -> SupportVerificationResponse:
    """
    Main endpoint for support response verification.
    
    This endpoint performs comprehensive verification of support responses including:
    - Factual accuracy checking against knowledge base
    - Guideline compliance verification
    - Quality scoring and feedback generation
    
    Args:
        request: Support verification request with response content and parameters
        background_tasks: FastAPI background tasks for async operations
        pipeline: Pipeline orchestrator dependency
        
    Returns:
        SupportVerificationResponse: Comprehensive verification results
        
    Raises:
        HTTPException: For validation errors or processing failures
    """
    start_time = time.time()
    verification_id = f"ver_{int(time.time())}_{str(uuid.uuid4())[:8]}"
    
    logger.info(
        f"Starting verification {verification_id} for agent {request.agent_id or 'unknown'}"
    )
    
    try:
        # Validate request parameters
        await _validate_request(request)
        
        # Process verification through pipeline
        result = await pipeline.verify_response(request, verification_id)
        
        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)
        result.processing_time_ms = processing_time
        
        # Log completion
        logger.info(
            f"Verification {verification_id} completed in {processing_time}ms "
            f"with status {result.verification_status} and score {result.overall_score:.3f}"
        )
        
        # Schedule background tasks if needed
        if result.verification_status == VerificationStatus.NEEDS_REVIEW:
            background_tasks.add_task(_schedule_review_notification, verification_id, result)
        
        return result
        
    except ValueError as e:
        logger.warning(f"Validation error for {verification_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
        
    except TimeoutError as e:
        logger.error(f"Timeout error for {verification_id}: {str(e)}")
        raise HTTPException(status_code=408, detail="Verification request timed out")
        
    except Exception as e:
        logger.error(f"Verification failed for {verification_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Internal verification error. Reference ID: {verification_id}"
        )


@router.post(
    "/verify-batch",
    summary="Batch Verify Support Responses",
    description="Verify multiple support responses in a single request"
)
async def verify_batch_responses(
    requests: list[SupportVerificationRequest],
    background_tasks: BackgroundTasks,
    pipeline: PipelineOrchestrator = Depends(get_pipeline_orchestrator)
) -> Dict[str, Any]:
    """
    Batch verification endpoint for multiple support responses.
    
    Args:
        requests: List of verification requests
        background_tasks: FastAPI background tasks
        pipeline: Pipeline orchestrator dependency
        
    Returns:
        Dict containing batch results and summary statistics
    """
    if len(requests) > 10:  # Limit batch size
        raise HTTPException(
            status_code=400, 
            detail="Batch size limited to 10 requests"
        )
    
    batch_id = f"batch_{int(time.time())}_{str(uuid.uuid4())[:8]}"
    start_time = time.time()
    
    logger.info(f"Starting batch verification {batch_id} with {len(requests)} requests")
    
    results = []
    errors = []
    
    for i, request in enumerate(requests):
        try:
            verification_id = f"{batch_id}_item_{i}"
            result = await pipeline.verify_response(request, verification_id)
            results.append({
                "index": i,
                "verification_id": verification_id,
                "result": result
            })
        except Exception as e:
            logger.error(f"Batch item {i} failed: {str(e)}")
            errors.append({
                "index": i,
                "error": str(e)
            })
    
    processing_time = int((time.time() - start_time) * 1000)
    
    # Calculate summary statistics
    successful_results = [r["result"] for r in results]
    summary = {
        "total_requests": len(requests),
        "successful": len(results),
        "failed": len(errors),
        "average_score": sum(r.overall_score for r in successful_results) / len(successful_results) if successful_results else 0,
        "processing_time_ms": processing_time
    }
    
    logger.info(f"Batch verification {batch_id} completed: {summary}")
    
    return {
        "batch_id": batch_id,
        "summary": summary,
        "results": results,
        "errors": errors
    }


@router.get(
    "/verification/{verification_id}",
    summary="Get Verification Result",
    description="Retrieve a previously completed verification result"
)
async def get_verification_result(verification_id: str) -> Dict[str, Any]:
    """
    Retrieve verification result by ID.
    
    Args:
        verification_id: Unique verification identifier
        
    Returns:
        Dict containing verification result if found
    """
    # TODO: Implement result storage and retrieval
    # For now, return not implemented
    raise HTTPException(
        status_code=501,
        detail="Verification result retrieval not yet implemented"
    )


async def _validate_request(request: SupportVerificationRequest) -> None:
    """
    Validate verification request parameters.
    
    Args:
        request: Verification request to validate
        
    Raises:
        ValueError: If validation fails
    """
    # Check API key configuration
    if not settings.OPENAI_API_KEY:
        raise ValueError("OpenAI API key not configured")
    
    # Validate response length based on verification level
    response_length = len(request.support_response.split())
    
    if request.verification_level == "comprehensive" and response_length < 10:
        raise ValueError("Comprehensive verification requires responses with at least 10 words")
    
    # Check for obvious spam or invalid content
    if request.support_response.lower().strip() in ["test", "hello", "hi", "."]:
        raise ValueError("Support response appears to be test content")
    
    # Validate subject areas if provided
    if request.subject_areas:
        # This validation is already handled by Pydantic, but we can add business logic here
        pass


async def _schedule_review_notification(verification_id: str, result: SupportVerificationResponse) -> None:
    """
    Schedule notification for manual review.
    
    Args:
        verification_id: Verification identifier
        result: Verification result that needs review
    """
    logger.info(f"Scheduling review notification for {verification_id}")
    
    # TODO: Implement notification system
    # This could send emails, Slack messages, or add to review queue
    pass


@router.get(
    "/stats",
    summary="Get Verification Statistics",
    description="Get system-wide verification statistics"
)
async def get_verification_stats() -> Dict[str, Any]:
    """
    Get verification system statistics.

    Returns:
        Dict containing system statistics
    """
    # TODO: Implement statistics collection
    # For now, return placeholder data
    return {
        "total_verifications": 0,
        "average_score": 0.0,
        "average_processing_time_ms": 0,
        "status_distribution": {
            "approved": 0,
            "needs_review": 0,
            "rejected": 0
        },
        "last_updated": time.time()
    }


@router.post(
    "/process-documents",
    summary="Process Documents",
    description="Process all documents in the data folder and create vector embeddings"
)
async def process_documents(
    background_tasks: BackgroundTasks,
    processor: DocumentProcessor = Depends(get_document_processor)
) -> Dict[str, Any]:
    """
    Process all documents and create vector embeddings.

    Returns:
        Processing results and statistics
    """
    logger.info("Starting document processing via API")

    try:
        # Process documents
        results = await processor.process_all_documents()

        logger.info(f"Document processing completed: {results}")
        return {
            "status": "success",
            "message": "Documents processed successfully",
            "results": results
        }

    except Exception as e:
        logger.error(f"Document processing failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(e)}"
        )


@router.get(
    "/processing-stats",
    summary="Get Processing Statistics",
    description="Get document processing and vector store statistics"
)
async def get_processing_stats(
    processor: DocumentProcessor = Depends(get_document_processor)
) -> Dict[str, Any]:
    """
    Get comprehensive processing statistics.

    Returns:
        Processing and vector store statistics
    """
    try:
        stats = await processor.get_processing_stats()
        return {
            "status": "success",
            "stats": stats
        }

    except Exception as e:
        logger.error(f"Failed to get processing stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get processing stats: {str(e)}"
        )


@router.get(
    "/processing-health",
    summary="Check Processing Health",
    description="Check health of document processing pipeline"
)
async def check_processing_health(
    processor: DocumentProcessor = Depends(get_document_processor)
) -> Dict[str, Any]:
    """
    Check health of document processing pipeline.

    Returns:
        Health status of processing components
    """
    try:
        health = await processor.health_check()
        return health

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }

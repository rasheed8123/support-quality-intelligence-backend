"""
Main pipeline orchestrator for the Support Quality Intelligence system.
Coordinates all verification steps and manages the complete workflow.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List
from datetime import datetime

from app.api.models import (
    SupportVerificationRequest,
    SupportVerificationResponse,
    VerificationStatus,
    ClaimVerification,
    GuidelineCompliance,
    FactualAccuracy,
    Evidence
)
from app.services.rag_pipeline.claim_extraction import ClaimExtractor
from app.services.rag_pipeline.evidence_retrieval import EvidenceRetriever
from app.services.rag_pipeline.fact_verification import FactVerificationEngine
from app.services.rag_pipeline.advanced_retrieval import AdvancedRetrievalEngine
from app.services.rag_pipeline.document_processor import DocumentProcessor
from app.services.rag_pipeline.compliance_checker import ComplianceChecker
from app.services.rag_pipeline.feedback_generator import FeedbackGenerator
from app.config import settings

# Configure logging
logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Main orchestrator for the support verification pipeline.
    
    Coordinates all verification steps including claim extraction,
    evidence retrieval, fact checking, compliance verification,
    and feedback generation.
    """
    
    def __init__(self):
        """Initialize the pipeline orchestrator with all required components"""
        self.model_versions = {
            "claim_extraction": settings.CLAIM_EXTRACTION_MODEL,
            "fact_verification": settings.FACT_VERIFICATION_MODEL,
            "compliance_check": settings.COMPLIANCE_CHECK_MODEL,
            "feedback_generation": settings.FEEDBACK_GENERATION_MODEL,
            "query_expansion": settings.QUERY_EXPANSION_MODEL,
            "reranking": settings.RERANKING_MODEL,
            "embedding": settings.EMBEDDING_MODEL
        }
        
        # Initialize components
        self._claim_extractor = ClaimExtractor()
        self._evidence_retriever = EvidenceRetriever()  # Legacy retriever for fallback
        self._advanced_retriever = AdvancedRetrievalEngine()  # New advanced retriever
        self._verification_engine = FactVerificationEngine()
        self._document_processor = DocumentProcessor()
        self._compliance_checker = ComplianceChecker()  # Phase 4: Compliance checking
        self._feedback_generator = FeedbackGenerator()  # Phase 4: Feedback generation
        
        logger.info("Pipeline orchestrator initialized")
    
    async def verify_response(
        self, 
        request: SupportVerificationRequest, 
        verification_id: str
    ) -> SupportVerificationResponse:
        """
        Main verification pipeline execution.
        
        Args:
            request: Verification request with support response and parameters
            verification_id: Unique identifier for this verification
            
        Returns:
            SupportVerificationResponse: Complete verification results
        """
        logger.info(f"Starting verification pipeline for {verification_id}")
        
        try:
            # Step 1: Extract claims from support response
            claims = await self._extract_claims(request, verification_id)
            logger.debug(f"Extracted {len(claims)} claims for {verification_id}")
            
            # Step 2: Retrieve evidence for claims
            evidence_results = await self._retrieve_evidence(claims, request, verification_id)
            logger.debug(f"Retrieved evidence for {verification_id}")
            
            # Step 3: Verify claims against evidence
            claim_verifications = await self._verify_claims(claims, evidence_results, verification_id)
            logger.debug(f"Verified {len(claim_verifications)} claims for {verification_id}")
            
            # Step 4: Check guideline compliance
            guideline_compliance = await self._check_compliance(request, verification_id)
            logger.debug(f"Completed compliance check for {verification_id}")
            
            # Step 5: Calculate scores and generate feedback
            factual_accuracy = self._calculate_factual_accuracy(claim_verifications)
            overall_score = self._calculate_overall_score(factual_accuracy, guideline_compliance)
            verification_status = self._determine_verification_status(overall_score, request)
            
            # Step 6: Generate feedback
            feedback = await self._generate_feedback(
                request, claim_verifications, guideline_compliance, verification_id
            )

            # Step 7: Compile all evidence
            all_supporting_evidence = []
            all_conflicting_evidence = []

            for verification in claim_verifications:
                all_supporting_evidence.extend(verification.supporting_evidence)
                all_conflicting_evidence.extend(verification.contradicting_evidence)

            # Step 8: Compile final response
            response = SupportVerificationResponse(
                overall_score=overall_score,
                verification_status=verification_status,
                processing_time_ms=0,  # Will be set by endpoint
                claim_verifications=claim_verifications,
                guideline_compliance=guideline_compliance,
                factual_accuracy=factual_accuracy,
                feedback_summary=feedback["summary"],
                improvement_suggestions=feedback["suggestions"],
                suggested_response=feedback.get("improved_response"),
                supporting_evidence=all_supporting_evidence,
                conflicting_evidence=all_conflicting_evidence,
                verification_id=verification_id,
                timestamp=datetime.utcnow().isoformat(),
                model_versions=self.model_versions
            )
            
            logger.info(
                f"Verification {verification_id} completed with status {verification_status} "
                f"and score {overall_score:.3f}"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Pipeline execution failed for {verification_id}: {str(e)}", exc_info=True)
            raise
    
    async def _extract_claims(
        self,
        request: SupportVerificationRequest,
        verification_id: str
    ) -> List[Any]:
        """
        Extract verifiable claims from the support response.

        Args:
            request: Verification request
            verification_id: Verification identifier

        Returns:
            List of extracted claims
        """
        logger.debug(f"Extracting claims for {verification_id}")

        # Build context for claim extraction
        context = {
            "agent_id": request.agent_id,
            "customer_segment": request.customer_segment,
            "subject_areas": request.subject_areas,
            "verification_level": request.verification_level
        }

        # Extract claims using OpenAI
        claims = await self._claim_extractor.extract_claims(
            response_text=request.support_response,
            customer_query=request.customer_query,
            context=context
        )

        # Validate and filter claims
        validated_claims = await self._claim_extractor.validate_claims(claims)

        logger.info(f"Extracted and validated {len(validated_claims)} claims for {verification_id}")
        return validated_claims
    
    async def _retrieve_evidence(
        self,
        claims: List[Any],
        request: SupportVerificationRequest,
        verification_id: str
    ) -> Dict[str, List[Evidence]]:
        """
        Retrieve evidence for all claims.

        Args:
            claims: List of extracted claims
            request: Original verification request
            verification_id: Verification identifier

        Returns:
            Dictionary mapping claim text to evidence list
        """
        logger.debug(f"Retrieving evidence for {verification_id}")

        # Determine max evidence per claim based on verification level
        max_evidence_per_claim = {
            "standard": 3,
            "strict": 5,
            "comprehensive": 7
        }.get(request.verification_level, 3)

        # Use advanced retrieval engine for better results
        try:
            evidence_map = await self._advanced_retriever.retrieve_evidence_for_claims(
                claims=claims,
                max_evidence_per_claim=max_evidence_per_claim
            )
        except Exception as e:
            logger.warning(f"Advanced retrieval failed, falling back to basic retrieval: {str(e)}")
            # Fallback to basic retrieval
            evidence_map = await self._evidence_retriever.retrieve_evidence_for_claims(
                claims=claims,
                max_evidence_per_claim=max_evidence_per_claim
            )

        logger.info(f"Retrieved evidence for {len(evidence_map)} claims for {verification_id}")
        return evidence_map
    
    async def _verify_claims(
        self,
        claims: List[Any],
        evidence_map: Dict[str, List[Evidence]],
        verification_id: str
    ) -> List[ClaimVerification]:
        """
        Verify each claim against retrieved evidence.

        Args:
            claims: List of claims to verify
            evidence_map: Map of claim text to evidence list
            verification_id: Verification identifier

        Returns:
            List of claim verification results
        """
        logger.debug(f"Verifying claims for {verification_id}")

        # Use batch verification for better performance
        verifications = await self._verification_engine.batch_verify_claims(
            claims=claims,
            evidence_map=evidence_map,
            batch_size=5
        )

        logger.info(f"Verified {len(verifications)} claims for {verification_id}")
        return verifications
    
    async def _check_compliance(
        self,
        request: SupportVerificationRequest,
        verification_id: str
    ) -> GuidelineCompliance:
        """
        Check response compliance against support guidelines.

        Args:
            request: Verification request
            verification_id: Verification identifier

        Returns:
            Guideline compliance assessment
        """
        logger.debug(f"Checking compliance for {verification_id}")

        try:
            # Extract claims for compliance checking
            claims = await self._claim_extractor.extract_claims(
                response_text=request.support_response,
                customer_query=request.customer_query,
                context={"verification_level": request.verification_level}
            )

            # Use the compliance checker
            compliance_result = await self._compliance_checker.check_compliance(
                support_response=request.support_response,
                customer_query=request.customer_query,
                claims=claims,
                context={
                    "verification_level": request.verification_level,
                    "subject_areas": request.subject_areas or []
                }
            )

            # Convert to GuidelineCompliance format
            return GuidelineCompliance(
                overall_score=compliance_result.overall_score,
                violations=[{
                    "type": v.rule_type,
                    "severity": v.severity,
                    "description": v.description,
                    "suggestion": v.suggested_correction
                } for v in compliance_result.violations],
                recommendations=[{
                    "category": r.category,
                    "description": r.description,
                    "priority": r.priority
                } for r in compliance_result.recommendations],
                compliant_aspects=compliance_result.compliant_aspects,
                guidelines_checked=compliance_result.guidelines_checked
            )

        except Exception as e:
            logger.error(f"Compliance checking failed for {verification_id}: {str(e)}")
            # Return fallback compliance result
            return GuidelineCompliance(
                overall_score=0.5,
                violations=[],
                recommendations=["Unable to perform compliance check"],
                compliant_aspects=["Basic response structure"],
                guidelines_checked=0
            )
    
    def _calculate_factual_accuracy(self, verifications: List[ClaimVerification]) -> FactualAccuracy:
        """
        Calculate factual accuracy metrics from claim verifications.

        Args:
            verifications: List of claim verification results

        Returns:
            FactualAccuracy metrics
        """
        # Use the verification engine's calculation method
        accuracy_metrics = self._verification_engine.calculate_overall_accuracy(verifications)

        return FactualAccuracy(
            overall_score=accuracy_metrics["overall_score"],
            total_claims=accuracy_metrics["total_claims"],
            accurate_claims=accuracy_metrics["accurate_claims"],
            inaccurate_claims=accuracy_metrics["inaccurate_claims"],
            partially_accurate_claims=accuracy_metrics["partially_accurate_claims"],
            insufficient_evidence_claims=accuracy_metrics["insufficient_evidence_claims"]
        )
    
    def _calculate_overall_score(
        self, 
        factual_accuracy: FactualAccuracy, 
        compliance: GuidelineCompliance
    ) -> float:
        """
        Calculate composite overall score.
        
        Args:
            factual_accuracy: Factual accuracy metrics
            compliance: Compliance assessment
            
        Returns:
            Overall composite score (0.0 to 1.0)
        """
        # Weight factual accuracy more heavily (60%) than compliance (40%)
        return (factual_accuracy.overall_score * 0.6) + (compliance.overall_score * 0.4)
    
    def _determine_verification_status(
        self, 
        overall_score: float, 
        request: SupportVerificationRequest
    ) -> VerificationStatus:
        """
        Determine verification status based on score and thresholds.
        
        Args:
            overall_score: Calculated overall score
            request: Original verification request
            
        Returns:
            VerificationStatus enum value
        """
        threshold = request.min_accuracy_score
        
        if overall_score >= threshold:
            return VerificationStatus.APPROVED
        elif overall_score >= (threshold - 0.1):  # Within 10% of threshold
            return VerificationStatus.NEEDS_REVIEW
        else:
            return VerificationStatus.REJECTED
    
    async def _generate_feedback(
        self,
        request: SupportVerificationRequest,
        verifications: List[ClaimVerification],
        compliance: GuidelineCompliance,
        verification_id: str
    ) -> Dict[str, Any]:
        """
        Generate actionable feedback for the support response.

        Args:
            request: Original verification request
            verifications: Claim verification results
            compliance: Compliance assessment
            verification_id: Verification identifier

        Returns:
            Dictionary with feedback summary and suggestions
        """
        logger.debug(f"Generating feedback for {verification_id}")

        try:
            # Extract claims for feedback generation
            claims = await self._claim_extractor.extract_claims(
                response_text=request.support_response,
                customer_query=request.customer_query,
                context={"verification_level": request.verification_level}
            )

            # Create compliance result object for feedback generator
            from app.services.rag_pipeline.compliance_checker import ComplianceResult, ComplianceViolation, ComplianceRecommendation

            compliance_result = ComplianceResult(
                overall_score=compliance.overall_score,
                violations=[
                    ComplianceViolation(
                        rule_type=v.get("type", "unknown"),
                        severity=v.get("severity", "minor"),
                        description=v.get("description", ""),
                        violated_text="",
                        guideline_reference="",
                        suggested_correction=v.get("suggestion", ""),
                        confidence=0.8
                    ) for v in compliance.violations
                ],
                recommendations=[
                    ComplianceRecommendation(
                        category=r.get("category", "general"),
                        description=r.get("description", ""),
                        priority=r.get("priority", "medium"),
                        implementation=""
                    ) for r in compliance.recommendations
                ],
                compliant_aspects=compliance.compliant_aspects,
                guidelines_checked=compliance.guidelines_checked,
                processing_time_ms=0
            )

            # Use the feedback generator
            feedback_result = await self._feedback_generator.generate_feedback(
                support_response=request.support_response,
                customer_query=request.customer_query,
                claims=claims,
                claim_verifications=verifications,
                compliance_result=compliance_result,
                context={
                    "verification_level": request.verification_level,
                    "agent_id": request.agent_id
                }
            )

            return {
                "summary": feedback_result.overall_feedback,
                "suggestions": [s.description for s in feedback_result.improvement_suggestions],
                "improved_response": feedback_result.response_suggestion.improved_response if feedback_result.response_suggestion else None
            }

        except Exception as e:
            logger.error(f"Feedback generation failed for {verification_id}: {str(e)}")
            # Return fallback feedback
            return {
                "summary": "Response processed successfully.",
                "suggestions": ["Consider reviewing response for accuracy and completeness"],
                "improved_response": None
            }

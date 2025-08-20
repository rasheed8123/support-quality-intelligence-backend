"""
Fact verification engine for the Support Quality Intelligence system.
Verifies claims against retrieved evidence using OpenAI GPT-4o.
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from datetime import datetime

from app.api.models import Evidence, ClaimVerification, ClaimStatus
from app.services.rag_pipeline.claim_extraction import Claim
from app.config import settings

logger = logging.getLogger(__name__)


class FactVerificationEngine:
    """
    Advanced fact verification engine using OpenAI GPT-4o.
    
    Verifies individual claims against retrieved evidence and provides
    detailed verification results with confidence scores.
    """
    
    def __init__(self):
        """Initialize the fact verification engine"""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.FACT_VERIFICATION_MODEL
        
        # Verification confidence thresholds
        self.confidence_thresholds = {
            "high_confidence": 0.9,
            "medium_confidence": 0.7,
            "low_confidence": 0.5
        }
        
        logger.info(f"Fact verification engine initialized with model: {self.model}")
    
    async def verify_claims(
        self, 
        claims: List[Claim], 
        evidence_map: Dict[str, List[Evidence]],
        min_confidence: float = 0.8
    ) -> List[ClaimVerification]:
        """
        Verify all claims against their evidence.
        
        Args:
            claims: List of claims to verify
            evidence_map: Map of claim text to evidence list
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of claim verification results
        """
        logger.info(f"Verifying {len(claims)} claims against evidence")
        
        verification_results = []
        
        for claim in claims:
            try:
                evidence_list = evidence_map.get(claim.text, [])
                
                verification = await self._verify_single_claim(
                    claim, evidence_list, min_confidence
                )
                
                verification_results.append(verification)
                
            except Exception as e:
                logger.error(f"Failed to verify claim '{claim.text}': {str(e)}")
                # Create fallback verification
                verification_results.append(self._create_fallback_verification(claim))
        
        # Log verification summary
        status_counts = {}
        for verification in verification_results:
            status = verification.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        logger.info(f"Verification complete: {status_counts}")
        return verification_results
    
    async def _verify_single_claim(
        self, 
        claim: Claim, 
        evidence_list: List[Evidence],
        min_confidence: float
    ) -> ClaimVerification:
        """Verify a single claim against its evidence"""
        
        if not evidence_list:
            return ClaimVerification(
                claim_text=claim.text,
                status=ClaimStatus.INSUFFICIENT_EVIDENCE,
                confidence=0.0,
                supporting_evidence=[],
                contradicting_evidence=[],
                explanation="No evidence found to verify this claim.",
                corrections=None,
                source_citations=[],
                verification_timestamp=datetime.utcnow().isoformat()
            )
        
        # Build verification prompt
        verification_prompt = self._build_verification_prompt(claim, evidence_list)
        
        try:
            # Call OpenAI for verification
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_verification_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": verification_prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistent verification
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            # Parse verification result
            result = json.loads(response.choices[0].message.content)
            return self._parse_verification_result(result, claim, evidence_list)
            
        except Exception as e:
            logger.error(f"OpenAI verification failed for claim '{claim.text}': {str(e)}")
            return self._create_fallback_verification(claim)
    
    def _get_verification_system_prompt(self) -> str:
        """Get the system prompt for fact verification"""
        return """You are an expert fact verification system for educational support responses.

Your task is to verify claims against authoritative evidence and provide detailed verification results.

For each claim, analyze the evidence and determine:

1. STATUS: Choose one of:
   - ACCURATE: Claim is fully supported by evidence
   - INACCURATE: Claim contradicts the evidence  
   - PARTIALLY_ACCURATE: Claim is partially correct but has inaccuracies
   - INSUFFICIENT_EVIDENCE: Not enough evidence to verify

2. CONFIDENCE: Score from 0.0 to 1.0 indicating verification confidence

3. SUPPORTING_EVIDENCE: List evidence that supports the claim

4. CONTRADICTING_EVIDENCE: List evidence that contradicts the claim

5. EXPLANATION: Clear reasoning for the verification decision

6. CORRECTIONS: If inaccurate, provide the correct information

7. SOURCE_CITATIONS: List specific sources used

Be conservative and precise. If evidence is ambiguous, indicate insufficient evidence rather than guessing.

Focus on factual accuracy for:
- Numbers, amounts, percentages
- Dates, durations, timelines  
- Names, titles, contact information
- Policies, procedures, requirements
- Statistics and data points

Return valid JSON with the verification result."""
    
    def _build_verification_prompt(self, claim: Claim, evidence_list: List[Evidence]) -> str:
        """Build verification prompt with claim and evidence"""
        
        prompt_parts = [
            f"CLAIM TO VERIFY: \"{claim.text}\"",
            f"CLAIM TYPE: {claim.claim_type}",
            f"VERIFICATION PRIORITY: {claim.verification_priority}",
            f"SPECIFICITY LEVEL: {claim.specificity_level}",
            ""
        ]
        
        if claim.entities:
            prompt_parts.append(f"KEY ENTITIES: {', '.join(claim.entities)}")
            prompt_parts.append("")
        
        prompt_parts.append("EVIDENCE:")
        
        for i, evidence in enumerate(evidence_list, 1):
            prompt_parts.extend([
                f"\nEvidence {i}:",
                f"Source: {evidence.source}",
                f"Content: {evidence.content}",
                f"Relevance Score: {evidence.relevance_score:.2f}",
                f"Document Type: {evidence.document_type}"
            ])
            
            if evidence.last_updated:
                prompt_parts.append(f"Last Updated: {evidence.last_updated}")
        
        prompt_parts.extend([
            "",
            "Verify the claim against this evidence and provide:",
            "- status: ACCURATE, INACCURATE, PARTIALLY_ACCURATE, or INSUFFICIENT_EVIDENCE",
            "- confidence: 0.0 to 1.0",
            "- supporting_evidence: list of evidence indices that support the claim",
            "- contradicting_evidence: list of evidence indices that contradict the claim", 
            "- explanation: detailed reasoning for the verification decision",
            "- corrections: if inaccurate, provide correct information",
            "- source_citations: list of source names used",
            "",
            "Return JSON format with these fields."
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_verification_result(
        self, 
        result: Dict[str, Any], 
        claim: Claim, 
        evidence_list: List[Evidence]
    ) -> ClaimVerification:
        """Parse OpenAI verification result into ClaimVerification object"""
        
        # Validate and extract status
        status_str = result.get("status", "INSUFFICIENT_EVIDENCE").upper()
        try:
            status = ClaimStatus(status_str)
        except ValueError:
            logger.warning(f"Invalid status '{status_str}', defaulting to INSUFFICIENT_EVIDENCE")
            status = ClaimStatus.INSUFFICIENT_EVIDENCE
        
        # Extract confidence score
        confidence = float(result.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
        
        # Extract supporting evidence
        supporting_indices = result.get("supporting_evidence", [])
        supporting_evidence = []
        for idx in supporting_indices:
            if isinstance(idx, int) and 1 <= idx <= len(evidence_list):
                supporting_evidence.append(evidence_list[idx - 1])
        
        # Extract contradicting evidence
        contradicting_indices = result.get("contradicting_evidence", [])
        contradicting_evidence = []
        for idx in contradicting_indices:
            if isinstance(idx, int) and 1 <= idx <= len(evidence_list):
                contradicting_evidence.append(evidence_list[idx - 1])
        
        # Extract other fields
        explanation = result.get("explanation", "No explanation provided.")
        corrections = result.get("corrections")
        source_citations = result.get("source_citations", [])
        
        # Ensure source citations are strings
        if not isinstance(source_citations, list):
            source_citations = []
        source_citations = [str(citation) for citation in source_citations]
        
        return ClaimVerification(
            claim_text=claim.text,
            status=status,
            confidence=confidence,
            supporting_evidence=supporting_evidence,
            contradicting_evidence=contradicting_evidence,
            explanation=explanation,
            corrections=corrections,
            source_citations=source_citations,
            verification_timestamp=datetime.utcnow().isoformat()
        )
    
    def _create_fallback_verification(self, claim: Claim) -> ClaimVerification:
        """Create fallback verification when OpenAI call fails"""
        return ClaimVerification(
            claim_text=claim.text,
            status=ClaimStatus.INSUFFICIENT_EVIDENCE,
            confidence=0.0,
            supporting_evidence=[],
            contradicting_evidence=[],
            explanation="Verification failed due to technical error. Manual review required.",
            corrections=None,
            source_citations=[],
            verification_timestamp=datetime.utcnow().isoformat()
        )
    
    async def batch_verify_claims(
        self, 
        claims: List[Claim], 
        evidence_map: Dict[str, List[Evidence]],
        batch_size: int = 5
    ) -> List[ClaimVerification]:
        """
        Verify claims in batches for better performance.
        
        Args:
            claims: List of claims to verify
            evidence_map: Map of claim text to evidence
            batch_size: Number of claims to verify concurrently
            
        Returns:
            List of verification results
        """
        logger.info(f"Batch verifying {len(claims)} claims with batch size {batch_size}")
        
        all_results = []
        
        for i in range(0, len(claims), batch_size):
            batch = claims[i:i + batch_size]
            
            # Create verification tasks for this batch
            tasks = []
            for claim in batch:
                evidence_list = evidence_map.get(claim.text, [])
                task = self._verify_single_claim(claim, evidence_list, 0.8)
                tasks.append(task)
            
            # Execute batch concurrently
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle results and exceptions
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Batch verification failed for claim {i+j}: {str(result)}")
                    all_results.append(self._create_fallback_verification(batch[j]))
                else:
                    all_results.append(result)
        
        return all_results
    
    def calculate_overall_accuracy(self, verifications: List[ClaimVerification]) -> Dict[str, Any]:
        """
        Calculate overall accuracy metrics from verification results.
        
        Args:
            verifications: List of claim verification results
            
        Returns:
            Dictionary with accuracy metrics
        """
        if not verifications:
            return {
                "overall_score": 0.0,
                "total_claims": 0,
                "accurate_claims": 0,
                "inaccurate_claims": 0,
                "partially_accurate_claims": 0,
                "insufficient_evidence_claims": 0,
                "average_confidence": 0.0
            }
        
        # Count by status
        status_counts = {
            "ACCURATE": 0,
            "INACCURATE": 0, 
            "PARTIALLY_ACCURATE": 0,
            "INSUFFICIENT_EVIDENCE": 0
        }
        
        total_confidence = 0.0
        
        for verification in verifications:
            status_counts[verification.status.value] += 1
            total_confidence += verification.confidence
        
        # Calculate overall score
        total_claims = len(verifications)
        accurate = status_counts["ACCURATE"]
        partially_accurate = status_counts["PARTIALLY_ACCURATE"]
        
        # Weight: accurate=1.0, partially_accurate=0.5, others=0.0
        weighted_score = (accurate + (partially_accurate * 0.5)) / total_claims
        
        return {
            "overall_score": weighted_score,
            "total_claims": total_claims,
            "accurate_claims": accurate,
            "inaccurate_claims": status_counts["INACCURATE"],
            "partially_accurate_claims": partially_accurate,
            "insufficient_evidence_claims": status_counts["INSUFFICIENT_EVIDENCE"],
            "average_confidence": total_confidence / total_claims
        }

"""
Response models for the Support Quality Intelligence API.
Defines the structure for API responses and verification results.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class VerificationStatus(str, Enum):
    """Overall verification status"""
    APPROVED = "APPROVED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REJECTED = "REJECTED"


class ClaimStatus(str, Enum):
    """Individual claim verification status"""
    ACCURATE = "ACCURATE"
    INACCURATE = "INACCURATE"
    PARTIALLY_ACCURATE = "PARTIALLY_ACCURATE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ViolationSeverity(str, Enum):
    """Compliance violation severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Evidence(BaseModel):
    """Evidence supporting or contradicting a claim"""
    
    source: str = Field(
        ...,
        description="Source document or section",
        example="course-catalog-data.md - Data Science Program"
    )
    
    content: str = Field(
        ...,
        max_length=2000,
        description="Relevant content excerpt",
        example="Data Science & AI Mastery Program: ₹99,000 for 6 months with placement assistance"
    )
    
    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relevance score for this evidence"
    )
    
    document_type: str = Field(
        ...,
        description="Type of source document",
        example="course_catalog"
    )
    
    last_updated: Optional[str] = Field(
        None,
        description="When this information was last updated",
        example="2024-01-15T10:30:00Z"
    )


class ClaimVerification(BaseModel):
    """Verification result for an individual claim"""
    
    claim_text: str = Field(
        ...,
        description="The original claim being verified",
        example="The Data Science program costs ₹99,000"
    )
    
    status: ClaimStatus = Field(
        ...,
        description="Verification status of this claim"
    )
    
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in the verification result"
    )
    
    supporting_evidence: List[Evidence] = Field(
        default_factory=list,
        description="Evidence that supports this claim"
    )
    
    contradicting_evidence: List[Evidence] = Field(
        default_factory=list,
        description="Evidence that contradicts this claim"
    )
    
    explanation: str = Field(
        ...,
        description="Human-readable explanation of the verification",
        example="Claim is accurate. Found exact match in course catalog data."
    )
    
    corrections: Optional[str] = Field(
        None,
        description="Suggested corrections if claim is inaccurate",
        example="The correct fee is ₹99,000, not ₹89,000 as stated."
    )
    
    source_citations: List[str] = Field(
        default_factory=list,
        description="Specific source citations for this claim",
        example=["course-catalog-data.md", "assessment-policies.md"]
    )
    
    verification_timestamp: str = Field(
        ...,
        description="When this verification was performed",
        example="2024-01-15T14:30:00Z"
    )


class ComplianceViolation(BaseModel):
    """A specific guideline compliance violation"""
    
    guideline: str = Field(
        ...,
        description="The guideline that was violated",
        example="Response Time Acknowledgment"
    )
    
    severity: ViolationSeverity = Field(
        ...,
        description="Severity level of this violation"
    )
    
    description: str = Field(
        ...,
        description="Description of the violation",
        example="Response does not acknowledge the customer's urgency level"
    )
    
    suggestion: str = Field(
        ...,
        description="Suggestion for fixing this violation",
        example="Add acknowledgment like 'I understand this is urgent for you'"
    )


class GuidelineCompliance(BaseModel):
    """Overall guideline compliance assessment"""
    
    overall_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall compliance score"
    )
    
    violations: List[ComplianceViolation] = Field(
        default_factory=list,
        description="List of compliance violations found"
    )
    
    recommendations: List[str] = Field(
        default_factory=list,
        description="General recommendations for improvement"
    )
    
    compliant_aspects: List[str] = Field(
        default_factory=list,
        description="Aspects that are compliant with guidelines"
    )
    
    guidelines_checked: int = Field(
        ...,
        description="Number of guidelines checked"
    )


class FactualAccuracy(BaseModel):
    """Factual accuracy assessment"""
    
    overall_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall factual accuracy score"
    )
    
    total_claims: int = Field(
        ...,
        description="Total number of claims verified"
    )
    
    accurate_claims: int = Field(
        ...,
        description="Number of accurate claims"
    )
    
    inaccurate_claims: int = Field(
        ...,
        description="Number of inaccurate claims"
    )
    
    partially_accurate_claims: int = Field(
        ...,
        description="Number of partially accurate claims"
    )
    
    insufficient_evidence_claims: int = Field(
        ...,
        description="Number of claims with insufficient evidence"
    )


class SupportVerificationResponse(BaseModel):
    """
    Complete response model for support verification results.
    
    Contains all verification results, scores, and actionable feedback
    for the support agent and quality assurance team.
    """
    
    # Overall assessment
    overall_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Composite score combining factual accuracy and compliance"
    )
    
    verification_status: VerificationStatus = Field(
        ...,
        description="Overall verification status"
    )
    
    processing_time_ms: int = Field(
        ...,
        description="Processing time in milliseconds"
    )
    
    # Detailed analysis
    claim_verifications: List[ClaimVerification] = Field(
        default_factory=list,
        description="Verification results for individual claims"
    )
    
    guideline_compliance: GuidelineCompliance = Field(
        ...,
        description="Compliance assessment results"
    )
    
    factual_accuracy: FactualAccuracy = Field(
        ...,
        description="Factual accuracy assessment"
    )
    
    # Actionable feedback
    feedback_summary: str = Field(
        ...,
        description="Human-readable summary of verification results"
    )
    
    improvement_suggestions: List[str] = Field(
        default_factory=list,
        description="Specific suggestions for improving the response"
    )
    
    suggested_response: Optional[str] = Field(
        None,
        description="AI-generated improved version of the response"
    )
    
    # Evidence and sources
    supporting_evidence: List[Evidence] = Field(
        default_factory=list,
        description="All evidence that supports claims in the response"
    )
    
    conflicting_evidence: List[Evidence] = Field(
        default_factory=list,
        description="Evidence that contradicts claims in the response"
    )
    
    # Metadata
    verification_id: str = Field(
        ...,
        description="Unique identifier for this verification"
    )
    
    timestamp: str = Field(
        ...,
        description="ISO timestamp when verification was completed"
    )
    
    model_versions: Dict[str, str] = Field(
        default_factory=dict,
        description="Versions of AI models used in verification"
    )
    
    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        schema_extra = {
            "example": {
                "overall_score": 0.92,
                "verification_status": "APPROVED",
                "processing_time_ms": 1847,
                "factual_accuracy": {
                    "overall_score": 0.95,
                    "total_claims": 3,
                    "accurate_claims": 3,
                    "inaccurate_claims": 0,
                    "partially_accurate_claims": 0,
                    "insufficient_evidence_claims": 0
                },
                "guideline_compliance": {
                    "overall_score": 0.88,
                    "violations": [],
                    "recommendations": ["Consider adding more specific timeline information"],
                    "compliant_aspects": ["Professional tone", "Accurate information"],
                    "guidelines_checked": 5
                },
                "feedback_summary": "Response is highly accurate and compliant with guidelines.",
                "verification_id": "ver_20240115_143000_abc123",
                "timestamp": "2024-01-15T14:30:00Z"
            }
        }

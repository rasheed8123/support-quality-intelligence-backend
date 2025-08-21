"""
Request models for the Support Quality Intelligence API.
Defines the structure and validation for incoming API requests.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional
from enum import Enum


class VerificationLevel(str, Enum):
    """Verification thoroughness levels"""
    STANDARD = "standard"
    STRICT = "strict" 
    COMPREHENSIVE = "comprehensive"


class ResponseFormat(str, Enum):
    """Response detail levels"""
    QUICK = "quick"
    STANDARD = "standard"
    DETAILED = "detailed"


class UrgencyLevel(str, Enum):
    """Request urgency levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class SupportVerificationRequest(BaseModel):
    """
    Main request model for support response verification.
    
    This model defines all parameters needed to verify a support agent's
    response against authoritative documentation and guidelines.
    """
    
    # Core content - required fields
    support_response: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description="The support agent's response to verify",
        example="The Data Science program costs ₹99,000 and includes 6 months of training with placement assistance."
    )
    
    customer_query: Optional[str] = Field(
        None,
        max_length=5000,
        description="Original customer question for context",
        example="What is the cost and duration of your Data Science course?"
    )
    
    # Context information
    agent_id: Optional[str] = Field(
        None,
        max_length=100,
        description="Support agent identifier",
        example="agent_001"
    )
    
    ticket_id: Optional[str] = Field(
        None,
        max_length=100,
        description="Support ticket ID",
        example="TKT-2024-001234"
    )
    
    customer_segment: Optional[str] = Field(
        None,
        max_length=50,
        description="Customer type: student, prospect, alumni, corporate",
        example="prospect"
    )
    
    # Verification parameters
    verification_level: VerificationLevel = Field(
        VerificationLevel.STANDARD,
        description="Thoroughness of verification process"
    )
    
    response_format: ResponseFormat = Field(
        ResponseFormat.STANDARD,
        description="Level of detail in response"
    )
    
    include_suggestions: bool = Field(
        True,
        description="Include improvement suggestions in response"
    )
    
    # Domain context
    subject_areas: Optional[List[str]] = Field(
        None,
        max_items=10,
        description="Relevant subject areas for focused verification",
        example=["data_science", "placement_assistance", "fees"]
    )
    
    urgency_level: UrgencyLevel = Field(
        UrgencyLevel.NORMAL,
        description="Request urgency level"
    )
    
    # Quality thresholds
    min_accuracy_score: float = Field(
        0.8,
        ge=0.0,
        le=1.0,
        description="Minimum acceptable accuracy score (0.0 to 1.0)"
    )
    
    require_source_citation: bool = Field(
        True,
        description="Require source attribution in verification"
    )
    
    @field_validator('support_response')
    @classmethod
    def validate_support_response(cls, v):
        """Validate support response content"""
        if not v or not v.strip():
            raise ValueError("Support response cannot be empty")

        # Check for minimum meaningful content
        words = v.strip().split()
        if len(words) < 3:
            raise ValueError("Support response must contain at least 3 words")

        return v.strip()
    
    @field_validator('subject_areas')
    @classmethod
    def validate_subject_areas(cls, v):
        """Validate subject areas"""
        if v is None:
            return v

        # Remove duplicates and empty strings
        cleaned = list(set(area.strip().lower() for area in v if area.strip()))

        # Validate known subject areas (based on your data folder structure)
        valid_areas = {
            "data_science", "web_development", "placement_assistance",
            "fees", "assessment", "certification", "instructors",
            "support_guidelines", "course_catalog", "general"
        }

        for area in cleaned:
            if area not in valid_areas:
                raise ValueError(f"Unknown subject area: {area}. Valid areas: {', '.join(valid_areas)}")

        return cleaned if cleaned else None
    
    @field_validator('min_accuracy_score')
    @classmethod
    def validate_accuracy_score(cls, v):
        """Validate accuracy score"""
        # Basic validation - detailed cross-field validation will be done in model_validator
        if v < 0.0 or v > 1.0:
            raise ValueError("Accuracy score must be between 0.0 and 1.0")

        return v

    @model_validator(mode='after')
    def validate_accuracy_with_verification_level(self):
        """Validate accuracy score based on verification level"""
        verification_level = self.verification_level
        min_accuracy_score = self.min_accuracy_score

        if verification_level == VerificationLevel.STRICT and min_accuracy_score < 0.85:
            raise ValueError("Strict verification requires minimum accuracy score of 0.85")
        elif verification_level == VerificationLevel.COMPREHENSIVE and min_accuracy_score < 0.9:
            raise ValueError("Comprehensive verification requires minimum accuracy score of 0.9")

        return self
    
    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"  # Reject unknown fields
        json_schema_extra = {
            "example": {
                "support_response": "Our Data Science & AI Mastery Program costs ₹99,000 for the complete 6-month course. This includes live sessions, projects, and placement assistance with our 500+ hiring partners.",
                "customer_query": "What is the fee structure for your Data Science course?",
                "agent_id": "agent_ds_001",
                "ticket_id": "TKT-2024-001234",
                "customer_segment": "prospect",
                "verification_level": "standard",
                "response_format": "detailed",
                "include_suggestions": True,
                "subject_areas": ["data_science", "fees", "placement_assistance"],
                "urgency_level": "normal",
                "min_accuracy_score": 0.8,
                "require_source_citation": True
            }
        }

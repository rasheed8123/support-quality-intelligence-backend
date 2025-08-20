"""
API models package.
Contains Pydantic models for request and response validation.
"""

from .request_models import (
    SupportVerificationRequest,
    VerificationLevel,
    ResponseFormat,
    UrgencyLevel
)

from .response_models import (
    SupportVerificationResponse,
    ClaimVerification,
    GuidelineCompliance,
    FactualAccuracy,
    Evidence,
    ComplianceViolation,
    VerificationStatus,
    ClaimStatus,
    ViolationSeverity
)

__all__ = [
    # Request models
    "SupportVerificationRequest",
    "VerificationLevel",
    "ResponseFormat",
    "UrgencyLevel",

    # Response models
    "SupportVerificationResponse",
    "ClaimVerification",
    "GuidelineCompliance",
    "FactualAccuracy",
    "Evidence",
    "ComplianceViolation",
    "VerificationStatus",
    "ClaimStatus",
    "ViolationSeverity"
]

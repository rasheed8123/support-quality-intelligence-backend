"""
Classification models module for email analysis.

This module provides functions for classifying emails based on:
- Priority level
- Spam/category classification  
- Tone analysis
- Issue type classification
"""

from .priority_classify import classify_priority
from .spam_classify import classify_category
from .tone_classify import classify_tone, classify_issue

__all__ = [
    "classify_priority",
    "classify_category", 
    "classify_tone",
    "classify_issue"
]

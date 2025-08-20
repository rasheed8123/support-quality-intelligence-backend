"""
RAG Pipeline package for the Support Quality Intelligence system.
Contains all components for claim extraction, evidence retrieval, and fact verification.
"""

from .claim_extraction import ClaimExtractor, Claim
from .evidence_retrieval import EvidenceRetriever, DocumentChunk
from .fact_verification import FactVerificationEngine
from .embedding_manager import AdaptiveEmbeddingManager, EmbeddedChunk
from .vector_store import AdvancedVectorStoreManager, SearchResult
from .adaptive_chunking import AdaptiveChunker, DocumentChunk as AdaptiveDocumentChunk
from .advanced_retrieval import AdvancedRetrievalEngine, QueryAnalysis
from .document_processor import DocumentProcessor
from .compliance_checker import ComplianceChecker, ComplianceViolation, ComplianceResult
from .feedback_generator import FeedbackGenerator, ImprovementSuggestion, ResponseSuggestion

__all__ = [
    "ClaimExtractor",
    "Claim",
    "EvidenceRetriever",
    "DocumentChunk",
    "FactVerificationEngine",
    "AdaptiveEmbeddingManager",
    "EmbeddedChunk",
    "AdvancedVectorStoreManager",
    "SearchResult",
    "AdaptiveChunker",
    "AdaptiveDocumentChunk",
    "AdvancedRetrievalEngine",
    "QueryAnalysis",
    "DocumentProcessor",
    "ComplianceChecker",
    "ComplianceViolation",
    "ComplianceResult",
    "FeedbackGenerator",
    "ImprovementSuggestion",
    "ResponseSuggestion"
]
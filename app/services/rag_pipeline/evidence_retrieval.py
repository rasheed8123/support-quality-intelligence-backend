"""
Evidence retrieval engine for the Support Quality Intelligence system.
Retrieves relevant evidence from the knowledge base to verify claims.
"""

import asyncio
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import re
from dataclasses import dataclass
from datetime import datetime

from app.api.models import Evidence
from app.services.rag_pipeline.claim_extraction import Claim
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """A chunk of document content with metadata"""
    content: str
    source_file: str
    document_type: str
    section: Optional[str] = None
    last_modified: Optional[datetime] = None
    relevance_score: float = 0.0


class EvidenceRetriever:
    """
    Evidence retrieval engine that searches through the knowledge base
    to find supporting or contradicting evidence for claims.
    """
    
    def __init__(self):
        """Initialize the evidence retriever"""
        self.data_folder = Path("data")
        self.document_cache = {}
        self.document_types = {
            "course-catalog": ["course", "program", "curriculum"],
            "assessment-policies": ["assessment", "exam", "grading", "evaluation"],
            "fee-structure": ["fee", "cost", "price", "payment"],
            "placement-data": ["placement", "job", "hiring", "company"],
            "instructor-profiles": ["instructor", "faculty", "teacher"],
            "support-guidelines": ["support", "help", "guideline", "policy"]
        }
        
        logger.info("Evidence retriever initialized")
        self._load_documents()
    
    def _load_documents(self):
        """Load and index all documents from the data folder"""
        logger.info("Loading documents from data folder")
        
        if not self.data_folder.exists():
            logger.warning(f"Data folder not found: {self.data_folder}")
            return
        
        document_count = 0
        for file_path in self.data_folder.rglob("*.md"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Determine document type
                doc_type = self._classify_document(file_path.name, content)
                
                # Split into chunks
                chunks = self._chunk_document(content, str(file_path), doc_type)
                
                # Store in cache
                self.document_cache[str(file_path)] = {
                    "content": content,
                    "chunks": chunks,
                    "type": doc_type,
                    "last_modified": datetime.fromtimestamp(file_path.stat().st_mtime)
                }
                
                document_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to load document {file_path}: {str(e)}")
        
        total_chunks = sum(len(doc["chunks"]) for doc in self.document_cache.values())
        logger.info(f"Loaded {document_count} documents with {total_chunks} chunks")
    
    def _classify_document(self, filename: str, content: str) -> str:
        """Classify document type based on filename and content"""
        filename_lower = filename.lower()
        content_lower = content.lower()
        
        for doc_type, keywords in self.document_types.items():
            # Check filename
            if any(keyword in filename_lower for keyword in keywords):
                return doc_type
            
            # Check content (first 500 characters)
            content_sample = content_lower[:500]
            keyword_matches = sum(1 for keyword in keywords if keyword in content_sample)
            if keyword_matches >= 2:
                return doc_type
        
        return "general"
    
    def _chunk_document(self, content: str, source_file: str, doc_type: str) -> List[DocumentChunk]:
        """Split document into meaningful chunks"""
        chunks = []
        
        # Split by sections (headers)
        sections = re.split(r'\n#{1,3}\s+', content)
        
        for i, section in enumerate(sections):
            if not section.strip():
                continue
            
            # Extract section title
            lines = section.strip().split('\n')
            section_title = lines[0] if lines else f"Section {i+1}"
            section_content = '\n'.join(lines[1:]) if len(lines) > 1 else section
            
            # Further split long sections
            if len(section_content) > 1000:
                sub_chunks = self._split_long_section(section_content)
                for j, sub_chunk in enumerate(sub_chunks):
                    chunks.append(DocumentChunk(
                        content=sub_chunk,
                        source_file=source_file,
                        document_type=doc_type,
                        section=f"{section_title} (Part {j+1})"
                    ))
            else:
                chunks.append(DocumentChunk(
                    content=section_content,
                    source_file=source_file,
                    document_type=doc_type,
                    section=section_title
                ))
        
        return chunks
    
    def _split_long_section(self, content: str, max_length: int = 800) -> List[str]:
        """Split long sections into smaller chunks"""
        chunks = []
        sentences = re.split(r'[.!?]+', content)
        
        current_chunk = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if len(current_chunk) + len(sentence) > max_length and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    async def retrieve_evidence_for_claims(
        self, 
        claims: List[Claim],
        max_evidence_per_claim: int = 5
    ) -> Dict[str, List[Evidence]]:
        """
        Retrieve evidence for all claims.
        
        Args:
            claims: List of claims to find evidence for
            max_evidence_per_claim: Maximum evidence items per claim
            
        Returns:
            Dictionary mapping claim text to evidence list
        """
        logger.info(f"Retrieving evidence for {len(claims)} claims")
        
        evidence_results = {}
        
        for claim in claims:
            try:
                evidence_list = await self._retrieve_evidence_for_claim(
                    claim, max_evidence_per_claim
                )
                evidence_results[claim.text] = evidence_list
                
            except Exception as e:
                logger.error(f"Failed to retrieve evidence for claim '{claim.text}': {str(e)}")
                evidence_results[claim.text] = []
        
        total_evidence = sum(len(evidence) for evidence in evidence_results.values())
        logger.info(f"Retrieved {total_evidence} evidence items total")
        
        return evidence_results
    
    async def _retrieve_evidence_for_claim(
        self, 
        claim: Claim, 
        max_evidence: int
    ) -> List[Evidence]:
        """Retrieve evidence for a single claim"""
        
        # Generate search queries for the claim
        search_queries = self._generate_search_queries(claim)
        
        # Search for relevant chunks
        relevant_chunks = []
        for query in search_queries:
            chunks = self._search_chunks(query, claim.expected_evidence_type)
            relevant_chunks.extend(chunks)
        
        # Remove duplicates and rank by relevance
        unique_chunks = self._deduplicate_chunks(relevant_chunks)
        ranked_chunks = self._rank_chunks(unique_chunks, claim)
        
        # Convert to Evidence objects
        evidence_list = []
        for chunk in ranked_chunks[:max_evidence]:
            evidence = Evidence(
                source=self._format_source_name(chunk.source_file, chunk.section),
                content=chunk.content,
                relevance_score=chunk.relevance_score,
                document_type=chunk.document_type,
                last_updated=chunk.last_modified.isoformat() if chunk.last_modified else None
            )
            evidence_list.append(evidence)
        
        return evidence_list
    
    def _generate_search_queries(self, claim: Claim) -> List[str]:
        """Generate search queries for a claim"""
        queries = [claim.text]  # Original claim text
        
        # Add entity-based queries
        for entity in claim.entities:
            if len(entity) > 2:  # Skip very short entities
                queries.append(entity)
        
        # Add type-specific queries
        if claim.claim_type == "factual_data":
            # Extract numbers and amounts
            numbers = re.findall(r'[\d,]+', claim.text)
            for number in numbers:
                queries.append(number)
        
        elif claim.claim_type == "policy_statement":
            # Look for policy keywords
            policy_words = ["policy", "rule", "guideline", "requirement"]
            for word in policy_words:
                if word in claim.text.lower():
                    queries.append(word)
        
        # Remove duplicates and very short queries
        unique_queries = list(set(q for q in queries if len(q) > 2))
        return unique_queries[:5]  # Limit to 5 queries
    
    def _search_chunks(self, query: str, evidence_type: str) -> List[DocumentChunk]:
        """Search for chunks matching the query"""
        matching_chunks = []
        query_lower = query.lower()
        
        for doc_path, doc_data in self.document_cache.items():
            # Filter by document type if relevant
            if evidence_type == "numerical_data" and doc_data["type"] not in ["course-catalog", "fee-structure", "placement-data"]:
                continue
            elif evidence_type == "policy_document" and doc_data["type"] not in ["assessment-policies", "support-guidelines"]:
                continue
            
            for chunk in doc_data["chunks"]:
                # Calculate relevance score
                relevance = self._calculate_relevance(chunk.content, query_lower)
                
                if relevance > 0.1:  # Minimum relevance threshold
                    chunk.relevance_score = relevance
                    matching_chunks.append(chunk)
        
        return matching_chunks
    
    def _calculate_relevance(self, content: str, query: str) -> float:
        """Calculate relevance score between content and query"""
        content_lower = content.lower()
        
        # Exact match gets highest score
        if query in content_lower:
            return 1.0
        
        # Word overlap scoring
        query_words = set(query.split())
        content_words = set(content_lower.split())
        
        if not query_words:
            return 0.0
        
        overlap = len(query_words.intersection(content_words))
        relevance = overlap / len(query_words)
        
        # Boost score for numerical matches
        if re.search(r'\d+', query) and re.search(r'\d+', content_lower):
            relevance += 0.3
        
        # Boost score for currency matches
        if '₹' in query and '₹' in content_lower:
            relevance += 0.4
        
        return min(relevance, 1.0)
    
    def _deduplicate_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Remove duplicate chunks"""
        seen_content = set()
        unique_chunks = []
        
        for chunk in chunks:
            # Use first 100 characters as deduplication key
            content_key = chunk.content[:100].strip()
            if content_key not in seen_content:
                seen_content.add(content_key)
                unique_chunks.append(chunk)
        
        return unique_chunks
    
    def _rank_chunks(self, chunks: List[DocumentChunk], claim: Claim) -> List[DocumentChunk]:
        """Rank chunks by relevance to the claim"""
        
        # Apply additional scoring based on claim characteristics
        for chunk in chunks:
            # Boost score for high-priority claims
            if claim.verification_priority == "high":
                chunk.relevance_score *= 1.2
            
            # Boost score for specific claims
            if claim.specificity_level == "specific":
                chunk.relevance_score *= 1.1
            
            # Boost score for matching document types
            if self._is_document_type_relevant(chunk.document_type, claim.claim_type):
                chunk.relevance_score *= 1.3
        
        # Sort by relevance score
        return sorted(chunks, key=lambda x: x.relevance_score, reverse=True)
    
    def _is_document_type_relevant(self, doc_type: str, claim_type: str) -> bool:
        """Check if document type is relevant for claim type"""
        relevance_map = {
            "factual_data": ["course-catalog", "fee-structure", "placement-data"],
            "policy_statement": ["assessment-policies", "support-guidelines"],
            "procedure_step": ["support-guidelines", "assessment-policies"],
            "timeline_info": ["course-catalog", "placement-data"],
            "contact_info": ["instructor-profiles", "support-guidelines"]
        }
        
        relevant_types = relevance_map.get(claim_type, [])
        return doc_type in relevant_types
    
    def _format_source_name(self, file_path: str, section: Optional[str]) -> str:
        """Format source name for display"""
        filename = Path(file_path).name
        if section:
            return f"{filename} - {section}"
        return filename
    
    async def get_document_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded documents"""
        if not self.document_cache:
            return {"total_documents": 0, "total_chunks": 0, "document_types": {}}
        
        type_counts = {}
        total_chunks = 0
        
        for doc_data in self.document_cache.values():
            doc_type = doc_data["type"]
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
            total_chunks += len(doc_data["chunks"])
        
        return {
            "total_documents": len(self.document_cache),
            "total_chunks": total_chunks,
            "document_types": type_counts,
            "data_folder": str(self.data_folder)
        }

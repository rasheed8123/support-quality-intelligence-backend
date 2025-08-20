"""
Adaptive chunking engine for the Support Quality Intelligence system.
Intelligently chunks documents based on content type and structure.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import hashlib

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ChunkMetadata:
    """Metadata for a document chunk"""
    chunk_id: str
    document_id: str
    document_type: str
    section_title: Optional[str]
    chunk_index: int
    total_chunks: int
    content_density: str
    contains_numbers: bool
    contains_dates: bool
    word_count: int
    char_count: int
    created_at: str


@dataclass
class DocumentChunk:
    """A chunk of document content with rich metadata"""
    content: str
    metadata: ChunkMetadata


class AdaptiveChunker:
    """
    Advanced document chunking engine that adapts chunking strategy
    based on document type and content characteristics.
    """
    
    def __init__(self):
        """Initialize the adaptive chunker"""
        self.max_chunk_size = settings.MAX_CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP
        
        # Content type patterns
        self.content_patterns = {
            "factual_dense": [
                r'₹[\d,]+',  # Currency amounts
                r'\d+%',     # Percentages
                r'\d+\s*(months?|weeks?|days?|years?)',  # Durations
                r'\d+\s*(students?|candidates?|companies?)',  # Counts
                r'(average|median|minimum|maximum)\s*[:=]\s*₹?[\d,]+',  # Statistics
            ],
            "policy_statements": [
                r'\b(must|shall|required|mandatory|prohibited)\b',
                r'\b(policy|rule|guideline|regulation)\b',
                r'\b(minimum|maximum)\s+\d+',
                r'\b(attendance|grade|score)\s*[:=]\s*\d+%?',
            ],
            "procedural": [
                r'\b(step|phase|stage)\s*\d+',
                r'\b(first|second|third|next|then|finally)\b',
                r'\b(process|procedure|workflow|method)\b',
                r'^\s*\d+\.',  # Numbered lists
            ],
            "narrative": [
                r'\b(story|experience|journey|background)\b',
                r'\b(he|she|they|we|I)\s+(was|were|am|is|are)',
                r'\b(once|when|after|before|during)\b',
            ]
        }
        
        logger.info("Adaptive chunker initialized")
    
    async def chunk_document(
        self, 
        content: str, 
        document_id: str,
        document_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """
        Chunk a document using adaptive strategies based on content type.
        
        Args:
            content: Document content to chunk
            document_id: Unique document identifier
            document_type: Type of document (course_catalog, policies, etc.)
            metadata: Additional document metadata
            
        Returns:
            List of document chunks with rich metadata
        """
        logger.info(f"Chunking document {document_id} of type {document_type}")
        
        if not content or not content.strip():
            logger.warning(f"Empty content for document {document_id}")
            return []
        
        # Analyze document structure and content
        structure_analysis = self._analyze_document_structure(content)
        content_analysis = self._analyze_content_characteristics(content)
        
        # Select chunking strategy
        chunking_strategy = self._select_chunking_strategy(
            document_type, structure_analysis, content_analysis
        )
        
        # Apply chunking strategy
        chunks = await self._apply_chunking_strategy(
            content, chunking_strategy, structure_analysis
        )
        
        # Create chunk objects with metadata
        document_chunks = []
        total_chunks = len(chunks)
        
        for i, (chunk_content, section_info) in enumerate(chunks):
            chunk_metadata = self._create_chunk_metadata(
                chunk_content=chunk_content,
                document_id=document_id,
                document_type=document_type,
                section_info=section_info,
                chunk_index=i,
                total_chunks=total_chunks,
                content_analysis=content_analysis
            )
            
            document_chunks.append(DocumentChunk(
                content=chunk_content,
                metadata=chunk_metadata
            ))
        
        logger.info(f"Created {len(document_chunks)} chunks for document {document_id}")
        return document_chunks
    
    def _analyze_document_structure(self, content: str) -> Dict[str, Any]:
        """Analyze document structure to identify sections and hierarchy"""
        
        # Find headers (markdown style)
        headers = []
        header_pattern = r'^(#{1,6})\s+(.+)$'
        
        for match in re.finditer(header_pattern, content, re.MULTILINE):
            level = len(match.group(1))
            title = match.group(2).strip()
            position = match.start()
            headers.append({
                "level": level,
                "title": title,
                "position": position
            })
        
        # Find list structures
        list_items = len(re.findall(r'^\s*[-*+]\s+', content, re.MULTILINE))
        numbered_items = len(re.findall(r'^\s*\d+\.\s+', content, re.MULTILINE))
        
        # Find table structures
        table_rows = len(re.findall(r'\|.*\|', content))
        
        return {
            "headers": headers,
            "has_clear_sections": len(headers) > 0,
            "max_header_level": max([h["level"] for h in headers]) if headers else 0,
            "list_items": list_items,
            "numbered_items": numbered_items,
            "table_rows": table_rows,
            "has_structured_content": list_items > 0 or numbered_items > 0 or table_rows > 0
        }
    
    def _analyze_content_characteristics(self, content: str) -> Dict[str, Any]:
        """Analyze content characteristics for adaptive chunking"""
        
        content_lower = content.lower()
        
        # Count pattern matches for each content type
        pattern_counts = {}
        for content_type, patterns in self.content_patterns.items():
            count = 0
            for pattern in patterns:
                count += len(re.findall(pattern, content_lower, re.IGNORECASE))
            pattern_counts[content_type] = count
        
        # Determine dominant content type
        dominant_type = max(pattern_counts, key=pattern_counts.get)
        
        # Additional characteristics
        word_count = len(content.split())
        sentence_count = len(re.findall(r'[.!?]+', content))
        avg_sentence_length = word_count / max(sentence_count, 1)
        
        # Check for specific elements
        contains_numbers = bool(re.search(r'\d+', content))
        contains_dates = bool(re.search(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b', content))
        contains_currency = bool(re.search(r'₹|rupees?|dollars?|\$', content_lower))
        
        return {
            "dominant_type": dominant_type,
            "pattern_counts": pattern_counts,
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_sentence_length": avg_sentence_length,
            "contains_numbers": contains_numbers,
            "contains_dates": contains_dates,
            "contains_currency": contains_currency,
            "content_density": self._determine_content_density(pattern_counts, contains_numbers, contains_currency)
        }
    
    def _determine_content_density(self, pattern_counts: Dict[str, int], contains_numbers: bool, contains_currency: bool) -> str:
        """Determine content density type"""
        
        if pattern_counts["factual_dense"] >= 3 or (contains_numbers and contains_currency):
            return "factual_dense"
        elif pattern_counts["policy_statements"] >= 2:
            return "policy_dense"
        elif pattern_counts["procedural"] >= 2:
            return "procedural"
        elif pattern_counts["narrative"] >= 1:
            return "narrative"
        else:
            return "mixed"
    
    def _select_chunking_strategy(
        self, 
        document_type: str, 
        structure_analysis: Dict[str, Any],
        content_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Select optimal chunking strategy based on analysis"""
        
        # Default strategy
        strategy = {
            "method": "semantic_sections",
            "max_size": self.max_chunk_size,
            "overlap": self.chunk_overlap,
            "preserve_sections": True,
            "split_on_sentences": True
        }
        
        # Adjust based on document type
        if document_type in ["course_catalog", "fee_structure"]:
            # Factual documents - preserve structure, smaller chunks for precision
            strategy.update({
                "max_size": 600,
                "overlap": 50,
                "preserve_sections": True,
                "split_on_sentences": True
            })
            
        elif document_type in ["assessment_policies", "support_guidelines"]:
            # Policy documents - preserve logical units
            strategy.update({
                "method": "policy_aware",
                "max_size": 800,
                "overlap": 100,
                "preserve_sections": True,
                "respect_policy_boundaries": True
            })
            
        elif document_type in ["instructor_profiles", "success_stories"]:
            # Narrative documents - larger chunks for context
            strategy.update({
                "max_size": 1200,
                "overlap": 150,
                "preserve_sections": False,
                "split_on_sentences": True
            })
        
        # Adjust based on content characteristics
        if content_analysis["content_density"] == "factual_dense":
            strategy["max_size"] = min(strategy["max_size"], 500)
            strategy["preserve_sections"] = True
            
        elif content_analysis["content_density"] == "narrative":
            strategy["max_size"] = max(strategy["max_size"], 1000)
            strategy["overlap"] = max(strategy["overlap"], 100)
        
        # Adjust based on structure
        if structure_analysis["has_clear_sections"]:
            strategy["preserve_sections"] = True
            strategy["section_aware"] = True
        
        return strategy
    
    async def _apply_chunking_strategy(
        self, 
        content: str, 
        strategy: Dict[str, Any],
        structure_analysis: Dict[str, Any]
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Apply the selected chunking strategy"""
        
        if strategy["method"] == "semantic_sections":
            return self._chunk_by_semantic_sections(content, strategy, structure_analysis)
        elif strategy["method"] == "policy_aware":
            return self._chunk_policy_aware(content, strategy, structure_analysis)
        else:
            return self._chunk_by_size(content, strategy)
    
    def _chunk_by_semantic_sections(
        self, 
        content: str, 
        strategy: Dict[str, Any],
        structure_analysis: Dict[str, Any]
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Chunk by semantic sections with size constraints"""
        
        chunks = []
        
        if structure_analysis["has_clear_sections"]:
            # Split by headers
            sections = self._split_by_headers(content, structure_analysis["headers"])
            
            for section_content, section_info in sections:
                if len(section_content) <= strategy["max_size"]:
                    # Section fits in one chunk
                    chunks.append((section_content.strip(), section_info))
                else:
                    # Split large section
                    sub_chunks = self._split_large_section(section_content, strategy, section_info)
                    chunks.extend(sub_chunks)
        else:
            # No clear sections - split by size with sentence boundaries
            chunks = self._chunk_by_size(content, strategy)
        
        return chunks
    
    def _chunk_policy_aware(
        self, 
        content: str, 
        strategy: Dict[str, Any],
        structure_analysis: Dict[str, Any]
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Chunk with awareness of policy structure"""
        
        # Split on policy boundaries (numbered items, bullet points)
        policy_sections = re.split(r'\n(?=\d+\.|[-*+]\s)', content)
        
        chunks = []
        current_chunk = ""
        current_section_info = {"section_title": "Policy Section", "section_type": "policy"}
        
        for section in policy_sections:
            section = section.strip()
            if not section:
                continue
            
            if len(current_chunk) + len(section) <= strategy["max_size"]:
                current_chunk += "\n" + section if current_chunk else section
            else:
                if current_chunk:
                    chunks.append((current_chunk.strip(), current_section_info))
                current_chunk = section
        
        if current_chunk:
            chunks.append((current_chunk.strip(), current_section_info))
        
        return chunks
    
    def _chunk_by_size(self, content: str, strategy: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """Basic size-based chunking with sentence boundaries"""
        
        chunks = []
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        current_chunk = ""
        section_info = {"section_title": "Content Section", "section_type": "general"}
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= strategy["max_size"]:
                current_chunk += " " + sentence if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append((current_chunk.strip(), section_info))
                current_chunk = sentence
        
        if current_chunk:
            chunks.append((current_chunk.strip(), section_info))
        
        return chunks
    
    def _split_by_headers(self, content: str, headers: List[Dict[str, Any]]) -> List[Tuple[str, Dict[str, Any]]]:
        """Split content by header positions"""
        
        sections = []
        
        for i, header in enumerate(headers):
            start_pos = header["position"]
            end_pos = headers[i + 1]["position"] if i + 1 < len(headers) else len(content)
            
            section_content = content[start_pos:end_pos].strip()
            section_info = {
                "section_title": header["title"],
                "section_type": "header_section",
                "header_level": header["level"]
            }
            
            sections.append((section_content, section_info))
        
        return sections
    
    def _split_large_section(
        self, 
        section_content: str, 
        strategy: Dict[str, Any],
        section_info: Dict[str, Any]
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Split a large section into smaller chunks"""
        
        chunks = []
        sentences = re.split(r'(?<=[.!?])\s+', section_content)
        
        current_chunk = ""
        chunk_index = 0
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= strategy["max_size"]:
                current_chunk += " " + sentence if current_chunk else sentence
            else:
                if current_chunk:
                    chunk_info = {
                        **section_info,
                        "sub_chunk_index": chunk_index
                    }
                    chunks.append((current_chunk.strip(), chunk_info))
                    chunk_index += 1
                current_chunk = sentence
        
        if current_chunk:
            chunk_info = {
                **section_info,
                "sub_chunk_index": chunk_index
            }
            chunks.append((current_chunk.strip(), chunk_info))
        
        return chunks
    
    def _create_chunk_metadata(
        self,
        chunk_content: str,
        document_id: str,
        document_type: str,
        section_info: Dict[str, Any],
        chunk_index: int,
        total_chunks: int,
        content_analysis: Dict[str, Any]
    ) -> ChunkMetadata:
        """Create comprehensive metadata for a chunk"""
        
        # Generate unique chunk ID
        chunk_hash = hashlib.md5(chunk_content.encode()).hexdigest()[:8]
        chunk_id = f"{document_id}_{chunk_index}_{chunk_hash}"
        
        return ChunkMetadata(
            chunk_id=chunk_id,
            document_id=document_id,
            document_type=document_type,
            section_title=section_info.get("section_title"),
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            content_density=content_analysis["content_density"],
            contains_numbers=bool(re.search(r'\d+', chunk_content)),
            contains_dates=bool(re.search(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', chunk_content)),
            word_count=len(chunk_content.split()),
            char_count=len(chunk_content),
            created_at=datetime.utcnow().isoformat()
        )

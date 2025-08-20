"""
Adaptive embedding manager for the Support Quality Intelligence system.
Generates context-aware embeddings using OpenAI's text-embedding-3-large.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from openai import AsyncOpenAI
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation"""
    model: str
    preprocessing: str
    instruction_prefix: str
    normalize: bool
    batch_size: int


@dataclass
class EmbeddedChunk:
    """A document chunk with its embedding"""
    chunk_id: str
    content: str
    embedding: List[float]
    embedding_model: str
    preprocessing_applied: str
    metadata: Dict[str, Any]


class AdaptiveEmbeddingManager:
    """
    Advanced embedding manager that generates context-aware embeddings
    based on content type and characteristics.
    """
    
    def __init__(self):
        """Initialize the embedding manager"""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.embedding_model = settings.EMBEDDING_MODEL
        self.embedding_dimensions = settings.EMBEDDING_DIMENSIONS
        
        # Content type patterns for adaptive embedding
        self.content_patterns = {
            "factual_dense": ["₹", "cost", "fee", "price", "salary", "percentage", "%", "months", "weeks"],
            "narrative": ["story", "experience", "journey", "background", "overview"],
            "procedural": ["step", "process", "procedure", "how to", "guide", "instructions"],
            "policy": ["policy", "rule", "guideline", "requirement", "must", "should"]
        }
        
        logger.info(f"Adaptive embedding manager initialized with model: {self.embedding_model}")
    
    async def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[EmbeddedChunk]:
        """
        Generate embeddings for document chunks with adaptive strategies.
        
        Args:
            chunks: List of document chunks with content and metadata
            
        Returns:
            List of embedded chunks with embeddings and metadata
        """
        logger.info(f"Generating embeddings for {len(chunks)} chunks")
        
        embedded_chunks = []
        
        # Process chunks in batches for efficiency
        batch_size = 32
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            try:
                batch_embeddings = await self._embed_batch(batch)
                embedded_chunks.extend(batch_embeddings)
                
            except Exception as e:
                logger.error(f"Failed to embed batch {i//batch_size + 1}: {str(e)}")
                # Create fallback embeddings for failed batch
                for chunk in batch:
                    fallback_embedding = self._create_fallback_embedding()
                    embedded_chunks.append(EmbeddedChunk(
                        chunk_id=chunk.get("chunk_id", f"chunk_{i}"),
                        content=chunk["content"],
                        embedding=fallback_embedding,
                        embedding_model="fallback",
                        preprocessing_applied="none",
                        metadata=chunk.get("metadata", {})
                    ))
        
        logger.info(f"Successfully generated {len(embedded_chunks)} embeddings")
        return embedded_chunks
    
    async def _embed_batch(self, chunks: List[Dict[str, Any]]) -> List[EmbeddedChunk]:
        """Embed a batch of chunks"""
        
        # Prepare texts for embedding
        texts_to_embed = []
        chunk_configs = []
        
        for chunk in chunks:
            # Determine embedding configuration
            config = self._select_embedding_config(chunk)
            
            # Preprocess content
            processed_content = self._preprocess_for_embedding(chunk["content"], config)
            
            texts_to_embed.append(processed_content)
            chunk_configs.append(config)
        
        # Generate embeddings
        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=texts_to_embed,
            encoding_format="float"
        )
        
        # Create embedded chunks
        embedded_chunks = []
        for i, (chunk, config) in enumerate(zip(chunks, chunk_configs)):
            embedding = response.data[i].embedding
            
            # Normalize if required
            if config.normalize:
                embedding = self._normalize_embedding(embedding)
            
            embedded_chunks.append(EmbeddedChunk(
                chunk_id=chunk.get("chunk_id", f"chunk_{i}"),
                content=chunk["content"],
                embedding=embedding,
                embedding_model=self.embedding_model,
                preprocessing_applied=config.preprocessing,
                metadata=chunk.get("metadata", {})
            ))
        
        return embedded_chunks
    
    def _select_embedding_config(self, chunk: Dict[str, Any]) -> EmbeddingConfig:
        """Select optimal embedding configuration based on chunk characteristics"""
        
        content = chunk["content"]
        metadata = chunk.get("metadata", {})
        content_type = metadata.get("type", "unknown")
        
        # Determine content density
        content_density = self._analyze_content_density(content)
        
        # High-precision embedding for critical factual content
        if content_density == "factual_dense" or content_type in ["course_catalog", "fee_structure"]:
            return EmbeddingConfig(
                model=self.embedding_model,
                preprocessing="factual_enhancement",
                instruction_prefix="Represent this factual educational content for precise retrieval: ",
                normalize=True,
                batch_size=32
            )
        
        # Optimized embedding for narrative content
        elif content_density == "narrative" or content_type in ["instructor_profiles", "success_stories"]:
            return EmbeddingConfig(
                model=self.embedding_model,
                preprocessing="narrative_optimization",
                instruction_prefix="Represent this narrative content for semantic search: ",
                normalize=True,
                batch_size=32
            )
        
        # Policy and procedure embedding
        elif content_density == "policy" or content_type in ["assessment_policies", "support_guidelines"]:
            return EmbeddingConfig(
                model=self.embedding_model,
                preprocessing="policy_enhancement",
                instruction_prefix="Represent this policy content for compliance verification: ",
                normalize=True,
                batch_size=32
            )
        
        # Default configuration
        else:
            return EmbeddingConfig(
                model=self.embedding_model,
                preprocessing="standard",
                instruction_prefix="Represent this document for retrieval: ",
                normalize=True,
                batch_size=32
            )
    
    def _analyze_content_density(self, content: str) -> str:
        """Analyze content to determine its density type"""
        content_lower = content.lower()
        
        # Count factual indicators
        factual_count = sum(1 for pattern in self.content_patterns["factual_dense"] 
                          if pattern in content_lower)
        
        # Count narrative indicators
        narrative_count = sum(1 for pattern in self.content_patterns["narrative"] 
                            if pattern in content_lower)
        
        # Count policy indicators
        policy_count = sum(1 for pattern in self.content_patterns["policy"] 
                         if pattern in content_lower)
        
        # Determine dominant type
        if factual_count >= 2:
            return "factual_dense"
        elif policy_count >= 2:
            return "policy"
        elif narrative_count >= 1:
            return "narrative"
        else:
            return "mixed"
    
    def _preprocess_for_embedding(self, content: str, config: EmbeddingConfig) -> str:
        """Apply content-specific preprocessing before embedding"""
        
        processed_content = content.strip()
        
        if config.preprocessing == "factual_enhancement":
            # Enhance factual content by highlighting numbers and amounts
            processed_content = self._enhance_factual_content(processed_content)
            
        elif config.preprocessing == "narrative_optimization":
            # Clean and optimize narrative content
            processed_content = self._optimize_narrative_content(processed_content)
            
        elif config.preprocessing == "policy_enhancement":
            # Enhance policy content with structural markers
            processed_content = self._enhance_policy_content(processed_content)
        
        # Apply instruction prefix
        return f"{config.instruction_prefix}{processed_content}"
    
    def _enhance_factual_content(self, content: str) -> str:
        """Enhance factual content for better embedding"""
        # Add context markers for important factual elements
        import re
        
        # Highlight monetary amounts
        content = re.sub(r'₹([\d,]+)', r'AMOUNT: ₹\1', content)
        
        # Highlight percentages
        content = re.sub(r'(\d+)%', r'PERCENTAGE: \1%', content)
        
        # Highlight durations
        content = re.sub(r'(\d+)\s*(months?|weeks?|days?)', r'DURATION: \1 \2', content)
        
        return content
    
    def _optimize_narrative_content(self, content: str) -> str:
        """Optimize narrative content for embedding"""
        # Remove excessive whitespace and normalize
        import re
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        return content
    
    def _enhance_policy_content(self, content: str) -> str:
        """Enhance policy content with structural markers"""
        import re
        
        # Mark requirements
        content = re.sub(r'\b(must|required|mandatory)\b', r'REQUIREMENT: \1', content, flags=re.IGNORECASE)
        
        # Mark recommendations
        content = re.sub(r'\b(should|recommended|advised)\b', r'RECOMMENDATION: \1', content, flags=re.IGNORECASE)
        
        return content
    
    def _normalize_embedding(self, embedding: List[float]) -> List[float]:
        """Normalize embedding vector to unit length"""
        embedding_array = np.array(embedding)
        norm = np.linalg.norm(embedding_array)
        if norm > 0:
            return (embedding_array / norm).tolist()
        return embedding
    
    def _create_fallback_embedding(self) -> List[float]:
        """Create a fallback embedding when API calls fail"""
        # Return a random normalized vector of the correct dimension
        import random
        embedding = [random.gauss(0, 0.1) for _ in range(self.embedding_dimensions)]
        return self._normalize_embedding(embedding)
    
    async def embed_query(self, query: str, query_type: str = "general") -> List[float]:
        """
        Generate embedding for a search query.
        
        Args:
            query: Search query text
            query_type: Type of query (factual, narrative, policy, general)
            
        Returns:
            Query embedding vector
        """
        try:
            # Preprocess query based on type
            if query_type == "factual":
                processed_query = f"Find factual information about: {query}"
            elif query_type == "policy":
                processed_query = f"Find policy information about: {query}"
            elif query_type == "narrative":
                processed_query = f"Find narrative content about: {query}"
            else:
                processed_query = f"Find information about: {query}"
            
            # Generate embedding
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=[processed_query],
                encoding_format="float"
            )
            
            embedding = response.data[0].embedding
            return self._normalize_embedding(embedding)
            
        except Exception as e:
            logger.error(f"Failed to embed query '{query}': {str(e)}")
            return self._create_fallback_embedding()
    
    async def get_embedding_stats(self) -> Dict[str, Any]:
        """Get statistics about embedding operations"""
        return {
            "embedding_model": self.embedding_model,
            "embedding_dimensions": self.embedding_dimensions,
            "supported_content_types": list(self.content_patterns.keys()),
            "preprocessing_strategies": ["factual_enhancement", "narrative_optimization", "policy_enhancement", "standard"]
        }

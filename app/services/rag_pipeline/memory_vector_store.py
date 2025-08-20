"""
In-memory vector store for testing and development.
Provides the same interface as the Qdrant vector store but stores data in memory.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import uuid

from app.services.rag_pipeline.embedding_manager import EmbeddedChunk

logger = logging.getLogger(__name__)


@dataclass
class MemorySearchResult:
    """In-memory search result"""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any]


@dataclass
class MemorySearchParams:
    """Parameters for memory vector search"""
    limit: int = 20
    score_threshold: float = 0.7


class MemoryVectorStore:
    """
    In-memory vector store for testing and development.
    Provides basic vector similarity search without external dependencies.
    """
    
    def __init__(self):
        """Initialize the memory vector store"""
        self.collections = {}  # collection_name -> {points: [], metadata: {}}
        self.initialized = False
        
        logger.info("Memory vector store initialized")
    
    async def initialize(self):
        """Initialize collections"""
        if self.initialized:
            return
        
        # Create default collections
        collection_configs = {
            "factual_precise": {"optimization": "precision"},
            "guidelines_fast": {"optimization": "speed"},
            "contextual_knowledge": {"optimization": "balanced"}
        }
        
        for name, config in collection_configs.items():
            self.collections[name] = {
                "points": [],
                "metadata": config
            }
        
        self.initialized = True
        logger.info("Memory vector store collections initialized")
    
    async def upsert_chunks(self, chunks: List[EmbeddedChunk]) -> Dict[str, int]:
        """
        Upsert embedded chunks into appropriate collections.
        
        Args:
            chunks: List of embedded chunks to store
            
        Returns:
            Dictionary with collection names and count of chunks stored
        """
        await self.initialize()
        
        logger.info(f"Upserting {len(chunks)} chunks to memory vector store")
        
        upsert_counts = {}
        
        for chunk in chunks:
            # Determine target collection
            collection = self._determine_target_collection(chunk)
            
            # Create point
            point = {
                "id": chunk.chunk_id or str(uuid.uuid4()),
                "vector": np.array(chunk.embedding),
                "payload": {
                    "content": chunk.content,
                    "embedding_model": chunk.embedding_model,
                    "preprocessing_applied": chunk.preprocessing_applied,
                    **chunk.metadata
                }
            }
            
            # Add to collection
            if collection not in self.collections:
                self.collections[collection] = {"points": [], "metadata": {}}
            
            # Remove existing point with same ID
            self.collections[collection]["points"] = [
                p for p in self.collections[collection]["points"] if p["id"] != point["id"]
            ]
            
            # Add new point
            self.collections[collection]["points"].append(point)
            
            # Update count
            upsert_counts[collection] = upsert_counts.get(collection, 0) + 1
        
        logger.info(f"Upserted chunks: {upsert_counts}")
        return upsert_counts
    
    def _determine_target_collection(self, chunk: EmbeddedChunk) -> str:
        """Determine the best collection for a chunk based on its metadata"""
        
        document_type = chunk.metadata.get("document_type", "general")
        content_density = chunk.metadata.get("content_density", "mixed")
        
        # Route to factual_precise for numerical and factual content
        if (document_type in ["course_catalog", "fee_structure", "placement_data"] or 
            content_density == "factual_dense"):
            return "factual_precise"
        
        # Route to guidelines_fast for policies and procedures
        elif document_type in ["assessment_policies", "support_guidelines", "procedures"]:
            return "guidelines_fast"
        
        # Route to contextual_knowledge for everything else
        else:
            return "contextual_knowledge"
    
    async def search(
        self, 
        query_embedding: List[float], 
        collections: Optional[List[str]] = None,
        search_params: Optional[MemorySearchParams] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MemorySearchResult]:
        """
        Search for similar vectors across collections.
        
        Args:
            query_embedding: Query vector
            collections: List of collections to search (None for all)
            search_params: Search parameters
            filters: Metadata filters
            
        Returns:
            List of search results sorted by score
        """
        await self.initialize()
        
        if search_params is None:
            search_params = MemorySearchParams()
        
        if collections is None:
            collections = list(self.collections.keys())
        
        query_vector = np.array(query_embedding).reshape(1, -1)
        all_results = []
        
        # Search each collection
        for collection_name in collections:
            if collection_name not in self.collections:
                continue
            
            points = self.collections[collection_name]["points"]
            
            for point in points:
                # Apply filters if specified
                if filters and not self._matches_filters(point["payload"], filters):
                    continue
                
                # Calculate cosine similarity
                point_vector = point["vector"].reshape(1, -1)
                similarity = cosine_similarity(query_vector, point_vector)[0][0]
                
                # Apply score threshold
                if similarity >= search_params.score_threshold:
                    all_results.append(MemorySearchResult(
                        id=point["id"],
                        content=point["payload"].get("content", ""),
                        score=float(similarity),
                        metadata={
                            "collection": collection_name,
                            **{k: v for k, v in point["payload"].items() if k != "content"}
                        }
                    ))
        
        # Sort by score and return top results
        all_results.sort(key=lambda x: x.score, reverse=True)
        return all_results[:search_params.limit]
    
    def _matches_filters(self, payload: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if payload matches filters"""
        for field, value in filters.items():
            if field not in payload:
                return False
            
            if isinstance(value, list):
                if payload[field] not in value:
                    return False
            else:
                if payload[field] != value:
                    return False
        
        return True
    
    async def intelligent_collection_routing(self, query_analysis: Dict[str, Any]) -> List[str]:
        """
        Route queries to optimal collections based on query characteristics.
        
        Args:
            query_analysis: Analysis of the query (intent, entities, etc.)
            
        Returns:
            List of collection names to search
        """
        intent = query_analysis.get("intent", "general")
        entities = query_analysis.get("entities", [])
        query_type = query_analysis.get("query_type", "general")
        
        target_collections = []
        
        # Route based on query intent
        if intent == "factual_lookup" or any(entity in ["cost", "fee", "salary", "percentage"] for entity in entities):
            target_collections.append("factual_precise")
            
        if intent == "policy_check" or query_type == "compliance":
            target_collections.append("guidelines_fast")
            
        if intent == "general_info" or query_type == "narrative":
            target_collections.append("contextual_knowledge")
        
        # Default to all collections if no specific routing
        if not target_collections:
            target_collections = list(self.collections.keys())
        
        return target_collections
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about all collections"""
        await self.initialize()
        
        stats = {}
        for collection_name, collection_data in self.collections.items():
            points = collection_data["points"]
            stats[collection_name] = {
                "points_count": len(points),
                "vectors_count": len(points),
                "status": "green",
                "config": collection_data["metadata"]
            }
        
        return stats
    
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection"""
        if collection_name in self.collections:
            del self.collections[collection_name]
            logger.info(f"Deleted collection: {collection_name}")
            return True
        return False
    
    async def close(self):
        """Close the vector store connection"""
        logger.info("Memory vector store closed")

"""
Advanced vector store manager for the Support Quality Intelligence system.
Manages multiple collections with optimized configurations for different content types.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
try:
    from qdrant_client import AsyncQdrantClient
    from qdrant_client.models import (
        VectorParams, Distance, CollectionInfo, PointStruct,
        Filter, FieldCondition, MatchValue, SearchParams
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

import uuid

from app.config import settings
from app.services.rag_pipeline.embedding_manager import EmbeddedChunk
from app.services.rag_pipeline.memory_vector_store import MemoryVectorStore, MemorySearchParams

logger = logging.getLogger(__name__)


@dataclass
class CollectionConfig:
    """Configuration for a vector collection"""
    name: str
    embedding_model: str
    dimensions: int
    distance_metric: Distance
    index_config: Dict[str, Any]
    content_types: List[str]
    optimization_target: str
    metadata_indexes: List[str]


@dataclass
class SearchParams:
    """Parameters for vector search"""
    limit: int = 20
    score_threshold: float = 0.7
    ef: Optional[int] = None
    exact: bool = False


@dataclass
class SearchResult:
    """Vector search result"""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any]


class AdvancedVectorStoreManager:
    """
    Advanced vector store manager with multi-collection support
    and intelligent routing for different content types.
    """
    
    def __init__(self):
        """Initialize the vector store manager"""
        self.use_memory_store = not QDRANT_AVAILABLE

        if self.use_memory_store:
            logger.warning("Qdrant not available, using in-memory vector store")
            self.client = MemoryVectorStore()
        else:
            try:
                self.client = AsyncQdrantClient(
                    host=settings.VECTOR_STORE_HOST,
                    port=settings.VECTOR_STORE_PORT,
                    api_key=settings.VECTOR_STORE_API_KEY
                )
            except Exception as e:
                logger.warning(f"Failed to connect to Qdrant, using memory store: {str(e)}")
                self.use_memory_store = True
                self.client = MemoryVectorStore()

        self.collections = self._setup_collections()
        self.initialized = False

        store_type = "memory" if self.use_memory_store else "qdrant"
        logger.info(f"Advanced vector store manager initialized with {store_type} backend")
    
    def _setup_collections(self) -> Dict[str, CollectionConfig]:
        """Setup optimized collections based on content characteristics"""
        
        return {
            # High-precision factual data
            "factual_precise": CollectionConfig(
                name="factual_precise",
                embedding_model=settings.EMBEDDING_MODEL,
                dimensions=settings.EMBEDDING_DIMENSIONS,
                distance_metric=Distance.COSINE,
                index_config={
                    "m": 32,           # Higher connectivity for precision
                    "ef_construct": 400, # More thorough construction
                    "ef": 200          # Higher search quality
                },
                content_types=["course_catalog", "fee_structure", "placement_data"],
                optimization_target="precision",
                metadata_indexes=["document_type", "last_updated", "content_density", "contains_numbers"]
            ),
            
            # Fast retrieval for guidelines and policies
            "guidelines_fast": CollectionConfig(
                name="guidelines_fast", 
                embedding_model=settings.EMBEDDING_MODEL,
                dimensions=settings.EMBEDDING_DIMENSIONS,
                distance_metric=Distance.COSINE,
                index_config={
                    "m": 16,           # Lower connectivity for speed
                    "ef_construct": 200,
                    "ef": 128          # Faster search
                },
                content_types=["assessment_policies", "support_guidelines", "procedures"],
                optimization_target="speed",
                metadata_indexes=["document_type", "policy_type", "compliance_level"]
            ),
            
            # Contextual knowledge and narratives
            "contextual_knowledge": CollectionConfig(
                name="contextual_knowledge",
                embedding_model=settings.EMBEDDING_MODEL, 
                dimensions=settings.EMBEDDING_DIMENSIONS,
                distance_metric=Distance.COSINE,
                index_config={
                    "m": 24,           # Balanced configuration
                    "ef_construct": 300,
                    "ef": 150
                },
                content_types=["instructor_profiles", "success_stories", "general_info"],
                optimization_target="balanced",
                metadata_indexes=["document_type", "content_category", "narrative_type"]
            )
        }
    
    async def initialize(self):
        """Initialize collections if they don't exist"""
        if self.initialized:
            return

        logger.info("Initializing vector store collections")

        try:
            if self.use_memory_store:
                # Memory store initialization
                await self.client.initialize()
            else:
                # Qdrant initialization
                existing_collections = await self.client.get_collections()
                existing_names = {col.name for col in existing_collections.collections}

                # Create missing collections
                for collection_name, config in self.collections.items():
                    if collection_name not in existing_names:
                        await self._create_collection(config)
                        logger.info(f"Created collection: {collection_name}")
                    else:
                        logger.info(f"Collection already exists: {collection_name}")

            self.initialized = True
            logger.info("Vector store initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize vector store: {str(e)}")
            # Fallback to memory store
            if not self.use_memory_store:
                logger.warning("Falling back to memory vector store")
                self.use_memory_store = True
                self.client = MemoryVectorStore()
                await self.client.initialize()
                self.initialized = True
            else:
                raise
    
    async def _create_collection(self, config: CollectionConfig):
        """Create a new collection with the specified configuration"""
        
        vector_params = VectorParams(
            size=config.dimensions,
            distance=config.distance_metric
        )
        
        await self.client.create_collection(
            collection_name=config.name,
            vectors_config=vector_params
        )
        
        # Create indexes for metadata fields
        for field in config.metadata_indexes:
            try:
                await self.client.create_payload_index(
                    collection_name=config.name,
                    field_name=field,
                    field_schema="keyword"  # Default to keyword index
                )
            except Exception as e:
                logger.warning(f"Failed to create index for {field} in {config.name}: {str(e)}")
    
    async def upsert_chunks(self, chunks: List[EmbeddedChunk]) -> Dict[str, int]:
        """
        Upsert embedded chunks into appropriate collections.

        Args:
            chunks: List of embedded chunks to store

        Returns:
            Dictionary with collection names and count of chunks stored
        """
        await self.initialize()

        logger.info(f"Upserting {len(chunks)} chunks to vector store")

        if self.use_memory_store:
            # Use memory store upsert
            return await self.client.upsert_chunks(chunks)
        else:
            # Use Qdrant upsert
            # Group chunks by target collection
            collection_chunks = {}
            for chunk in chunks:
                collection = self._determine_target_collection(chunk)
                if collection not in collection_chunks:
                    collection_chunks[collection] = []
                collection_chunks[collection].append(chunk)

            # Upsert to each collection
            upsert_counts = {}
            for collection_name, chunk_list in collection_chunks.items():
                try:
                    points = self._prepare_points(chunk_list)

                    await self.client.upsert(
                        collection_name=collection_name,
                        points=points
                    )

                    upsert_counts[collection_name] = len(chunk_list)
                    logger.info(f"Upserted {len(chunk_list)} chunks to {collection_name}")

                except Exception as e:
                    logger.error(f"Failed to upsert to {collection_name}: {str(e)}")
                    upsert_counts[collection_name] = 0

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
    
    def _prepare_points(self, chunks: List[EmbeddedChunk]) -> List[PointStruct]:
        """Prepare chunks as Qdrant points"""
        
        points = []
        for chunk in chunks:
            # Generate unique ID if not provided
            point_id = chunk.chunk_id or str(uuid.uuid4())
            
            # Prepare payload with metadata
            payload = {
                "content": chunk.content,
                "embedding_model": chunk.embedding_model,
                "preprocessing_applied": chunk.preprocessing_applied,
                **chunk.metadata
            }
            
            points.append(PointStruct(
                id=point_id,
                vector=chunk.embedding,
                payload=payload
            ))
        
        return points
    
    async def search(
        self,
        query_embedding: List[float],
        collections: Optional[List[str]] = None,
        search_params: Optional[SearchParams] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
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
            search_params = SearchParams()

        if collections is None:
            collections = list(self.collections.keys())

        if self.use_memory_store:
            # Use memory store search
            memory_params = MemorySearchParams(
                limit=search_params.limit,
                score_threshold=search_params.score_threshold
            )

            memory_results = await self.client.search(
                query_embedding=query_embedding,
                collections=collections,
                search_params=memory_params,
                filters=filters
            )

            # Convert to SearchResult objects
            return [SearchResult(
                id=result.id,
                content=result.content,
                score=result.score,
                metadata=result.metadata
            ) for result in memory_results]

        else:
            # Use Qdrant search
            all_results = []
            for collection_name in collections:
                try:
                    # Prepare search parameters
                    qdrant_search_params = SearchParams(
                        hnsw_ef=search_params.ef or self.collections[collection_name].index_config["ef"],
                        exact=search_params.exact
                    )

                    # Prepare filters
                    qdrant_filter = self._prepare_filter(filters) if filters else None

                    # Perform search
                    results = await self.client.search(
                        collection_name=collection_name,
                        query_vector=query_embedding,
                        limit=search_params.limit,
                        score_threshold=search_params.score_threshold,
                        search_params=qdrant_search_params,
                        query_filter=qdrant_filter
                    )

                    # Convert to SearchResult objects
                    for result in results:
                        all_results.append(SearchResult(
                            id=str(result.id),
                            content=result.payload.get("content", ""),
                            score=result.score,
                            metadata={
                                "collection": collection_name,
                                **{k: v for k, v in result.payload.items() if k != "content"}
                            }
                        ))

                except Exception as e:
                    logger.error(f"Search failed in collection {collection_name}: {str(e)}")

            # Sort by score and return top results
            all_results.sort(key=lambda x: x.score, reverse=True)
            return all_results[:search_params.limit]
    
    def _prepare_filter(self, filters: Dict[str, Any]) -> Filter:
        """Prepare Qdrant filter from dictionary"""
        
        conditions = []
        for field, value in filters.items():
            if isinstance(value, list):
                # Multiple values - use should condition
                for v in value:
                    conditions.append(FieldCondition(
                        key=field,
                        match=MatchValue(value=v)
                    ))
            else:
                # Single value
                conditions.append(FieldCondition(
                    key=field,
                    match=MatchValue(value=value)
                ))
        
        return Filter(should=conditions) if len(conditions) > 1 else Filter(must=[conditions[0]])
    
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
        for collection_name in self.collections.keys():
            try:
                info = await self.client.get_collection(collection_name)
                stats[collection_name] = {
                    "points_count": info.points_count,
                    "vectors_count": info.vectors_count,
                    "status": info.status,
                    "config": self.collections[collection_name].__dict__
                }
            except Exception as e:
                logger.error(f"Failed to get stats for {collection_name}: {str(e)}")
                stats[collection_name] = {"error": str(e)}
        
        return stats
    
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection"""
        try:
            await self.client.delete_collection(collection_name)
            logger.info(f"Deleted collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {str(e)}")
            return False
    
    async def close(self):
        """Close the vector store connection"""
        if hasattr(self.client, 'close'):
            await self.client.close()
        logger.info("Vector store connection closed")

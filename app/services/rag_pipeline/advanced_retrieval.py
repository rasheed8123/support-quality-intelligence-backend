"""
Advanced retrieval engine for the Support Quality Intelligence system.
Multi-stage retrieval with query expansion, semantic reranking, and diversity optimization.
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from openai import AsyncOpenAI

from app.config import settings
from app.services.rag_pipeline.embedding_manager import AdaptiveEmbeddingManager
from app.services.rag_pipeline.vector_store import AdvancedVectorStoreManager, SearchParams, SearchResult
from app.services.rag_pipeline.claim_extraction import Claim
from app.api.models import Evidence

logger = logging.getLogger(__name__)


@dataclass
class QueryAnalysis:
    """Analysis of a search query"""
    intent: str  # factual_lookup, guideline_check, compliance_verification, contextual_info
    complexity: str  # low, medium, high
    precision_required: str  # low, medium, high
    urgency: str  # low, medium, high
    temporal_sensitivity: str  # none, recent, specific_date
    entity_types: List[str]
    expected_answer_type: str  # specific_fact, explanation, procedure, comparison
    scope: str  # narrow, broad, comprehensive
    contains_temporal_elements: bool


@dataclass
class RetrievalResult:
    """Enhanced retrieval result with multiple scores"""
    content: str
    metadata: Dict[str, Any]
    vector_score: float
    rerank_score: Optional[float] = None
    combined_score: Optional[float] = None
    source_collection: str = ""
    query_variation: str = ""


class AdvancedRetrievalEngine:
    """
    Multi-stage intelligent retrieval engine with query expansion,
    semantic reranking, and diversity optimization.
    """
    
    def __init__(self):
        """Initialize the advanced retrieval engine"""
        self.embedding_manager = AdaptiveEmbeddingManager()
        self.vector_store = AdvancedVectorStoreManager()
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.query_analyzer = settings.QUERY_EXPANSION_MODEL
        self.reranker = settings.RERANKING_MODEL
        
        logger.info("Advanced retrieval engine initialized")
    
    async def retrieve_evidence_for_claims(
        self, 
        claims: List[Claim],
        max_evidence_per_claim: int = 5
    ) -> Dict[str, List[Evidence]]:
        """
        Retrieve evidence for all claims using advanced multi-stage retrieval.
        
        Args:
            claims: List of claims to find evidence for
            max_evidence_per_claim: Maximum evidence items per claim
            
        Returns:
            Dictionary mapping claim text to evidence list
        """
        logger.info(f"Advanced retrieval for {len(claims)} claims")
        
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
        """Multi-stage retrieval for a single claim"""
        
        # Stage 1: Query Analysis and Expansion
        query_analysis = await self._analyze_query_deeply(claim)
        expanded_queries = await self._expand_query(claim, query_analysis)
        
        # Stage 2: Multi-Collection Retrieval
        raw_results = await self._multi_collection_retrieval(expanded_queries, query_analysis)
        
        # Stage 3: Metadata Filtering
        filtered_results = await self._apply_intelligent_filtering(raw_results, query_analysis)
        
        # Stage 4: Semantic Reranking
        reranked_results = await self._semantic_reranking(filtered_results, claim, query_analysis)
        
        # Stage 5: Diversity and Quality Optimization
        final_results = await self._optimize_result_diversity(reranked_results, query_analysis)
        
        # Convert to Evidence objects
        evidence_list = []
        for result in final_results[:max_evidence]:
            evidence = Evidence(
                source=self._format_source_name(result.metadata),
                content=result.content,
                relevance_score=result.combined_score or result.vector_score,
                document_type=result.metadata.get("document_type", "unknown"),
                last_updated=result.metadata.get("created_at")
            )
            evidence_list.append(evidence)
        
        return evidence_list
    
    async def _analyze_query_deeply(self, claim: Claim) -> QueryAnalysis:
        """Deep analysis of claim characteristics for retrieval optimization"""
        
        analysis_prompt = f"""
        Analyze this claim for a support response verification system:
        
        Claim: "{claim.text}"
        Claim Type: {claim.claim_type}
        Priority: {claim.verification_priority}
        Entities: {claim.entities}
        
        Identify:
        1. Intent type: factual_lookup, guideline_check, compliance_verification, contextual_info
        2. Complexity level: low, medium, high
        3. Precision requirements: low, medium, high
        4. Urgency level: low, medium, high
        5. Temporal sensitivity: none, recent, specific_date
        6. Entity types: numbers, dates, names, policies, procedures
        7. Expected answer type: specific_fact, explanation, procedure, comparison
        8. Scope: narrow, broad, comprehensive
        
        Return JSON with these fields.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.query_analyzer,
                messages=[
                    {"role": "system", "content": "You are a query analysis expert. Return only valid JSON."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.1,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return QueryAnalysis(
                intent=result.get("intent", "factual_lookup"),
                complexity=result.get("complexity", "medium"),
                precision_required=result.get("precision_requirements", "medium"),
                urgency=result.get("urgency_level", "medium"),
                temporal_sensitivity=result.get("temporal_sensitivity", "none"),
                entity_types=result.get("entity_types", []),
                expected_answer_type=result.get("expected_answer_type", "specific_fact"),
                scope=result.get("scope", "narrow"),
                contains_temporal_elements=result.get("temporal_sensitivity", "none") != "none"
            )
            
        except Exception as e:
            logger.error(f"Query analysis failed: {str(e)}")
            # Return default analysis
            return QueryAnalysis(
                intent="factual_lookup",
                complexity="medium",
                precision_required="medium",
                urgency="medium",
                temporal_sensitivity="none",
                entity_types=claim.entities,
                expected_answer_type="specific_fact",
                scope="narrow",
                contains_temporal_elements=False
            )
    
    async def _expand_query(self, claim: Claim, analysis: QueryAnalysis) -> List[str]:
        """Generate diverse query variations for comprehensive retrieval"""
        
        expansion_prompt = f"""
        Generate 3-5 diverse search queries to find evidence for this claim:
        
        Original Claim: "{claim.text}"
        Intent: {analysis.intent}
        Entities: {claim.entities}
        
        Generate queries that:
        1. Search for direct factual confirmation
        2. Look for related policy/guideline information  
        3. Find contextual supporting information
        4. Search for potential contradictory information
        5. Use different phrasings and synonyms
        
        Return JSON with "queries" array.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.query_analyzer,
                messages=[
                    {"role": "system", "content": "Generate diverse search queries. Return only valid JSON."},
                    {"role": "user", "content": expansion_prompt}
                ],
                temperature=0.3,
                max_tokens=400,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            queries = result.get("queries", [claim.text])
            
            # Ensure original claim is included
            if claim.text not in queries:
                queries.insert(0, claim.text)
            
            return queries[:5]  # Limit to 5 queries
            
        except Exception as e:
            logger.error(f"Query expansion failed: {str(e)}")
            return [claim.text]  # Fallback to original claim
    
    async def _multi_collection_retrieval(
        self, 
        queries: List[str], 
        analysis: QueryAnalysis
    ) -> List[RetrievalResult]:
        """Retrieve from multiple collections with query-specific optimization"""
        
        # Route to appropriate collections
        target_collections = await self.vector_store.intelligent_collection_routing({
            "intent": analysis.intent,
            "entities": analysis.entity_types,
            "query_type": analysis.expected_answer_type
        })
        
        all_results = []
        
        for collection in target_collections:
            for query_text in queries:
                try:
                    # Generate query embedding
                    query_type = self._determine_query_type(analysis.intent)
                    query_embedding = await self.embedding_manager.embed_query(query_text, query_type)
                    
                    # Adaptive search parameters
                    search_params = self._get_adaptive_search_params(analysis, collection)
                    
                    # Perform search
                    results = await self.vector_store.search(
                        query_embedding=query_embedding,
                        collections=[collection],
                        search_params=search_params
                    )
                    
                    # Convert to RetrievalResult objects
                    for result in results:
                        all_results.append(RetrievalResult(
                            content=result.content,
                            metadata=result.metadata,
                            vector_score=result.score,
                            source_collection=collection,
                            query_variation=query_text
                        ))
                        
                except Exception as e:
                    logger.error(f"Search failed for query '{query_text}' in {collection}: {str(e)}")
        
        return all_results
    
    def _determine_query_type(self, intent: str) -> str:
        """Map intent to query type for embedding"""
        mapping = {
            "factual_lookup": "factual",
            "guideline_check": "policy",
            "compliance_verification": "policy",
            "contextual_info": "narrative"
        }
        return mapping.get(intent, "general")
    
    def _get_adaptive_search_params(self, analysis: QueryAnalysis, collection: str) -> SearchParams:
        """Get adaptive search parameters based on query analysis"""
        
        base_params = SearchParams(limit=15, score_threshold=0.6)
        
        # Adjust for precision requirements
        if analysis.precision_required == "high":
            base_params.score_threshold = 0.8
            base_params.limit = 20
        elif analysis.precision_required == "low":
            base_params.score_threshold = 0.5
            base_params.limit = 10
        
        # Adjust for complexity
        if analysis.complexity == "high":
            base_params.limit = 25
        elif analysis.complexity == "low":
            base_params.limit = 10
        
        return base_params
    
    async def _apply_intelligent_filtering(
        self, 
        results: List[RetrievalResult], 
        analysis: QueryAnalysis
    ) -> List[RetrievalResult]:
        """Apply context-aware filtering based on query analysis"""
        
        filtered_results = []
        
        for result in results:
            # Temporal filtering
            if analysis.temporal_sensitivity != "none":
                if not self._passes_temporal_filter(result, analysis):
                    continue
            
            # Content type filtering
            if analysis.intent == "factual_lookup":
                if result.metadata.get("content_density") == "narrative":
                    result.vector_score *= 0.8  # Reduce score but don't eliminate
            
            # Quality threshold filtering
            relevance_threshold = self._calculate_dynamic_threshold(analysis)
            if result.vector_score >= relevance_threshold:
                filtered_results.append(result)
        
        return filtered_results
    
    def _passes_temporal_filter(self, result: RetrievalResult, analysis: QueryAnalysis) -> bool:
        """Check if result passes temporal filtering"""
        # Simplified temporal filtering - can be enhanced
        return True  # For now, pass all results
    
    def _calculate_dynamic_threshold(self, analysis: QueryAnalysis) -> float:
        """Calculate dynamic relevance threshold"""
        base_threshold = 0.6
        
        if analysis.precision_required == "high":
            return base_threshold + 0.2
        elif analysis.precision_required == "low":
            return base_threshold - 0.1
        
        return base_threshold
    
    async def _semantic_reranking(
        self, 
        results: List[RetrievalResult], 
        claim: Claim,
        analysis: QueryAnalysis
    ) -> List[RetrievalResult]:
        """Advanced semantic reranking with context awareness"""
        
        if len(results) <= 5:
            return results  # Skip reranking for small result sets
        
        rerank_prompt = f"""
        Rerank these search results for relevance to the claim:
        
        Claim: "{claim.text}"
        Claim Type: {claim.claim_type}
        Intent: {analysis.intent}
        
        Rate each result 0.0-1.0 for relevance to verifying this claim.
        Consider factual accuracy, completeness, and authority.
        
        Results:
        """
        
        # Prepare results for reranking
        result_texts = []
        for i, result in enumerate(results[:10]):  # Limit to top 10 for reranking
            result_texts.append(f"{i+1}. {result.content[:300]}...")
        
        try:
            response = await self.client.chat.completions.create(
                model=self.reranker,
                messages=[
                    {"role": "system", "content": "You are a relevance scoring expert. Return JSON with scores array."},
                    {"role": "user", "content": rerank_prompt + "\n".join(result_texts)}
                ],
                temperature=0.1,
                max_tokens=300,
                response_format={"type": "json_object"}
            )
            
            rerank_result = json.loads(response.choices[0].message.content)
            scores = rerank_result.get("scores", [0.5] * len(result_texts))
            
            # Apply rerank scores
            for i, score in enumerate(scores):
                if i < len(results):
                    results[i].rerank_score = float(score)
                    results[i].combined_score = self._combine_scores(
                        results[i].vector_score, float(score), analysis
                    )
            
            # Sort by combined score
            return sorted(results, key=lambda x: x.combined_score or x.vector_score, reverse=True)
            
        except Exception as e:
            logger.error(f"Semantic reranking failed: {str(e)}")
            return results
    
    def _combine_scores(self, vector_score: float, rerank_score: float, analysis: QueryAnalysis) -> float:
        """Intelligently combine vector and rerank scores"""
        
        # Default weights
        vector_weight = 0.4
        rerank_weight = 0.6
        
        # Adjust weights based on query analysis
        if analysis.intent == "factual_lookup":
            vector_weight = 0.5  # Vector similarity important for facts
            rerank_weight = 0.5
        elif analysis.precision_required == "high":
            rerank_weight = 0.8  # Trust semantic reranking more
            vector_weight = 0.2
        
        return (vector_score * vector_weight) + (rerank_score * rerank_weight)
    
    async def _optimize_result_diversity(
        self, 
        results: List[RetrievalResult], 
        analysis: QueryAnalysis
    ) -> List[RetrievalResult]:
        """Ensure diverse, high-quality results"""
        
        if len(results) <= 8:
            return results
        
        optimized_results = []
        seen_content_hashes = set()
        source_type_counts = {}
        
        for result in results:
            # Deduplication
            content_hash = hash(result.content[:200])
            if content_hash in seen_content_hashes:
                continue
            
            # Diversity enforcement
            source_type = result.metadata.get("document_type", "unknown")
            current_count = source_type_counts.get(source_type, 0)
            
            # Limit results per source type
            max_per_type = 3 if analysis.scope == "narrow" else 2
            if current_count >= max_per_type:
                continue
            
            # Quality threshold
            min_quality_score = 0.6 if analysis.precision_required == "high" else 0.4
            final_score = result.combined_score or result.vector_score
            if final_score < min_quality_score:
                continue
            
            optimized_results.append(result)
            seen_content_hashes.add(content_hash)
            source_type_counts[source_type] = current_count + 1
            
            # Limit total results
            if len(optimized_results) >= 10:
                break
        
        return optimized_results
    
    def _format_source_name(self, metadata: Dict[str, Any]) -> str:
        """Format source name for display"""
        document_type = metadata.get("document_type", "unknown")
        section_title = metadata.get("section_title", "")
        
        if section_title:
            return f"{document_type} - {section_title}"
        return document_type

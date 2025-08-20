"""
Document processing pipeline for the Support Quality Intelligence system.
Handles document ingestion, chunking, embedding, and vector store updates.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import hashlib
from datetime import datetime

from app.services.rag_pipeline.adaptive_chunking import AdaptiveChunker
from app.services.rag_pipeline.embedding_manager import AdaptiveEmbeddingManager
from app.services.rag_pipeline.vector_store import AdvancedVectorStoreManager
from app.config import settings

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Complete document processing pipeline that handles the full workflow
    from raw documents to searchable vector embeddings.
    """
    
    def __init__(self):
        """Initialize the document processor"""
        self.chunker = AdaptiveChunker()
        self.embedding_manager = AdaptiveEmbeddingManager()
        self.vector_store = AdvancedVectorStoreManager()
        
        self.data_folder = Path("data")
        self.processed_documents = {}  # Track processed documents
        
        logger.info("Document processor initialized")
    
    async def initialize(self):
        """Initialize all components"""
        await self.vector_store.initialize()
        logger.info("Document processor ready")
    
    async def process_all_documents(self) -> Dict[str, Any]:
        """
        Process all documents in the data folder.
        
        Returns:
            Processing statistics and results
        """
        logger.info("Starting full document processing")
        
        await self.initialize()
        
        if not self.data_folder.exists():
            logger.warning(f"Data folder not found: {self.data_folder}")
            return {"error": "Data folder not found", "processed": 0}
        
        # Find all markdown files
        document_files = list(self.data_folder.rglob("*.md"))
        logger.info(f"Found {len(document_files)} documents to process")
        
        processing_stats = {
            "total_documents": len(document_files),
            "processed_successfully": 0,
            "failed_documents": [],
            "total_chunks": 0,
            "total_embeddings": 0,
            "collections_updated": {},
            "processing_time_seconds": 0
        }
        
        start_time = datetime.now()
        
        # Process each document
        for doc_path in document_files:
            try:
                result = await self.process_single_document(doc_path)
                
                if result["success"]:
                    processing_stats["processed_successfully"] += 1
                    processing_stats["total_chunks"] += result["chunks_created"]
                    processing_stats["total_embeddings"] += result["embeddings_created"]
                    
                    # Update collection stats
                    for collection, count in result["collections_updated"].items():
                        processing_stats["collections_updated"][collection] = (
                            processing_stats["collections_updated"].get(collection, 0) + count
                        )
                else:
                    processing_stats["failed_documents"].append({
                        "file": str(doc_path),
                        "error": result["error"]
                    })
                    
            except Exception as e:
                logger.error(f"Failed to process document {doc_path}: {str(e)}")
                processing_stats["failed_documents"].append({
                    "file": str(doc_path),
                    "error": str(e)
                })
        
        processing_stats["processing_time_seconds"] = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Document processing complete: {processing_stats}")
        return processing_stats
    
    async def process_single_document(self, file_path: Path) -> Dict[str, Any]:
        """
        Process a single document through the complete pipeline.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Processing result with statistics
        """
        logger.info(f"Processing document: {file_path}")
        
        try:
            # Read document content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                return {"success": False, "error": "Empty document"}
            
            # Generate document ID and metadata
            document_id = self._generate_document_id(file_path)
            document_type = self._classify_document_type(file_path.name, content)
            
            document_metadata = {
                "file_path": str(file_path),
                "file_name": file_path.name,
                "document_type": document_type,
                "file_size": len(content),
                "last_modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                "processed_at": datetime.utcnow().isoformat()
            }
            
            # Step 1: Adaptive Chunking
            chunks = await self.chunker.chunk_document(
                content=content,
                document_id=document_id,
                document_type=document_type,
                metadata=document_metadata
            )
            
            if not chunks:
                return {"success": False, "error": "No chunks created"}
            
            logger.info(f"Created {len(chunks)} chunks for {file_path.name}")
            
            # Step 2: Generate Embeddings
            chunk_data = []
            for chunk in chunks:
                chunk_data.append({
                    "chunk_id": chunk.metadata.chunk_id,
                    "content": chunk.content,
                    "metadata": {
                        **chunk.metadata.__dict__,
                        **document_metadata
                    }
                })
            
            embedded_chunks = await self.embedding_manager.embed_chunks(chunk_data)
            logger.info(f"Generated {len(embedded_chunks)} embeddings for {file_path.name}")
            
            # Step 3: Store in Vector Database
            upsert_results = await self.vector_store.upsert_chunks(embedded_chunks)
            
            # Track processed document
            self.processed_documents[document_id] = {
                "file_path": str(file_path),
                "document_type": document_type,
                "chunks_count": len(chunks),
                "processed_at": datetime.utcnow().isoformat()
            }
            
            return {
                "success": True,
                "document_id": document_id,
                "document_type": document_type,
                "chunks_created": len(chunks),
                "embeddings_created": len(embedded_chunks),
                "collections_updated": upsert_results
            }
            
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _generate_document_id(self, file_path: Path) -> str:
        """Generate unique document ID"""
        # Use file path hash for consistent IDs
        path_str = str(file_path.resolve())
        return hashlib.md5(path_str.encode()).hexdigest()[:12]
    
    def _classify_document_type(self, filename: str, content: str) -> str:
        """Classify document type based on filename and content"""
        
        filename_lower = filename.lower()
        content_lower = content.lower()
        
        # Document type patterns
        type_patterns = {
            "course_catalog": ["course", "program", "curriculum", "catalog"],
            "fee_structure": ["fee", "cost", "price", "payment", "tuition"],
            "placement_data": ["placement", "job", "hiring", "company", "salary"],
            "assessment_policies": ["assessment", "exam", "grading", "evaluation", "policy"],
            "instructor_profiles": ["instructor", "faculty", "teacher", "profile"],
            "support_guidelines": ["support", "help", "guideline", "procedure"]
        }
        
        # Check filename first
        for doc_type, keywords in type_patterns.items():
            if any(keyword in filename_lower for keyword in keywords):
                return doc_type
        
        # Check content
        for doc_type, keywords in type_patterns.items():
            content_sample = content_lower[:500]
            keyword_matches = sum(1 for keyword in keywords if keyword in content_sample)
            if keyword_matches >= 2:
                return doc_type
        
        return "general"
    
    async def process_document_change(self, file_path: str, change_type: str) -> Dict[str, Any]:
        """
        Process document changes from Google Drive webhook.
        
        Args:
            file_path: Path to the changed document
            change_type: Type of change (created, updated, deleted)
            
        Returns:
            Processing result
        """
        logger.info(f"Processing document change: {file_path} ({change_type})")
        
        try:
            path_obj = Path(file_path)
            
            if change_type == "deleted":
                return await self._handle_document_deletion(path_obj)
            elif change_type in ["created", "updated"]:
                return await self.process_single_document(path_obj)
            else:
                return {"success": False, "error": f"Unknown change type: {change_type}"}
                
        except Exception as e:
            logger.error(f"Failed to process document change: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _handle_document_deletion(self, file_path: Path) -> Dict[str, Any]:
        """Handle document deletion"""
        
        document_id = self._generate_document_id(file_path)
        
        # Remove from tracking
        if document_id in self.processed_documents:
            del self.processed_documents[document_id]
        
        # Note: In a production system, you would also remove the chunks
        # from the vector database. This requires implementing deletion
        # functionality in the vector store.
        
        logger.info(f"Handled deletion of document: {file_path}")
        return {
            "success": True,
            "action": "deleted",
            "document_id": document_id
        }
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get comprehensive processing statistics"""
        
        # Get vector store stats
        vector_stats = await self.vector_store.get_collection_stats()
        
        # Get embedding stats
        embedding_stats = await self.embedding_manager.get_embedding_stats()
        
        return {
            "processed_documents": len(self.processed_documents),
            "document_details": self.processed_documents,
            "vector_store_stats": vector_stats,
            "embedding_stats": embedding_stats,
            "data_folder": str(self.data_folder),
            "last_updated": datetime.utcnow().isoformat()
        }
    
    async def reprocess_all_documents(self) -> Dict[str, Any]:
        """
        Reprocess all documents (useful for updates to processing logic).
        
        Returns:
            Reprocessing results
        """
        logger.info("Starting full document reprocessing")
        
        # Clear processed documents tracking
        self.processed_documents = {}
        
        # Note: In production, you might want to clear vector store collections
        # before reprocessing to avoid duplicates
        
        return await self.process_all_documents()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of document processing pipeline"""
        
        try:
            # Check data folder
            data_folder_exists = self.data_folder.exists()
            document_count = len(list(self.data_folder.rglob("*.md"))) if data_folder_exists else 0
            
            # Check vector store
            vector_store_healthy = True
            try:
                await self.vector_store.get_collection_stats()
            except Exception:
                vector_store_healthy = False
            
            return {
                "status": "healthy" if data_folder_exists and vector_store_healthy else "degraded",
                "data_folder_exists": data_folder_exists,
                "document_count": document_count,
                "processed_documents": len(self.processed_documents),
                "vector_store_healthy": vector_store_healthy,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

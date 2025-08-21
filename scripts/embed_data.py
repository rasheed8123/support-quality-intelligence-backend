#!/usr/bin/env python3
"""
Data embedding script for Qdrant vector store.
Processes documents from /data folder and embeds them into Qdrant collections.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import List, Dict, Any
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.config import settings
from app.services.rag_pipeline.document_processor import DocumentProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataEmbedder:
    """Simplified data embedder using the complete DocumentProcessor pipeline"""

    def __init__(self):
        self.document_processor = None

    async def initialize(self):
        """Initialize document processor"""
        logger.info("🚀 Initializing data embedding components...")

        try:
            # Initialize document processor (handles everything internally)
            self.document_processor = DocumentProcessor()
            logger.info("✅ Document processor initialized")

            return True

        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            return False
    
    async def process_documents(self) -> Dict[str, Any]:
        """Process all documents using the complete pipeline"""
        logger.info("📊 Processing all documents in data folder...")

        try:
            # Use the document processor's built-in method to process all documents
            results = await self.document_processor.process_all_documents()
            return results

        except Exception as e:
            logger.error(f"❌ Failed to process documents: {e}")
            return {}
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics from document processor"""
        try:
            return await self.document_processor.get_processing_stats()
        except Exception as e:
            logger.error(f"❌ Failed to get processing stats: {e}")
            return {}
    



async def main():
    """Main embedding function"""
    print("🔢 Data Embedding for Qdrant Vector Store")
    print("=" * 50)
    
    embedder = DataEmbedder()
    
    # Initialize components
    if not await embedder.initialize():
        print("❌ Failed to initialize components")
        return False
    
    # Process documents
    print("\n📊 Processing documents...")
    results = await embedder.process_documents()

    # Display results
    print("\n📈 Embedding Results:")
    print("-" * 30)

    if results and isinstance(results, dict):
        total_documents = results.get("total_documents", 0)
        processed_successfully = results.get("processed_successfully", 0)
        total_chunks = results.get("total_chunks", 0)
        total_embeddings = results.get("total_embeddings", 0)
        collections_updated = results.get("collections_updated", {})
        processing_time = results.get("processing_time_seconds", 0)

        print(f"📄 Documents processed: {processed_successfully}/{total_documents}")
        print(f"📝 Total chunks created: {total_chunks}")
        print(f"🔢 Total embeddings generated: {total_embeddings}")
        print(f"⏱️  Processing time: {processing_time:.2f} seconds")

        print(f"\n📊 Collections Updated:")
        print("-" * 25)
        for collection, count in collections_updated.items():
            status = "✅" if count > 0 else "❌"
            print(f"{status} {collection}: {count} chunks")

        if total_chunks > 0 and total_embeddings > 0:
            print("\n🎉 Data embedding completed successfully!")
            print("✅ Your documents are now searchable in the RAG pipeline")
            print(f"🔍 Ready to search across {sum(collections_updated.values())} embedded chunks")
            return True
        else:
            print("\n⚠️  No data was embedded. Check the logs for errors.")
            return False
    else:
        print(f"\n❌ Processing failed: Invalid results format")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)

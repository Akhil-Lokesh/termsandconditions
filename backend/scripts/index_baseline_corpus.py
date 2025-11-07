#!/usr/bin/env python3
"""
Baseline Corpus Indexing Script

This script processes collected T&C PDFs and indexes them to Pinecone's baseline namespace
for anomaly detection comparison.

Features:
- Batch processing with progress tracking
- Resume capability (skip already indexed)
- Error recovery and retry logic
- Performance metrics tracking
- Dry-run mode for testing

Prerequisites:
    - Baseline corpus collected (scripts/collect_baseline_corpus.py)
    - Environment variables configured (.env)
    - Pinecone API key and index created

Usage:
    # Index all documents
    python scripts/index_baseline_corpus.py

    # Dry run (no actual indexing)
    python scripts/index_baseline_corpus.py --dry-run

    # Force re-index
    python scripts/index_baseline_corpus.py --force

    # Resume from specific category
    python scripts/index_baseline_corpus.py --category tech
"""

import asyncio
import sys
import time
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import argparse

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.document_processor import DocumentProcessor
from app.core.structure_extractor import StructureExtractor
from app.core.legal_chunker import LegalChunker
from app.services.openai_service import OpenAIService
from app.services.pinecone_service import PineconeService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("corpus_indexing.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# INDEXING FUNCTIONS
# ============================================================================

class CorpusIndexer:
    """Handles indexing of baseline T&C corpus to Pinecone."""

    def __init__(
        self,
        openai_service: OpenAIService,
        pinecone_service: PineconeService,
        dry_run: bool = False
    ):
        self.openai = openai_service
        self.pinecone = pinecone_service
        self.dry_run = dry_run

        self.processor = DocumentProcessor()
        self.extractor = StructureExtractor()
        self.chunker = LegalChunker(max_chunk_size=500, overlap=50)

        # Statistics
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total_chunks": 0,
            "total_chars": 0,
            "total_time": 0.0,
            "errors": []
        }

    async def check_already_indexed(self, document_id: str) -> bool:
        """
        Check if document is already indexed in Pinecone.

        Args:
            document_id: Baseline document ID

        Returns:
            True if already indexed, False otherwise
        """
        if self.dry_run:
            return False

        try:
            # Query with document_id filter
            results = await self.pinecone.query(
                query_embedding=[0.0] * 1536,  # Dummy embedding
                namespace=settings.PINECONE_BASELINE_NAMESPACE,
                top_k=1,
                filter={"document_id": document_id}
            )
            return len(results) > 0
        except Exception as e:
            logger.warning(f"Could not check if {document_id} is indexed: {e}")
            return False

    async def index_document(
        self,
        file_path: Path,
        metadata: Dict,
        force: bool = False
    ) -> Optional[Dict]:
        """
        Process and index a single T&C document.

        Args:
            file_path: Path to PDF or TXT file
            metadata: Document metadata from collection
            force: Force re-indexing even if exists

        Returns:
            Processing stats dict if successful, None otherwise
        """
        doc_id = f"baseline_{file_path.stem}"
        company = metadata.get("company", file_path.stem)

        start_time = time.time()

        try:
            # Check if already indexed
            if not force:
                already_indexed = await self.check_already_indexed(doc_id)
                if already_indexed:
                    logger.info(f"⊙ Skipping (already indexed): {company}")
                    self.stats["skipped"] += 1
                    return {
                        "document_id": doc_id,
                        "status": "skipped",
                        "reason": "already_indexed"
                    }

            logger.info(f"📄 Processing: {company}")

            # Step 1: Extract text
            logger.info(f"   1/5 Extracting text...")
            if file_path.suffix == ".txt":
                # Read text file directly
                text = file_path.read_text(encoding="utf-8")
                page_count = 1  # Text files don't have pages
            else:
                # Extract from PDF
                extracted = await self.processor.extract_text(str(file_path))
                text = extracted["text"]
                page_count = extracted["page_count"]

            if len(text) < 500:
                logger.warning(f"   ⚠️  Text too short ({len(text)} chars), skipping")
                self.stats["failed"] += 1
                self.stats["errors"].append({
                    "document": company,
                    "error": "text_too_short",
                    "details": f"{len(text)} characters"
                })
                return None

            # Step 2: Parse structure
            logger.info(f"   2/5 Parsing structure...")
            clauses = await self.extractor.extract_structure(text)
            logger.info(f"       Found {len(clauses)} clauses")

            # Step 3: Create chunks
            logger.info(f"   3/5 Creating chunks...")
            chunks = await self.chunker.create_chunks(clauses)
            logger.info(f"       Created {len(chunks)} chunks")

            # Step 4: Generate embeddings
            logger.info(f"   4/5 Generating embeddings...")
            texts = [chunk["text"] for chunk in chunks]
            embeddings = await self.openai.batch_create_embeddings(texts)

            for chunk, embedding in zip(chunks, embeddings):
                chunk["embedding"] = embedding

            # Add baseline-specific metadata
            for chunk in chunks:
                chunk["metadata"]["document_id"] = doc_id
                chunk["metadata"]["company"] = company
                chunk["metadata"]["category"] = metadata.get("category", "unknown")
                chunk["metadata"]["source_url"] = metadata.get("source_url", "")
                chunk["metadata"]["is_baseline"] = True

            # Step 5: Upload to Pinecone
            if not self.dry_run:
                logger.info(f"   5/5 Uploading to Pinecone baseline namespace...")
                await self.pinecone.upsert_chunks(
                    chunks=chunks,
                    namespace=settings.PINECONE_BASELINE_NAMESPACE,
                    document_id=doc_id
                )
            else:
                logger.info(f"   5/5 [DRY RUN] Would upload {len(chunks)} vectors")

            processing_time = time.time() - start_time

            # Update statistics
            self.stats["successful"] += 1
            self.stats["total_chunks"] += len(chunks)
            self.stats["total_chars"] += len(text)
            self.stats["total_time"] += processing_time

            logger.info(f"✓ Indexed: {company} ({len(chunks)} chunks, {processing_time:.1f}s)")

            return {
                "document_id": doc_id,
                "company": company,
                "status": "success",
                "page_count": page_count,
                "clause_count": len(clauses),
                "chunk_count": len(chunks),
                "text_length": len(text),
                "processing_time": processing_time
            }

        except Exception as e:
            logger.error(f"✗ Failed to index {company}: {e}", exc_info=True)
            self.stats["failed"] += 1
            self.stats["errors"].append({
                "document": company,
                "error": str(e),
                "path": str(pdf_path)
            })
            return None

    async def index_corpus(
        self,
        corpus_dir: Path,
        categories: Optional[List[str]] = None,
        force: bool = False,
        batch_delay: float = 1.0
    ):
        """
        Index entire baseline corpus.

        Args:
            corpus_dir: Directory containing corpus PDFs
            categories: List of categories to index (None = all)
            force: Force re-indexing
            batch_delay: Delay between documents (seconds)
        """
        if not corpus_dir.exists():
            logger.error(f"❌ Corpus directory not found: {corpus_dir}")
            return

        # Load metadata
        metadata_path = corpus_dir / "metadata.json"
        if metadata_path.exists():
            metadata_list = json.loads(metadata_path.read_text())
            metadata_map = {m["filename"]: m for m in metadata_list}
        else:
            logger.warning("⚠️  metadata.json not found, proceeding without metadata")
            metadata_map = {}

        # Get all PDF and TXT files
        if categories:
            doc_files = []
            for category in categories:
                category_dir = corpus_dir / category
                if category_dir.exists():
                    doc_files.extend(list(category_dir.glob("*.pdf")))
                    doc_files.extend(list(category_dir.glob("*.txt")))
        else:
            doc_files = list(corpus_dir.rglob("*.pdf")) + list(corpus_dir.rglob("*.txt"))

        total_files = len(doc_files)
        logger.info(f"{'='*60}")
        logger.info(f"📚 INDEXING BASELINE CORPUS")
        logger.info(f"{'='*60}")
        logger.info(f"Total documents: {total_files}")
        logger.info(f"Target namespace: {settings.PINECONE_BASELINE_NAMESPACE}")
        logger.info(f"Dry run: {self.dry_run}")
        logger.info(f"{'='*60}\n")

        # Process each document
        results = []
        for idx, doc_path in enumerate(doc_files, 1):
            logger.info(f"\n[{idx}/{total_files}] {doc_path.name}")

            # Get metadata
            metadata = metadata_map.get(doc_path.name, {})

            # Index document
            result = await self.index_document(doc_path, metadata, force)
            if result:
                results.append(result)

            # Progress update
            progress_pct = (idx / total_files) * 100
            logger.info(f"Progress: {progress_pct:.1f}% ({idx}/{total_files})")

            # Rate limiting
            if idx < total_files:
                await asyncio.sleep(batch_delay)

        # Save results
        results_path = corpus_dir / "indexing_results.json"
        results_path.write_text(json.dumps(results, indent=2))

        # Final summary
        self.print_summary(results_path)

        return results

    def print_summary(self, results_path: Path):
        """Print final summary statistics."""
        logger.info(f"\n{'='*60}")
        logger.info("📊 INDEXING SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"✓ Successful:     {self.stats['successful']}")
        logger.info(f"⊙ Skipped:        {self.stats['skipped']}")
        logger.info(f"✗ Failed:         {self.stats['failed']}")
        logger.info(f"📄 Total Docs:    {self.stats['total_processed']}")
        logger.info(f"📦 Total Chunks:  {self.stats['total_chunks']}")
        logger.info(f"📝 Total Chars:   {self.stats['total_chars']:,}")

        if self.stats['successful'] > 0:
            avg_time = self.stats['total_time'] / self.stats['successful']
            avg_chunks = self.stats['total_chunks'] / self.stats['successful']
            logger.info(f"⏱️  Avg Time/Doc:  {avg_time:.1f}s")
            logger.info(f"📊 Avg Chunks/Doc: {avg_chunks:.1f}")

        logger.info(f"\n💾 Results saved to: {results_path}")

        if self.stats['errors']:
            logger.info(f"\n⚠️  {len(self.stats['errors'])} ERRORS:")
            for error in self.stats['errors'][:5]:  # Show first 5
                logger.info(f"   • {error['document']}: {error['error']}")
            if len(self.stats['errors']) > 5:
                logger.info(f"   ... and {len(self.stats['errors']) - 5} more")

        # Cost estimate
        if self.stats['total_chunks'] > 0:
            embedding_cost = (self.stats['total_chunks'] / 1000) * 0.02  # $0.02 per 1K tokens
            logger.info(f"\n💰 Estimated OpenAI Cost: ${embedding_cost:.2f}")


# ============================================================================
# CLI INTERFACE
# ============================================================================

async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Index baseline T&C corpus to Pinecone",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Index all documents
    python index_baseline_corpus.py

    # Dry run (test without uploading)
    python index_baseline_corpus.py --dry-run

    # Force re-index existing documents
    python index_baseline_corpus.py --force

    # Index specific categories
    python index_baseline_corpus.py --category tech saas

    # Faster processing (less delay between documents)
    python index_baseline_corpus.py --delay 0.5
        """
    )

    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=Path("data/baseline_corpus"),
        help="Corpus directory (default: data/baseline_corpus)"
    )

    parser.add_argument(
        "--category",
        nargs="+",
        help="Specific categories to index"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-indexing of existing documents"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test run without actual indexing"
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between documents in seconds (default: 1.0)"
    )

    args = parser.parse_args()

    # Initialize services
    try:
        logger.info("Initializing services...")
        openai_service = OpenAIService()
        pinecone_service = PineconeService()
        await pinecone_service.initialize()

        # Create indexer
        indexer = CorpusIndexer(
            openai_service=openai_service,
            pinecone_service=pinecone_service,
            dry_run=args.dry_run
        )

        # Run indexing
        await indexer.index_corpus(
            corpus_dir=args.corpus_dir,
            categories=args.category,
            force=args.force,
            batch_delay=args.delay
        )

        # Cleanup
        await openai_service.close()
        await pinecone_service.close()

        logger.info("\n✅ Indexing complete!")
        logger.info("\n🚀 Next steps:")
        logger.info("   1. Validate index: python scripts/validate_corpus.py")
        logger.info("   2. Test anomaly detection with baseline")

    except KeyboardInterrupt:
        logger.info("\n⚠️  Indexing interrupted by user")
        logger.info("   Run again to resume (already indexed docs will be skipped)")
    except Exception as e:
        logger.error(f"\n❌ Indexing failed: {e}", exc_info=True)
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())

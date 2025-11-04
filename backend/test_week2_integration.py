"""
Week 2 Integration Test

Tests the complete document processing pipeline with all services:
- OpenAI service (embeddings, completions)
- Pinecone service (vector storage, retrieval)
- Redis cache service (caching)
- Metadata extractor (GPT-4)
- Complete pipeline (document → chunks → embeddings → storage)

This script requires:
- Valid OpenAI API key
- Valid Pinecone API key
- Redis running (optional, will work without cache)
- A sample PDF file

Usage:
    python backend/test_week2_integration.py [pdf_path]

Example:
    python backend/test_week2_integration.py data/test_samples/simple_tos.pdf
"""

import asyncio
import sys
from pathlib import Path
import json
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.core.document_processor import DocumentProcessor
from app.core.structure_extractor import StructureExtractor
from app.core.legal_chunker import LegalChunker
from app.core.metadata_extractor import MetadataExtractor
from app.services.openai_service import OpenAIService
from app.services.pinecone_service import PineconeService
from app.services.cache_service import CacheService


async def test_cache_service():
    """Test Redis cache service."""
    print("\n" + "="*60)
    print("TEST 1: Redis Cache Service")
    print("="*60)

    try:
        cache = CacheService()
        await cache.connect()
        print("✓ Connected to Redis")

        # Test set/get
        await cache.set("test_key", {"value": 123, "name": "test"}, ttl=60)
        value = await cache.get("test_key")
        assert value["value"] == 123, "Cache value mismatch"
        print("✓ Set/get working")

        # Test exists
        exists = await cache.exists("test_key")
        assert exists, "Key should exist"
        print("✓ Exists check working")

        # Test delete
        await cache.delete("test_key")
        value = await cache.get("test_key")
        assert value is None, "Key should be deleted"
        print("✓ Delete working")

        # Test stats
        stats = await cache.get_stats()
        print(f"✓ Cache stats: {stats['status']}, keys: {stats.get('total_keys', 'N/A')}")

        await cache.disconnect()
        print("✓ Disconnected from Redis")

    except Exception as e:
        print(f"✗ Cache test failed: {e}")
        print("  (This is OK if Redis is not running)")
        return None

    return cache


async def test_openai_service(cache=None):
    """Test OpenAI service."""
    print("\n" + "="*60)
    print("TEST 2: OpenAI Service")
    print("="*60)

    try:
        openai = OpenAIService(cache_service=cache)
        print("✓ OpenAI service initialized")

        # Test embedding
        print("\nTesting embedding generation...")
        text = "This is a test terms of service document."
        embedding = await openai.create_embedding(text)
        assert len(embedding) == 1536, f"Expected 1536 dimensions, got {len(embedding)}"
        print(f"✓ Generated embedding: {len(embedding)} dimensions")

        # Test batch embeddings
        print("\nTesting batch embeddings...")
        texts = [
            "First test clause about payments.",
            "Second test clause about liability.",
            "Third test clause about termination.",
        ]
        embeddings = await openai.batch_create_embeddings(texts)
        assert len(embeddings) == 3, "Should have 3 embeddings"
        print(f"✓ Generated {len(embeddings)} batch embeddings")

        # Test completion
        print("\nTesting GPT-4 completion...")
        prompt = "Explain in one sentence what a Terms of Service document is."
        completion = await openai.create_completion(prompt, max_tokens=100)
        assert len(completion) > 0, "Completion should not be empty"
        print(f"✓ Generated completion: {completion[:100]}...")

        # Test structured completion
        print("\nTesting structured (JSON) completion...")
        prompt = 'Return a JSON object with fields "name" and "age". Set name to "Test" and age to 25.'
        result = await openai.create_structured_completion(prompt)
        assert "name" in result, "JSON should have 'name' field"
        print(f"✓ Structured completion: {result}")

        await openai.close()
        print("✓ OpenAI service closed")

        return openai

    except Exception as e:
        logger.error(f"OpenAI test failed: {e}", exc_info=True)
        raise


async def test_pinecone_service():
    """Test Pinecone service."""
    print("\n" + "="*60)
    print("TEST 3: Pinecone Service")
    print("="*60)

    try:
        pinecone = PineconeService()
        await pinecone.initialize()
        print("✓ Pinecone initialized")

        # Get index stats
        stats = await pinecone.get_index_stats()
        print(f"✓ Index stats: {stats['total_vector_count']} total vectors")
        print(f"  Namespaces: {list(stats['namespaces'].keys())}")

        return pinecone

    except Exception as e:
        logger.error(f"Pinecone test failed: {e}", exc_info=True)
        raise


async def test_complete_pipeline(pdf_path: str):
    """Test complete document processing pipeline."""
    print("\n" + "="*60)
    print("TEST 4: Complete Processing Pipeline")
    print("="*60)

    # Initialize all services
    cache = await test_cache_service()
    openai = OpenAIService(cache_service=cache)
    pinecone = await test_pinecone_service()

    # Step 1: Extract text
    print("\n[Step 1] Extracting text from PDF...")
    processor = DocumentProcessor()
    result = await processor.extract_text(pdf_path)
    text = result["text"]
    print(f"✓ Extracted {len(text)} characters from {result['page_count']} pages")
    print(f"  Method: {result['extraction_method']}")

    # Step 2: Extract structure
    print("\n[Step 2] Extracting document structure...")
    extractor = StructureExtractor()
    structure = await extractor.extract_structure(text)
    sections = structure["sections"]
    print(f"✓ Extracted {len(sections)} sections")
    for i, section in enumerate(sections[:3], 1):
        print(f"  {i}. {section['title']} ({len(section.get('clauses', []))} clauses)")

    # Step 3: Create chunks
    print("\n[Step 3] Creating semantic chunks...")
    chunker = LegalChunker(max_chunk_size=500, overlap=50)
    chunks = await chunker.create_chunks(sections)
    print(f"✓ Created {len(chunks)} chunks")
    print(f"  Sample chunk metadata: {chunks[0]['metadata']}")

    # Step 4: Generate embeddings
    print("\n[Step 4] Generating embeddings...")
    texts = [chunk["text"] for chunk in chunks]
    embeddings = await openai.batch_create_embeddings(texts[:10])  # Limit to 10 for testing
    print(f"✓ Generated {len(embeddings)} embeddings (limited to 10 for testing)")

    # Add embeddings to chunks
    for i, embedding in enumerate(embeddings):
        chunks[i]["embedding"] = embedding

    # Step 5: Upload to Pinecone
    print("\n[Step 5] Uploading to Pinecone...")
    doc_id = "test_document_week2"
    chunks_with_embeddings = chunks[:10]  # Only upload first 10
    result = await pinecone.upsert_chunks(
        chunks=chunks_with_embeddings,
        namespace=pinecone.user_namespace,
        document_id=doc_id,
    )
    print(f"✓ Uploaded {result['vectors_upserted']} vectors to namespace '{result['namespace']}'")

    # Step 6: Test retrieval
    print("\n[Step 6] Testing vector retrieval...")
    query_text = "What are the payment terms?"
    query_embedding = await openai.create_embedding(query_text)
    matches = await pinecone.query(
        query_embedding=query_embedding,
        namespace=pinecone.user_namespace,
        top_k=3,
        filter={"document_id": doc_id},
    )
    print(f"✓ Found {len(matches)} matches for query: '{query_text}'")
    for i, match in enumerate(matches, 1):
        print(f"  {i}. Score: {match['score']:.3f} - Section: {match['metadata'].get('section')}")

    # Step 7: Extract metadata
    print("\n[Step 7] Extracting metadata with GPT-4...")
    metadata_extractor = MetadataExtractor(openai)
    metadata = await metadata_extractor.extract_metadata(text)
    print(f"✓ Metadata extracted:")
    print(f"  Company: {metadata.get('company_name')}")
    print(f"  Jurisdiction: {metadata.get('jurisdiction')}")
    print(f"  Document Type: {metadata.get('document_type')}")
    print(f"  Effective Date: {metadata.get('effective_date')}")

    # Cleanup
    print("\n[Cleanup] Deleting test vectors...")
    await pinecone.delete_document(doc_id, pinecone.user_namespace)
    print("✓ Test vectors deleted")

    # Close services
    await openai.close()
    await pinecone.close()
    if cache:
        await cache.disconnect()

    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60)


async def main():
    """Run all integration tests."""
    # Check for PDF path
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        # Try to find a sample PDF
        test_samples = Path("data/test_samples")
        if test_samples.exists():
            pdfs = list(test_samples.glob("*.pdf"))
            if pdfs:
                pdf_path = str(pdfs[0])
                print(f"Using sample PDF: {pdf_path}")
            else:
                print("Error: No PDF found in data/test_samples/")
                print("Usage: python backend/test_week2_integration.py <pdf_path>")
                sys.exit(1)
        else:
            print("Error: data/test_samples/ directory not found")
            print("Usage: python backend/test_week2_integration.py <pdf_path>")
            sys.exit(1)

    if not Path(pdf_path).exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)

    print("\n" + "="*60)
    print("WEEK 2 INTEGRATION TEST")
    print("="*60)
    print(f"PDF: {pdf_path}")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"OpenAI Model: {settings.OPENAI_MODEL_GPT4}")
    print(f"Pinecone Index: {settings.PINECONE_INDEX_NAME}")
    print("="*60)

    try:
        await test_complete_pipeline(pdf_path)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nTest failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

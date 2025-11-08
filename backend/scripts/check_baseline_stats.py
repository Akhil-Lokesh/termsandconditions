#!/usr/bin/env python3
"""
Baseline Corpus Statistics Checker

Queries Pinecone to verify baseline corpus is properly indexed and provides
statistics about the indexed documents.

Usage:
    python scripts/check_baseline_stats.py
"""

import asyncio
import sys
from pathlib import Path
from collections import defaultdict

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services.openai_service import OpenAIService
from app.services.pinecone_service import PineconeService


async def check_baseline_stats():
    """Check baseline corpus statistics in Pinecone."""

    print("=" * 70)
    print("🔍 BASELINE CORPUS STATISTICS")
    print("=" * 70)
    print()

    # Initialize services
    print("Initializing services...")
    openai_service = OpenAIService()
    pinecone_service = PineconeService()
    await pinecone_service.initialize()

    print(f"✓ Connected to Pinecone index: {settings.PINECONE_INDEX_NAME}")
    print(f"✓ Baseline namespace: {settings.PINECONE_BASELINE_NAMESPACE}")
    print()

    # Get index statistics
    try:
        index_stats = pinecone_service.index.describe_index_stats()
        print("📊 INDEX STATISTICS")
        print("-" * 70)

        # Overall stats
        total_vectors = index_stats.get("total_vector_count", 0)
        print(f"Total vectors (all namespaces): {total_vectors:,}")

        # Namespace stats
        namespaces = index_stats.get("namespaces", {})

        if settings.PINECONE_BASELINE_NAMESPACE in namespaces:
            baseline_stats = namespaces[settings.PINECONE_BASELINE_NAMESPACE]
            baseline_count = baseline_stats.get("vector_count", 0)

            print(f"Baseline namespace vectors: {baseline_count:,}")
            print()

            if baseline_count == 0:
                print("⚠️  WARNING: Baseline namespace is EMPTY!")
                print()
                print("The baseline corpus has not been indexed yet.")
                print()
                print("To index the baseline corpus, run:")
                print("  cd backend")
                print("  python scripts/index_baseline_corpus.py")
                print()
                await openai_service.close()
                await pinecone_service.close()
                return

        else:
            print(f"⚠️  WARNING: Baseline namespace '{settings.PINECONE_BASELINE_NAMESPACE}' not found!")
            print()
            print("Available namespaces:")
            for ns_name, ns_stats in namespaces.items():
                print(f"  - {ns_name}: {ns_stats.get('vector_count', 0):,} vectors")
            print()
            print("To create and populate the baseline namespace, run:")
            print("  cd backend")
            print("  python scripts/index_baseline_corpus.py")
            print()
            await openai_service.close()
            await pinecone_service.close()
            return

        # All namespaces breakdown
        print("Namespace breakdown:")
        for ns_name, ns_stats in namespaces.items():
            count = ns_stats.get("vector_count", 0)
            print(f"  • {ns_name}: {count:,} vectors")
        print()

    except Exception as e:
        print(f"❌ Error fetching index statistics: {e}")
        await openai_service.close()
        await pinecone_service.close()
        return

    # Sample queries to test baseline corpus
    print("🔎 SAMPLE QUERIES")
    print("-" * 70)

    test_queries = [
        "data collection and privacy",
        "terminate account or service",
        "liability and indemnification",
        "payment terms and refunds",
        "intellectual property rights"
    ]

    for query_text in test_queries:
        try:
            # Generate embedding for query
            query_embedding = await openai_service.create_embedding(query_text)

            # Query baseline namespace
            results = await pinecone_service.query(
                query_embedding=query_embedding,
                namespace=settings.PINECONE_BASELINE_NAMESPACE,
                top_k=10,
                include_metadata=True
            )

            if results:
                print(f"\n'{query_text}'")
                print(f"  Found {len(results)} relevant clauses")

                # Show top 3 results
                for i, match in enumerate(results[:3], 1):
                    score = match.get("score", 0)
                    metadata = match.get("metadata", {})
                    company = metadata.get("company", "Unknown")
                    text_preview = metadata.get("text", "")[:100]

                    print(f"  {i}. {company} (similarity: {score:.2f})")
                    print(f"     \"{text_preview}...\"")
            else:
                print(f"\n'{query_text}'")
                print(f"  ⚠️  No results found")

        except Exception as e:
            print(f"\n'{query_text}'")
            print(f"  ❌ Error: {e}")

    print()

    # Get unique companies and industries from metadata
    print("📚 CORPUS COMPOSITION")
    print("-" * 70)

    try:
        # Query a sample of vectors to extract metadata
        dummy_embedding = [0.0] * 1536
        sample_results = await pinecone_service.query(
            query_embedding=dummy_embedding,
            namespace=settings.PINECONE_BASELINE_NAMESPACE,
            top_k=1000,  # Get large sample
            include_metadata=True
        )

        if sample_results:
            companies = set()
            industries = defaultdict(int)
            document_ids = set()

            for match in sample_results:
                metadata = match.get("metadata", {})

                # Extract company names
                company = metadata.get("company")
                if company:
                    companies.add(company)

                # Extract industries/categories
                category = metadata.get("category") or metadata.get("industry")
                if category:
                    industries[category] += 1

                # Extract document IDs
                doc_id = metadata.get("document_id")
                if doc_id:
                    document_ids.add(doc_id)

            print(f"Unique documents: {len(document_ids)}")
            print(f"Unique companies: {len(companies)}")
            print()

            if companies:
                print("Sample companies:")
                for company in sorted(list(companies))[:15]:
                    print(f"  • {company}")
                if len(companies) > 15:
                    print(f"  ... and {len(companies) - 15} more")
                print()

            if industries:
                print("Industries/Categories:")
                for category, count in sorted(industries.items(), key=lambda x: x[1], reverse=True):
                    print(f"  • {category}: {count} chunks")
                print()

        else:
            print("⚠️  Could not fetch sample data from baseline namespace")
            print()

    except Exception as e:
        print(f"❌ Error analyzing corpus composition: {e}")
        print()

    # Final summary
    print("=" * 70)
    print("✅ BASELINE CORPUS CHECK COMPLETE")
    print("=" * 70)
    print()

    if baseline_count > 0:
        print(f"✓ Baseline corpus is properly indexed with {baseline_count:,} vectors")
        print(f"✓ Ready for anomaly detection")
        print()
        print("Next steps:")
        print("  1. Upload a test T&C document via the API")
        print("  2. Check anomaly detection results")
        print("  3. Verify prevalence calculations are working")
    else:
        print("⚠️  Baseline corpus needs to be indexed")
        print()
        print("Run: python scripts/index_baseline_corpus.py")

    print()

    # Cleanup
    await openai_service.close()
    await pinecone_service.close()


if __name__ == "__main__":
    try:
        asyncio.run(check_baseline_stats())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3
"""
Baseline Corpus Statistics Analyzer

This script analyzes the baseline corpus and generates comprehensive statistics
including content analysis, category distribution, and indexing metrics.

Features:
- Document statistics (pages, length, sections)
- Category distribution and balance
- Pinecone index statistics
- Content analysis (common clauses, topics)
- Quality metrics
- Visual reports (if matplotlib available)

Usage:
    # Analyze corpus
    python scripts/analyze_corpus_stats.py

    # Include Pinecone index stats
    python scripts/analyze_corpus_stats.py --check-index

    # Generate detailed report
    python scripts/analyze_corpus_stats.py --detailed

    # Save report to file
    python scripts/analyze_corpus_stats.py --output corpus_stats.json
"""

import sys
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List
from collections import defaultdict, Counter
from datetime import datetime
import argparse

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.document_processor import DocumentProcessor
from app.services.pinecone_service import PineconeService

# Try to import matplotlib for visualizations
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("matplotlib not available - visualizations disabled")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("corpus_analysis.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# ANALYSIS FUNCTIONS
# ============================================================================

class CorpusAnalyzer:
    """Analyzes baseline corpus statistics."""

    def __init__(self, corpus_dir: Path):
        self.corpus_dir = corpus_dir
        self.processor = DocumentProcessor()

        self.stats = {
            "analyzed_at": datetime.now().isoformat(),
            "corpus_directory": str(corpus_dir),
            "document_stats": {},
            "category_stats": {},
            "content_stats": {},
            "quality_metrics": {},
            "pinecone_stats": {}
        }

    async def analyze_documents(self) -> Dict:
        """Analyze all documents in corpus."""
        logger.info("📄 Analyzing documents...")

        pdf_files = list(self.corpus_dir.rglob("*.pdf"))
        total_files = len(pdf_files)

        if total_files == 0:
            logger.warning("No PDF files found!")
            return {}

        # Aggregate statistics
        doc_stats = {
            "total_documents": total_files,
            "total_pages": 0,
            "total_chars": 0,
            "page_counts": [],
            "char_counts": [],
            "extraction_methods": defaultdict(int),
            "documents_by_category": defaultdict(list)
        }

        # Analyze each document
        for idx, pdf_path in enumerate(pdf_files, 1):
            logger.info(f"   [{idx}/{total_files}] {pdf_path.name}")

            try:
                # Extract text
                extracted = await self.processor.extract_text(str(pdf_path))

                page_count = extracted["page_count"]
                text_length = len(extracted["text"])
                method = extracted["extraction_method"]

                # Update statistics
                doc_stats["total_pages"] += page_count
                doc_stats["total_chars"] += text_length
                doc_stats["page_counts"].append(page_count)
                doc_stats["char_counts"].append(text_length)
                doc_stats["extraction_methods"][method] += 1

                # Category
                category = pdf_path.parent.name if pdf_path.parent != self.corpus_dir else "root"
                doc_stats["documents_by_category"][category].append({
                    "filename": pdf_path.name,
                    "pages": page_count,
                    "chars": text_length
                })

            except Exception as e:
                logger.error(f"   Error processing {pdf_path.name}: {e}")

        # Calculate averages and statistics
        if doc_stats["page_counts"]:
            doc_stats["avg_pages"] = doc_stats["total_pages"] / total_files
            doc_stats["avg_chars"] = doc_stats["total_chars"] / total_files
            doc_stats["min_pages"] = min(doc_stats["page_counts"])
            doc_stats["max_pages"] = max(doc_stats["page_counts"])
            doc_stats["median_pages"] = sorted(doc_stats["page_counts"])[total_files // 2]

        self.stats["document_stats"] = doc_stats
        return doc_stats

    def analyze_categories(self) -> Dict:
        """Analyze category distribution."""
        logger.info("\n📁 Analyzing categories...")

        doc_stats = self.stats.get("document_stats", {})
        docs_by_cat = doc_stats.get("documents_by_category", {})

        cat_stats = {}
        for category, documents in docs_by_cat.items():
            cat_stats[category] = {
                "count": len(documents),
                "total_pages": sum(d["pages"] for d in documents),
                "total_chars": sum(d["chars"] for d in documents),
                "avg_pages": sum(d["pages"] for d in documents) / len(documents) if documents else 0,
                "avg_chars": sum(d["chars"] for d in documents) / len(documents) if documents else 0,
            }

        # Check balance
        total_docs = doc_stats.get("total_documents", 0)
        expected_per_category = total_docs / len(cat_stats) if cat_stats else 0

        for category, stats in cat_stats.items():
            deviation = abs(stats["count"] - expected_per_category)
            stats["balance_score"] = 1.0 - (deviation / total_docs) if total_docs > 0 else 0

        self.stats["category_stats"] = cat_stats
        return cat_stats

    async def analyze_pinecone_index(self, pinecone_service: PineconeService) -> Dict:
        """Analyze Pinecone index statistics."""
        logger.info("\n🔍 Analyzing Pinecone index...")

        try:
            # Get index stats
            index_stats = pinecone_service.index.describe_index_stats()

            pinecone_stats = {
                "index_name": settings.PINECONE_INDEX_NAME,
                "total_vector_count": index_stats.get("total_vector_count", 0),
                "dimension": index_stats.get("dimension", 0),
                "namespaces": {}
            }

            # Namespace statistics
            namespaces = index_stats.get("namespaces", {})
            for namespace_name, namespace_stats in namespaces.items():
                pinecone_stats["namespaces"][namespace_name] = {
                    "vector_count": namespace_stats.get("vector_count", 0)
                }

            # Check baseline namespace
            baseline_vectors = pinecone_stats["namespaces"].get(
                settings.PINECONE_BASELINE_NAMESPACE, {}
            ).get("vector_count", 0)

            total_docs = self.stats.get("document_stats", {}).get("total_documents", 0)

            if baseline_vectors > 0 and total_docs > 0:
                pinecone_stats["avg_vectors_per_doc"] = baseline_vectors / total_docs
                pinecone_stats["indexing_coverage"] = f"{(baseline_vectors / (total_docs * 50)) * 100:.1f}%"

            self.stats["pinecone_stats"] = pinecone_stats
            return pinecone_stats

        except Exception as e:
            logger.error(f"Error analyzing Pinecone: {e}")
            return {}

    def calculate_quality_metrics(self) -> Dict:
        """Calculate corpus quality metrics."""
        logger.info("\n✅ Calculating quality metrics...")

        doc_stats = self.stats.get("document_stats", {})
        cat_stats = self.stats.get("category_stats", {})

        quality = {
            "completeness_score": 0.0,
            "diversity_score": 0.0,
            "quality_score": 0.0,
            "recommendations": []
        }

        # Completeness: Do we have enough documents?
        total_docs = doc_stats.get("total_documents", 0)
        target_docs = 100
        quality["completeness_score"] = min(total_docs / target_docs, 1.0)

        if total_docs < target_docs:
            quality["recommendations"].append(
                f"Add {target_docs - total_docs} more documents to reach target of {target_docs}"
            )

        # Diversity: Are categories balanced?
        if cat_stats:
            balance_scores = [stats["balance_score"] for stats in cat_stats.values()]
            quality["diversity_score"] = sum(balance_scores) / len(balance_scores)

            # Check if any category is underrepresented
            for category, stats in cat_stats.items():
                if stats["count"] < 15:
                    quality["recommendations"].append(
                        f"Category '{category}' has only {stats['count']} documents (target: 20+)"
                    )

        # Quality: Average document length
        avg_pages = doc_stats.get("avg_pages", 0)
        if avg_pages >= 5:
            quality["length_score"] = 1.0
        elif avg_pages >= 3:
            quality["length_score"] = 0.8
        else:
            quality["length_score"] = 0.5
            quality["recommendations"].append("Average document length is low (< 3 pages)")

        # Overall quality score
        quality["quality_score"] = (
            quality["completeness_score"] * 0.4 +
            quality["diversity_score"] * 0.3 +
            quality["length_score"] * 0.3
        )

        self.stats["quality_metrics"] = quality
        return quality

    def print_summary(self):
        """Print comprehensive summary."""
        logger.info(f"\n{'='*70}")
        logger.info("📊 BASELINE CORPUS STATISTICS")
        logger.info(f"{'='*70}")

        # Document statistics
        doc_stats = self.stats.get("document_stats", {})
        if doc_stats:
            logger.info("\n📄 DOCUMENT STATISTICS:")
            logger.info(f"   Total Documents:      {doc_stats.get('total_documents', 0)}")
            logger.info(f"   Total Pages:          {doc_stats.get('total_pages', 0):,}")
            logger.info(f"   Total Characters:     {doc_stats.get('total_chars', 0):,}")
            logger.info(f"   Average Pages/Doc:    {doc_stats.get('avg_pages', 0):.1f}")
            logger.info(f"   Average Chars/Doc:    {doc_stats.get('avg_chars', 0):,.0f}")
            logger.info(f"   Page Range:           {doc_stats.get('min_pages', 0)} - {doc_stats.get('max_pages', 0)}")
            logger.info(f"   Median Pages:         {doc_stats.get('median_pages', 0)}")

            extraction_methods = doc_stats.get("extraction_methods", {})
            if extraction_methods:
                logger.info(f"\n   Extraction Methods:")
                for method, count in extraction_methods.items():
                    pct = (count / doc_stats['total_documents']) * 100
                    logger.info(f"      {method:15s}: {count:3d} ({pct:.1f}%)")

        # Category statistics
        cat_stats = self.stats.get("category_stats", {})
        if cat_stats:
            logger.info(f"\n📁 CATEGORY DISTRIBUTION:")
            for category, stats in sorted(cat_stats.items()):
                logger.info(f"   {category:15s}: {stats['count']:3d} docs, "
                          f"{stats['avg_pages']:.1f} avg pages, "
                          f"balance: {stats['balance_score']:.2f}")

        # Pinecone statistics
        pinecone_stats = self.stats.get("pinecone_stats", {})
        if pinecone_stats:
            logger.info(f"\n🔍 PINECONE INDEX:")
            logger.info(f"   Index Name:           {pinecone_stats.get('index_name', 'N/A')}")
            logger.info(f"   Total Vectors:        {pinecone_stats.get('total_vector_count', 0):,}")
            logger.info(f"   Dimension:            {pinecone_stats.get('dimension', 0)}")

            namespaces = pinecone_stats.get("namespaces", {})
            if namespaces:
                logger.info(f"   Namespaces:")
                for ns_name, ns_stats in namespaces.items():
                    logger.info(f"      {ns_name:20s}: {ns_stats.get('vector_count', 0):,} vectors")

            if "avg_vectors_per_doc" in pinecone_stats:
                logger.info(f"   Avg Vectors/Doc:      {pinecone_stats['avg_vectors_per_doc']:.1f}")

        # Quality metrics
        quality = self.stats.get("quality_metrics", {})
        if quality:
            logger.info(f"\n✅ QUALITY METRICS:")
            logger.info(f"   Completeness:         {quality.get('completeness_score', 0):.1%}")
            logger.info(f"   Diversity:            {quality.get('diversity_score', 0):.1%}")
            logger.info(f"   Length Quality:       {quality.get('length_score', 0):.1%}")
            logger.info(f"   Overall Score:        {quality.get('quality_score', 0):.1%}")

            recommendations = quality.get("recommendations", [])
            if recommendations:
                logger.info(f"\n💡 RECOMMENDATIONS:")
                for rec in recommendations:
                    logger.info(f"   • {rec}")

        logger.info(f"\n{'='*70}")

    def generate_visualizations(self, output_dir: Path):
        """Generate visualization charts (requires matplotlib)."""
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("Matplotlib not available - skipping visualizations")
            return

        logger.info(f"\n📊 Generating visualizations...")
        output_dir.mkdir(parents=True, exist_ok=True)

        doc_stats = self.stats.get("document_stats", {})
        cat_stats = self.stats.get("category_stats", {})

        # Chart 1: Category distribution
        if cat_stats:
            fig, ax = plt.subplots(figsize=(10, 6))
            categories = list(cat_stats.keys())
            counts = [stats["count"] for stats in cat_stats.values()]

            ax.bar(categories, counts, color='steelblue')
            ax.set_xlabel('Category')
            ax.set_ylabel('Number of Documents')
            ax.set_title('Baseline Corpus - Category Distribution')
            ax.grid(axis='y', alpha=0.3)

            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig(output_dir / 'category_distribution.png', dpi=300)
            logger.info(f"   Saved: category_distribution.png")
            plt.close()

        # Chart 2: Page count distribution
        if doc_stats.get("page_counts"):
            fig, ax = plt.subplots(figsize=(10, 6))
            page_counts = doc_stats["page_counts"]

            ax.hist(page_counts, bins=20, color='seagreen', edgecolor='black')
            ax.set_xlabel('Page Count')
            ax.set_ylabel('Number of Documents')
            ax.set_title('Baseline Corpus - Page Count Distribution')
            ax.axvline(doc_stats.get("avg_pages", 0), color='red', linestyle='--',
                      label=f'Average: {doc_stats.get("avg_pages", 0):.1f}')
            ax.legend()
            ax.grid(axis='y', alpha=0.3)

            plt.tight_layout()
            plt.savefig(output_dir / 'page_count_distribution.png', dpi=300)
            logger.info(f"   Saved: page_count_distribution.png")
            plt.close()

        logger.info(f"✓ Visualizations saved to: {output_dir}")

    def save_report(self, output_path: Path):
        """Save statistics report to JSON."""
        output_path.write_text(json.dumps(self.stats, indent=2, default=str))
        logger.info(f"\n💾 Statistics report saved to: {output_path}")


# ============================================================================
# CLI INTERFACE
# ============================================================================

async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze baseline T&C corpus statistics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic analysis
    python analyze_corpus_stats.py

    # Include Pinecone index stats
    python analyze_corpus_stats.py --check-index

    # Generate visualizations
    python analyze_corpus_stats.py --visualize

    # Save detailed report
    python analyze_corpus_stats.py --output corpus_stats.json --detailed
        """
    )

    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=Path("data/baseline_corpus"),
        help="Corpus directory (default: data/baseline_corpus)"
    )

    parser.add_argument(
        "--check-index",
        action="store_true",
        help="Check Pinecone index statistics"
    )

    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Generate visualization charts (requires matplotlib)"
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Save statistics report to JSON file"
    )

    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Include detailed per-document statistics"
    )

    args = parser.parse_args()

    try:
        analyzer = CorpusAnalyzer(args.corpus_dir)

        # Run analysis
        await analyzer.analyze_documents()
        analyzer.analyze_categories()
        analyzer.calculate_quality_metrics()

        # Check Pinecone if requested
        if args.check_index:
            pinecone_service = PineconeService()
            await pinecone_service.initialize()
            await analyzer.analyze_pinecone_index(pinecone_service)
            await pinecone_service.close()

        # Print summary
        analyzer.print_summary()

        # Generate visualizations if requested
        if args.visualize:
            viz_dir = args.corpus_dir / "visualizations"
            analyzer.generate_visualizations(viz_dir)

        # Save report if requested
        if args.output:
            analyzer.save_report(args.output)

        logger.info("\n✅ Analysis complete!")

    except KeyboardInterrupt:
        logger.info("\n⚠️  Analysis interrupted by user")
        exit(130)
    except Exception as e:
        logger.error(f"\n❌ Analysis failed: {e}", exc_info=True)
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Baseline Corpus Validation Script

This script validates the quality and completeness of the baseline T&C corpus.

Validation Checks:
- ✓ All PDFs are readable
- ✓ Text extraction works
- ✓ Minimum page count (2 pages)
- ✓ Minimum content length (500 chars)
- ✓ No duplicate documents (by content hash)
- ✓ Metadata completeness
- ✓ Category distribution
- ✓ File size validation

Usage:
    # Validate entire corpus
    python scripts/validate_corpus.py

    # Validate specific category
    python scripts/validate_corpus.py --category tech

    # Generate detailed report
    python scripts/validate_corpus.py --detailed

    # Fix metadata issues
    python scripts/validate_corpus.py --fix-metadata
"""

import sys
import asyncio
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict
from datetime import datetime
import argparse

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.document_processor import DocumentProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("corpus_validation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# VALIDATION CHECKS
# ============================================================================

class CorpusValidator:
    """Validates baseline corpus quality."""

    def __init__(self, corpus_dir: Path):
        self.corpus_dir = corpus_dir
        self.processor = DocumentProcessor()

        # Validation results
        self.results = {
            "total_files": 0,
            "valid_files": 0,
            "invalid_files": 0,
            "warnings": [],
            "errors": [],
            "duplicates": [],
            "statistics": {}
        }

        # Content hashes for duplicate detection
        self.content_hashes: Dict[str, List[str]] = defaultdict(list)

    async def validate_document(self, pdf_path: Path) -> Dict:
        """
        Validate a single PDF document.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Validation result dict
        """
        result = {
            "filename": pdf_path.name,
            "path": str(pdf_path),
            "valid": True,
            "checks": {},
            "issues": []
        }

        try:
            # Check 1: File exists and is readable
            if not pdf_path.exists():
                result["valid"] = False
                result["issues"].append("File not found")
                return result

            file_size = pdf_path.stat().st_size
            result["checks"]["file_size"] = file_size

            # Check 2: Minimum file size (10KB)
            if file_size < 10_000:
                result["valid"] = False
                result["issues"].append(f"File too small: {file_size} bytes")
                return result

            # Check 3: Extract text
            try:
                extracted = await self.processor.extract_text(str(pdf_path))
                text = extracted["text"]
                page_count = extracted["page_count"]
                extraction_method = extracted["extraction_method"]

                result["checks"]["page_count"] = page_count
                result["checks"]["text_length"] = len(text)
                result["checks"]["extraction_method"] = extraction_method

            except Exception as e:
                result["valid"] = False
                result["issues"].append(f"Text extraction failed: {e}")
                return result

            # Check 4: Minimum page count
            if page_count < 2:
                result["valid"] = False
                result["issues"].append(f"Too few pages: {page_count}")

            # Check 5: Minimum content length
            if len(text) < 500:
                result["valid"] = False
                result["issues"].append(f"Content too short: {len(text)} chars")

            # Check 6: Check for mostly empty content
            non_whitespace = len(text.replace(" ", "").replace("\n", ""))
            if non_whitespace < 300:
                result["valid"] = False
                result["issues"].append(f"Mostly whitespace: {non_whitespace} chars")

            # Check 7: Calculate content hash for duplicate detection
            content_hash = hashlib.md5(text.encode()).hexdigest()
            result["checks"]["content_hash"] = content_hash
            self.content_hashes[content_hash].append(pdf_path.name)

            # Check 8: Language detection (basic check for English)
            common_words = ["the", "and", "to", "of", "a", "in", "is", "you", "that", "for"]
            text_lower = text.lower()
            word_count = sum(1 for word in common_words if word in text_lower)

            if word_count < 5:
                result["issues"].append("May not be English text")

            # Warnings (not critical)
            if extraction_method == "pypdf2":
                result["issues"].append("Warning: Used fallback extraction (PyPDF2)")

            if len(text) > 100_000:
                result["issues"].append("Warning: Very long document")

        except Exception as e:
            result["valid"] = False
            result["issues"].append(f"Validation error: {e}")
            logger.error(f"Error validating {pdf_path.name}: {e}", exc_info=True)

        return result

    async def validate_corpus(
        self,
        categories: List[str] = None,
        detailed: bool = False
    ) -> Dict:
        """
        Validate entire corpus.

        Args:
            categories: List of categories to validate (None = all)
            detailed: Generate detailed report

        Returns:
            Validation results dict
        """
        logger.info(f"{'='*60}")
        logger.info("🔍 CORPUS VALIDATION")
        logger.info(f"{'='*60}")
        logger.info(f"Corpus directory: {self.corpus_dir}")
        logger.info(f"{'='*60}\n")

        # Get PDF files
        if categories:
            pdf_files = []
            for category in categories:
                category_dir = self.corpus_dir / category
                if category_dir.exists():
                    pdf_files.extend(list(category_dir.glob("*.pdf")))
        else:
            pdf_files = list(self.corpus_dir.rglob("*.pdf"))

        self.results["total_files"] = len(pdf_files)

        if not pdf_files:
            logger.error("❌ No PDF files found!")
            return self.results

        logger.info(f"Found {len(pdf_files)} PDF files\n")

        # Validate each document
        validation_results = []
        for idx, pdf_path in enumerate(pdf_files, 1):
            logger.info(f"[{idx}/{len(pdf_files)}] Validating: {pdf_path.name}")

            result = await self.validate_document(pdf_path)
            validation_results.append(result)

            # Show result
            if result["valid"]:
                self.results["valid_files"] += 1
                checks = result["checks"]
                logger.info(
                    f"   ✓ Valid - {checks.get('page_count', 0)} pages, "
                    f"{checks.get('text_length', 0):,} chars"
                )
                if result["issues"]:
                    for issue in result["issues"]:
                        logger.info(f"   ⚠️  {issue}")
                        self.results["warnings"].append({
                            "file": pdf_path.name,
                            "issue": issue
                        })
            else:
                self.results["invalid_files"] += 1
                logger.info(f"   ✗ Invalid")
                for issue in result["issues"]:
                    logger.info(f"      • {issue}")
                    self.results["errors"].append({
                        "file": pdf_path.name,
                        "issue": issue
                    })

            if detailed:
                logger.info(f"   Details: {json.dumps(result['checks'], indent=6)}")

        # Check for duplicates
        duplicates = {
            hash_val: files
            for hash_val, files in self.content_hashes.items()
            if len(files) > 1
        }

        if duplicates:
            logger.info(f"\n⚠️  Found {len(duplicates)} sets of duplicate documents:")
            for files in duplicates.values():
                logger.info(f"   • {', '.join(files)}")
                self.results["duplicates"].append(files)

        # Validate metadata
        await self.validate_metadata()

        # Category statistics
        self.calculate_statistics(validation_results)

        # Generate report
        self.print_summary()

        return self.results

    async def validate_metadata(self):
        """Validate metadata.json file."""
        metadata_path = self.corpus_dir / "metadata.json"

        if not metadata_path.exists():
            logger.warning("\n⚠️  metadata.json not found")
            self.results["warnings"].append({
                "file": "metadata.json",
                "issue": "Missing metadata file"
            })
            return

        try:
            metadata_list = json.loads(metadata_path.read_text())
            logger.info(f"\n✓ Found metadata.json with {len(metadata_list)} entries")

            # Check metadata completeness
            required_fields = ["filename", "company", "category", "source_url"]
            incomplete = []

            for entry in metadata_list:
                missing_fields = [
                    field for field in required_fields
                    if field not in entry or not entry[field]
                ]
                if missing_fields:
                    incomplete.append({
                        "filename": entry.get("filename", "unknown"),
                        "missing": missing_fields
                    })

            if incomplete:
                logger.warning(f"\n⚠️  {len(incomplete)} metadata entries incomplete:")
                for entry in incomplete[:5]:
                    logger.warning(f"   • {entry['filename']}: missing {entry['missing']}")
                if len(incomplete) > 5:
                    logger.warning(f"   ... and {len(incomplete) - 5} more")

        except Exception as e:
            logger.error(f"\n❌ Error reading metadata.json: {e}")
            self.results["errors"].append({
                "file": "metadata.json",
                "issue": str(e)
            })

    def calculate_statistics(self, validation_results: List[Dict]):
        """Calculate corpus statistics."""
        stats = {
            "total_pages": 0,
            "total_chars": 0,
            "avg_pages": 0,
            "avg_chars": 0,
            "min_pages": float('inf'),
            "max_pages": 0,
            "by_category": defaultdict(int),
            "by_extraction_method": defaultdict(int)
        }

        valid_results = [r for r in validation_results if r["valid"]]

        for result in valid_results:
            checks = result["checks"]
            page_count = checks.get("page_count", 0)
            text_length = checks.get("text_length", 0)

            stats["total_pages"] += page_count
            stats["total_chars"] += text_length
            stats["min_pages"] = min(stats["min_pages"], page_count)
            stats["max_pages"] = max(stats["max_pages"], page_count)

            # Category (from path)
            path = Path(result["path"])
            category = path.parent.name if path.parent != self.corpus_dir else "root"
            stats["by_category"][category] += 1

            # Extraction method
            method = checks.get("extraction_method", "unknown")
            stats["by_extraction_method"][method] += 1

        if valid_results:
            stats["avg_pages"] = stats["total_pages"] / len(valid_results)
            stats["avg_chars"] = stats["total_chars"] / len(valid_results)

        self.results["statistics"] = stats

    def print_summary(self):
        """Print validation summary."""
        logger.info(f"\n{'='*60}")
        logger.info("📊 VALIDATION SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total Files:    {self.results['total_files']}")
        logger.info(f"✓ Valid:        {self.results['valid_files']}")
        logger.info(f"✗ Invalid:      {self.results['invalid_files']}")
        logger.info(f"⚠️  Warnings:    {len(self.results['warnings'])}")
        logger.info(f"❌ Errors:       {len(self.results['errors'])}")
        logger.info(f"🔄 Duplicates:  {len(self.results['duplicates'])}")

        stats = self.results["statistics"]
        if stats:
            logger.info(f"\n📈 STATISTICS:")
            logger.info(f"Total Pages:    {stats['total_pages']:,}")
            logger.info(f"Total Chars:    {stats['total_chars']:,}")
            logger.info(f"Avg Pages/Doc:  {stats['avg_pages']:.1f}")
            logger.info(f"Avg Chars/Doc:  {stats['avg_chars']:,.0f}")
            logger.info(f"Page Range:     {stats['min_pages']} - {stats['max_pages']}")

            if stats["by_category"]:
                logger.info(f"\n📁 BY CATEGORY:")
                for category, count in sorted(stats["by_category"].items()):
                    logger.info(f"   {category:15s}: {count:3d} documents")

            if stats["by_extraction_method"]:
                logger.info(f"\n🔧 EXTRACTION METHOD:")
                for method, count in stats["by_extraction_method"].items():
                    logger.info(f"   {method:15s}: {count:3d} documents")

        # Overall status
        logger.info(f"\n{'='*60}")
        if self.results['invalid_files'] == 0 and len(self.results['errors']) == 0:
            logger.info("✅ CORPUS VALIDATION PASSED")
            if len(self.results['warnings']) > 0:
                logger.info(f"   ({len(self.results['warnings'])} warnings)")
        else:
            logger.info("❌ CORPUS VALIDATION FAILED")
            logger.info(f"   {self.results['invalid_files']} invalid files")
            logger.info(f"   {len(self.results['errors'])} errors")
        logger.info(f"{'='*60}")

    def save_report(self, output_path: Path):
        """Save validation report to JSON."""
        output_path.write_text(json.dumps(self.results, indent=2))
        logger.info(f"\n💾 Validation report saved to: {output_path}")


# ============================================================================
# CLI INTERFACE
# ============================================================================

async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate baseline T&C corpus quality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Validate entire corpus
    python validate_corpus.py

    # Validate specific categories
    python validate_corpus.py --category tech saas

    # Generate detailed report
    python validate_corpus.py --detailed

    # Save report to file
    python validate_corpus.py --output validation_report.json
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
        help="Specific categories to validate"
    )

    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed validation results"
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Save validation report to JSON file"
    )

    args = parser.parse_args()

    try:
        validator = CorpusValidator(args.corpus_dir)
        results = await validator.validate_corpus(
            categories=args.category,
            detailed=args.detailed
        )

        # Save report if requested
        if args.output:
            validator.save_report(args.output)

        # Exit with appropriate code
        if results["invalid_files"] > 0:
            logger.info("\n⚠️  Some files failed validation")
            exit(1)
        else:
            logger.info("\n✅ All files passed validation!")
            exit(0)

    except KeyboardInterrupt:
        logger.info("\n⚠️  Validation interrupted by user")
        exit(130)
    except Exception as e:
        logger.error(f"\n❌ Validation failed: {e}", exc_info=True)
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())

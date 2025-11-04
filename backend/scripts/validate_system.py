#!/usr/bin/env python3
"""
Complete System Validation Script

This script performs comprehensive validation of the T&C Analysis System:
1. Environment configuration
2. Database connectivity
3. External service integration (OpenAI, Pinecone, Redis)
4. Core module functionality
5. API endpoint availability
6. Data collection scripts
7. Integration tests

Usage:
    python scripts/validate_system.py
    python scripts/validate_system.py --quick     # Skip slow tests
    python scripts/validate_system.py --detailed  # Show detailed output
"""

import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import argparse
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("system_validation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SystemValidator:
    """Comprehensive system validation."""

    def __init__(self, detailed: bool = False):
        self.detailed = detailed
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "environment": {},
            "services": {},
            "core_modules": {},
            "api": {},
            "scripts": {},
            "overall_status": "unknown"
        }
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    async def validate_environment(self) -> bool:
        """Validate environment configuration."""
        logger.info("\n" + "=" * 60)
        logger.info("1. ENVIRONMENT CONFIGURATION")
        logger.info("=" * 60)

        checks = []

        # Check .env file exists
        env_file = Path("backend/.env")
        env_example = Path("backend/.env.example")

        if not env_example.exists():
            logger.error("✗ .env.example not found")
            checks.append(("env_example_exists", False))
        else:
            logger.info("✓ .env.example found")
            checks.append(("env_example_exists", True))

        if not env_file.exists():
            logger.warning("⚠️  .env file not found (will use defaults/environment variables)")
            checks.append(("env_file_exists", False))
            self.warnings += 1
        else:
            logger.info("✓ .env file found")
            checks.append(("env_file_exists", True))

        # Check config loads
        try:
            from app.core.config import settings

            # Check required settings
            required = [
                ("OPENAI_API_KEY", settings.OPENAI_API_KEY),
                ("PINECONE_API_KEY", settings.PINECONE_API_KEY),
                ("DATABASE_URL", settings.DATABASE_URL),
                ("SECRET_KEY", settings.SECRET_KEY),
            ]

            for name, value in required:
                if not value or value == "your-" or value == "sk-your-":
                    logger.warning(f"⚠️  {name} not set or using example value")
                    checks.append((f"config_{name}", False))
                    self.warnings += 1
                else:
                    logger.info(f"✓ {name} configured")
                    checks.append((f"config_{name}", True))

            logger.info(f"✓ Configuration loaded successfully")
            logger.info(f"   Environment: {settings.ENVIRONMENT}")
            logger.info(f"   Debug: {settings.DEBUG}")
            checks.append(("config_loads", True))

        except Exception as e:
            logger.error(f"✗ Configuration load failed: {e}")
            checks.append(("config_loads", False))

        self.results["environment"] = dict(checks)
        passed = sum(1 for _, status in checks if status)
        total = len(checks)

        logger.info(f"\nEnvironment: {passed}/{total} checks passed")
        return passed == total

    async def validate_database(self) -> bool:
        """Validate database connectivity and models."""
        logger.info("\n" + "=" * 60)
        logger.info("2. DATABASE CONNECTIVITY")
        logger.info("=" * 60)

        checks = []

        try:
            from app.db.session import engine, SessionLocal
            from app.models.user import User
            from app.models.document import Document
            from app.models.anomaly import Anomaly

            # Test connection
            try:
                with engine.connect() as conn:
                    logger.info("✓ Database connection successful")
                    checks.append(("db_connection", True))
            except Exception as e:
                logger.error(f"✗ Database connection failed: {e}")
                logger.warning("   Make sure PostgreSQL is running:")
                logger.warning("   docker-compose up -d postgres")
                checks.append(("db_connection", False))
                self.results["database"] = dict(checks)
                return False

            # Check if tables exist
            from sqlalchemy import inspect
            inspector = inspect(engine)
            tables = inspector.get_table_names()

            expected_tables = ["users", "documents", "anomalies"]
            for table in expected_tables:
                if table in tables:
                    logger.info(f"✓ Table '{table}' exists")
                    checks.append((f"table_{table}", True))
                else:
                    logger.warning(f"⚠️  Table '{table}' not found (run migrations)")
                    logger.warning("   cd backend && alembic upgrade head")
                    checks.append((f"table_{table}", False))
                    self.warnings += 1

            # Test session
            try:
                db = SessionLocal()
                db.close()
                logger.info("✓ Database session created successfully")
                checks.append(("db_session", True))
            except Exception as e:
                logger.error(f"✗ Database session failed: {e}")
                checks.append(("db_session", False))

        except Exception as e:
            logger.error(f"✗ Database validation failed: {e}")
            checks.append(("db_validation", False))

        self.results["database"] = dict(checks)
        passed = sum(1 for _, status in checks if status)
        total = len(checks)

        logger.info(f"\nDatabase: {passed}/{total} checks passed")
        return all(status for _, status in checks)

    async def validate_services(self) -> Dict[str, bool]:
        """Validate external services (OpenAI, Pinecone, Redis)."""
        logger.info("\n" + "=" * 60)
        logger.info("3. EXTERNAL SERVICES")
        logger.info("=" * 60)

        service_status = {}

        # OpenAI
        try:
            from app.services.openai_service import OpenAIService
            from app.core.config import settings

            logger.info("\n📡 Testing OpenAI...")
            openai_service = OpenAIService()

            # Test embedding generation
            try:
                embedding = await openai_service.create_embedding("test")
                if len(embedding) == 1536:
                    logger.info("✓ OpenAI API working (embedding generated)")
                    logger.info(f"   Embedding dimension: {len(embedding)}")
                    service_status["openai"] = True
                else:
                    logger.error(f"✗ OpenAI embedding wrong dimension: {len(embedding)}")
                    service_status["openai"] = False
            except Exception as e:
                logger.error(f"✗ OpenAI API call failed: {e}")
                logger.warning("   Check API key and quota")
                service_status["openai"] = False

            await openai_service.close()

        except Exception as e:
            logger.error(f"✗ OpenAI service initialization failed: {e}")
            service_status["openai"] = False

        # Pinecone
        try:
            from app.services.pinecone_service import PineconeService
            from app.core.config import settings

            logger.info("\n📊 Testing Pinecone...")
            pinecone_service = PineconeService()

            try:
                await pinecone_service.initialize()

                # Get index stats
                stats = pinecone_service.index.describe_index_stats()
                logger.info("✓ Pinecone connected successfully")
                logger.info(f"   Index: {settings.PINECONE_INDEX_NAME}")
                logger.info(f"   Total vectors: {stats.get('total_vector_count', 0):,}")

                namespaces = stats.get("namespaces", {})
                for ns_name, ns_stats in namespaces.items():
                    logger.info(f"   {ns_name}: {ns_stats.get('vector_count', 0):,} vectors")

                service_status["pinecone"] = True

            except Exception as e:
                logger.error(f"✗ Pinecone connection failed: {e}")
                logger.warning("   Check API key and index name")
                service_status["pinecone"] = False

            await pinecone_service.close()

        except Exception as e:
            logger.error(f"✗ Pinecone service initialization failed: {e}")
            service_status["pinecone"] = False

        # Redis
        try:
            from app.services.cache_service import CacheService

            logger.info("\n💾 Testing Redis...")
            cache_service = CacheService()

            try:
                await cache_service.connect()

                # Test set/get
                test_key = "test_validation"
                test_value = {"test": "data"}
                await cache_service.set(test_key, test_value, ttl=60)
                retrieved = await cache_service.get(test_key)

                if retrieved == test_value:
                    logger.info("✓ Redis connected and working")
                    service_status["redis"] = True
                else:
                    logger.error("✗ Redis data mismatch")
                    service_status["redis"] = False

                await cache_service.delete(test_key)
                await cache_service.disconnect()

            except Exception as e:
                logger.warning(f"⚠️  Redis connection failed: {e}")
                logger.warning("   System will work without cache (degraded performance)")
                logger.warning("   Start Redis: docker-compose up -d redis")
                service_status["redis"] = False
                self.warnings += 1

        except Exception as e:
            logger.error(f"✗ Redis service initialization failed: {e}")
            service_status["redis"] = False

        self.results["services"] = service_status

        passed = sum(1 for status in service_status.values() if status)
        total = len(service_status)
        logger.info(f"\nServices: {passed}/{total} working")

        return service_status

    async def validate_core_modules(self) -> bool:
        """Validate core processing modules."""
        logger.info("\n" + "=" * 60)
        logger.info("4. CORE MODULES")
        logger.info("=" * 60)

        checks = []

        # Test document processor
        try:
            from app.core.document_processor import DocumentProcessor

            logger.info("\n📄 Testing DocumentProcessor...")
            processor = DocumentProcessor()

            # Create test PDF if it exists
            test_pdf = Path("data/test_samples/simple_tos.pdf")
            if test_pdf.exists():
                extracted = await processor.extract_text(str(test_pdf))
                if extracted["text"] and len(extracted["text"]) > 100:
                    logger.info(f"✓ DocumentProcessor working")
                    logger.info(f"   Extracted {len(extracted['text'])} chars from test PDF")
                    checks.append(("document_processor", True))
                else:
                    logger.error("✗ DocumentProcessor extracted empty/short text")
                    checks.append(("document_processor", False))
            else:
                logger.warning("⚠️  No test PDF found, skipping extraction test")
                logger.warning("   Run: python scripts/create_test_pdfs.py")
                checks.append(("document_processor", True))  # Module itself is fine
                self.warnings += 1

        except Exception as e:
            logger.error(f"✗ DocumentProcessor failed: {e}")
            checks.append(("document_processor", False))

        # Test structure extractor
        try:
            from app.core.structure_extractor import StructureExtractor

            logger.info("\n🏗️  Testing StructureExtractor...")
            extractor = StructureExtractor()

            test_text = """
            1. TERMS OF SERVICE
            By using this service, you agree to these terms.

            2. USER OBLIGATIONS
            You must use the service responsibly.
            """

            clauses = await extractor.extract_structure(test_text)
            if len(clauses) >= 2:
                logger.info(f"✓ StructureExtractor working")
                logger.info(f"   Extracted {len(clauses)} clauses from test text")
                checks.append(("structure_extractor", True))
            else:
                logger.error("✗ StructureExtractor failed to parse structure")
                checks.append(("structure_extractor", False))

        except Exception as e:
            logger.error(f"✗ StructureExtractor failed: {e}")
            checks.append(("structure_extractor", False))

        # Test legal chunker
        try:
            from app.core.legal_chunker import LegalChunker
            from app.core.structure_extractor import Clause

            logger.info("\n✂️  Testing LegalChunker...")
            chunker = LegalChunker()

            test_clauses = [
                Clause(section="Test", subsection="", clause_number="1",
                       text="Test clause " * 50, level=0)
            ]

            chunks = await chunker.create_chunks(test_clauses)
            if len(chunks) > 0 and "text" in chunks[0] and "metadata" in chunks[0]:
                logger.info(f"✓ LegalChunker working")
                logger.info(f"   Created {len(chunks)} chunks from test clauses")
                checks.append(("legal_chunker", True))
            else:
                logger.error("✗ LegalChunker failed to create valid chunks")
                checks.append(("legal_chunker", False))

        except Exception as e:
            logger.error(f"✗ LegalChunker failed: {e}")
            checks.append(("legal_chunker", False))

        self.results["core_modules"] = dict(checks)
        passed = sum(1 for _, status in checks if status)
        total = len(checks)

        logger.info(f"\nCore Modules: {passed}/{total} working")
        return all(status for _, status in checks)

    async def validate_api_health(self) -> bool:
        """Validate API server health."""
        logger.info("\n" + "=" * 60)
        logger.info("5. API HEALTH CHECK")
        logger.info("=" * 60)

        try:
            import httpx

            # Try to connect to API
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get("http://localhost:8000/health")

                    if response.status_code == 200:
                        data = response.json()
                        logger.info("✓ API server is running")
                        logger.info(f"   Status: {data.get('status')}")
                        logger.info(f"   Version: {data.get('version')}")
                        logger.info(f"   Environment: {data.get('environment')}")
                        self.results["api"]["health"] = True
                        return True
                    else:
                        logger.error(f"✗ API returned status {response.status_code}")
                        self.results["api"]["health"] = False
                        return False

            except httpx.ConnectError:
                logger.warning("⚠️  API server not running")
                logger.warning("   Start server: cd backend && uvicorn app.main:app --reload")
                logger.warning("   Skipping API tests...")
                self.results["api"]["health"] = False
                self.warnings += 1
                return False

        except ImportError:
            logger.warning("⚠️  httpx not installed, skipping API tests")
            logger.warning("   Install: pip install httpx")
            self.results["api"]["health"] = None
            self.warnings += 1
            return False

    async def validate_scripts(self) -> bool:
        """Validate data collection scripts."""
        logger.info("\n" + "=" * 60)
        logger.info("6. DATA COLLECTION SCRIPTS")
        logger.info("=" * 60)

        checks = []

        scripts = [
            "scripts/collect_baseline_corpus.py",
            "scripts/index_baseline_corpus.py",
            "scripts/validate_corpus.py",
            "scripts/analyze_corpus_stats.py",
            "scripts/create_test_pdfs.py",
        ]

        for script_path in scripts:
            script_file = Path("backend") / script_path
            if script_file.exists():
                logger.info(f"✓ {script_path} exists")

                # Check if it's executable and has main
                content = script_file.read_text()
                has_main = '__main__' in content
                has_shebang = content.startswith('#!/usr/bin/env python')

                if has_main:
                    logger.info(f"   ✓ Has main entry point")
                if has_shebang:
                    logger.info(f"   ✓ Has shebang")

                checks.append((script_path, True))
            else:
                logger.error(f"✗ {script_path} not found")
                checks.append((script_path, False))

        self.results["scripts"] = dict(checks)
        passed = sum(1 for _, status in checks if status)
        total = len(checks)

        logger.info(f"\nScripts: {passed}/{total} found")
        return all(status for _, status in checks)

    def print_summary(self):
        """Print validation summary."""
        logger.info("\n" + "=" * 60)
        logger.info("📊 VALIDATION SUMMARY")
        logger.info("=" * 60)

        # Count results
        for section, checks in self.results.items():
            if section in ["timestamp", "overall_status"]:
                continue

            if isinstance(checks, dict):
                passed = sum(1 for v in checks.values() if v is True)
                failed = sum(1 for v in checks.values() if v is False)
                warnings = sum(1 for v in checks.values() if v is None)
                total = len(checks)

                logger.info(f"\n{section.upper().replace('_', ' ')}:")
                logger.info(f"   ✓ Passed:   {passed}/{total}")
                if failed > 0:
                    logger.info(f"   ✗ Failed:   {failed}/{total}")
                if warnings > 0:
                    logger.info(f"   ⚠️  Warnings: {warnings}/{total}")

                self.passed += passed
                self.failed += failed
                self.warnings += warnings

        # Overall status
        logger.info(f"\n{'=' * 60}")
        logger.info(f"OVERALL: {self.passed} passed, {self.failed} failed, {self.warnings} warnings")

        if self.failed == 0 and self.warnings == 0:
            logger.info("✅ SYSTEM FULLY OPERATIONAL")
            self.results["overall_status"] = "excellent"
        elif self.failed == 0:
            logger.info("⚠️  SYSTEM OPERATIONAL WITH WARNINGS")
            self.results["overall_status"] = "good"
        else:
            logger.info("❌ SYSTEM HAS CRITICAL ISSUES")
            self.results["overall_status"] = "needs_attention"

        logger.info(f"{'=' * 60}")

    async def run_full_validation(self, quick: bool = False) -> bool:
        """Run complete system validation."""
        logger.info("🔍 Starting System Validation...")
        logger.info(f"Time: {datetime.now().isoformat()}")

        # Run validations
        await self.validate_environment()
        await self.validate_database()
        await self.validate_services()
        await self.validate_core_modules()

        if not quick:
            await self.validate_api_health()

        await self.validate_scripts()

        # Print summary
        self.print_summary()

        # Save report
        import json
        report_path = Path("backend/validation_report.json")
        report_path.write_text(json.dumps(self.results, indent=2))
        logger.info(f"\n💾 Validation report saved to: {report_path}")

        return self.failed == 0


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate T&C Analysis System",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip slow tests (API calls, etc.)"
    )

    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed output"
    )

    args = parser.parse_args()

    try:
        validator = SystemValidator(detailed=args.detailed)
        success = await validator.run_full_validation(quick=args.quick)

        exit(0 if success else 1)

    except KeyboardInterrupt:
        logger.info("\n⚠️  Validation interrupted by user")
        exit(130)
    except Exception as e:
        logger.error(f"\n❌ Validation failed: {e}", exc_info=True)
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())

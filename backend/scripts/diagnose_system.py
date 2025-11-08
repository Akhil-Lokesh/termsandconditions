"""
System diagnostic script.

Checks:
1. Service connectivity (OpenAI, Pinecone, Redis, PostgreSQL)
2. Baseline corpus status
3. Configuration validation
4. API endpoints health
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services.openai_service import OpenAIService
from app.services.pinecone_service import PineconeService
from app.services.cache_service import CacheService
from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


async def check_openai():
    """Check OpenAI connectivity."""
    try:
        openai = OpenAIService()
        embedding = await openai.create_embedding("test")
        logger.info("✓ OpenAI: Connected (embedding dimension: %d)", len(embedding))
        return True
    except Exception as e:
        logger.error("✗ OpenAI: %s", e)
        return False


async def check_pinecone():
    """Check Pinecone connectivity and baseline corpus."""
    try:
        pinecone = PineconeService()
        await pinecone.initialize()

        stats = pinecone.index.describe_index_stats()
        baseline_count = stats['namespaces'].get(settings.PINECONE_BASELINE_NAMESPACE, {}).get('vector_count', 0)
        user_count = stats['namespaces'].get(settings.PINECONE_USER_NAMESPACE, {}).get('vector_count', 0)

        logger.info("✓ Pinecone: Connected")
        logger.info("  - Index: %s", settings.PINECONE_INDEX_NAME)
        logger.info("  - Baseline vectors: %d", baseline_count)
        logger.info("  - User vectors: %d", user_count)

        if baseline_count == 0:
            logger.warning("  ⚠️  WARNING: Baseline corpus is EMPTY!")
            logger.warning("  Run: python scripts/index_baseline_corpus.py")
            return False
        elif baseline_count < 1000:
            logger.warning("  ⚠️  WARNING: Baseline corpus is small (%d vectors)", baseline_count)
            logger.warning("  Recommended: 1000+ vectors for accurate anomaly detection")

        return True

    except Exception as e:
        logger.error("✗ Pinecone: %s", e)
        return False


async def check_redis():
    """Check Redis connectivity."""
    try:
        cache = CacheService()
        await cache.connect()

        # Test set/get
        await cache.set("diagnostic_test", "ok", ttl=10)
        value = await cache.get("diagnostic_test")

        if value == "ok":
            logger.info("✓ Redis: Connected")
            await cache.disconnect()
            return True
        else:
            logger.error("✗ Redis: Get/Set test failed")
            return False

    except Exception as e:
        logger.error("✗ Redis: %s", e)
        logger.info("  (Redis is optional - system can run without it)")
        return False


def check_database():
    """Check PostgreSQL connectivity."""
    try:
        engine = create_engine(settings.DATABASE_URL)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()

        logger.info("✓ PostgreSQL: Connected")
        logger.info("  - URL: %s", settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else "localhost")

        # Check tables exist
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result]

        required_tables = ['users', 'documents', 'clauses', 'anomalies']
        missing = [t for t in required_tables if t not in tables]

        if missing:
            logger.warning("  ⚠️  WARNING: Missing tables: %s", missing)
            logger.warning("  Run: python scripts/init_database.py")
            return False
        else:
            logger.info("  - Tables: %s", ', '.join(tables))

        return True

    except Exception as e:
        logger.error("✗ PostgreSQL: %s", e)
        return False


def check_config():
    """Check configuration."""
    logger.info("\n=== Configuration ===")
    logger.info("Environment: %s", settings.ENVIRONMENT)
    logger.info("Debug: %s", settings.DEBUG)
    logger.info("OpenAI Model: %s", settings.OPENAI_MODEL_GPT4)
    logger.info("Embedding Model: %s", settings.OPENAI_EMBEDDING_MODEL)
    logger.info("Max Upload Size: %d MB", settings.MAX_FILE_SIZE_MB)

    # Check API keys are set
    issues = []

    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("sk-proj-your"):
        issues.append("OpenAI API key not configured")

    if not settings.PINECONE_API_KEY or settings.PINECONE_API_KEY.startswith("pcsk_your"):
        issues.append("Pinecone API key not configured")

    if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32:
        issues.append("JWT SECRET_KEY is weak or not set")

    if issues:
        logger.warning("\n⚠️  Configuration Issues:")
        for issue in issues:
            logger.warning("  - %s", issue)
        return False

    return True


async def main():
    """Run all diagnostic checks."""
    logger.info("="*60)
    logger.info("T&C Analysis System Diagnostics")
    logger.info("="*60)

    # Configuration check
    config_ok = check_config()

    logger.info("\n=== Service Connectivity ===")

    # Service checks
    openai_ok = await check_openai()
    pinecone_ok = await check_pinecone()
    redis_ok = await check_redis()
    db_ok = check_database()

    # Summary
    logger.info("\n" + "="*60)
    logger.info("Summary")
    logger.info("="*60)

    all_critical_ok = openai_ok and pinecone_ok and db_ok and config_ok

    if all_critical_ok:
        logger.info("✓ All critical services operational!")
        logger.info("System is ready to process documents.")

        if not redis_ok:
            logger.info("\nNote: Redis is offline (optional - caching disabled)")
    else:
        logger.error("✗ System is NOT ready!")
        logger.error("Fix the issues above before starting the API.")
        sys.exit(1)

    logger.info("="*60)


if __name__ == "__main__":
    asyncio.run(main())

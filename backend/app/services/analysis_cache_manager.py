"""
Cache manager for GPT-5 analysis results.

Caches analysis results to avoid redundant API calls for:
- Duplicate documents (same text hash)
- Recently analyzed documents
- Frequently accessed results

Expected cache hit rate: 15-25% for typical usage.
Additional cost savings: ~20% on top of two-stage savings.
"""

import hashlib
import json
from typing import Optional, Dict, Any
from datetime import timedelta
import logging

from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class AnalysisCacheManager:
    """
    Manages caching of GPT-5 analysis results.

    Cache strategy:
    - Key: Hash of document text
    - Value: Full analysis result (JSON)
    - TTL: 7 days (results remain valid for reasonable time)
    - Invalidation: Manual or on document update
    """

    # Cache TTLs
    ANALYSIS_RESULT_TTL = timedelta(days=7)  # 7 days for analysis results
    DOCUMENT_HASH_TTL = timedelta(days=30)  # 30 days for document hashes

    # Cache key prefixes
    PREFIX_ANALYSIS = "gpt5:analysis:"
    PREFIX_HASH = "gpt5:hash:"
    PREFIX_STATS = "gpt5:stats:"

    def __init__(self, cache_service: Optional[CacheService] = None):
        """
        Initialize cache manager.

        Args:
            cache_service: Optional cache service instance (Redis)
        """
        self.cache = cache_service or CacheService()
        self.cache_hits = 0
        self.cache_misses = 0

        logger.info("Initialized AnalysisCacheManager")

    def _hash_document(self, document_text: str) -> str:
        """
        Generate consistent hash for document text.

        Uses SHA-256 to create unique identifier for content.
        Same text = same hash = cache hit.
        """
        # Normalize text (remove extra whitespace, lowercase)
        normalized = " ".join(document_text.lower().split())

        # Generate hash
        return hashlib.sha256(normalized.encode()).hexdigest()

    async def get_cached_analysis(
        self,
        document_text: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached analysis result if available.

        Args:
            document_text: Full text of document

        Returns:
            Cached analysis result or None if not found
        """
        # Generate document hash
        doc_hash = self._hash_document(document_text)
        cache_key = f"{self.PREFIX_ANALYSIS}{doc_hash}"

        try:
            # Try to get from cache
            cached_data = await self.cache.get(cache_key)

            if cached_data:
                self.cache_hits += 1
                logger.info(f"Cache HIT for document hash {doc_hash[:16]}...")

                # Parse JSON
                result = json.loads(cached_data) if isinstance(cached_data, str) else cached_data

                # Add cache metadata
                result["from_cache"] = True
                result["cache_hit"] = True

                return result

            else:
                self.cache_misses += 1
                logger.info(f"Cache MISS for document hash {doc_hash[:16]}...")
                return None

        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
            self.cache_misses += 1
            return None

    async def cache_analysis_result(
        self,
        document_text: str,
        analysis_result: Dict[str, Any]
    ):
        """
        Cache analysis result for future use.

        Args:
            document_text: Full text of document
            analysis_result: Analysis result to cache
        """
        # Generate document hash
        doc_hash = self._hash_document(document_text)
        cache_key = f"{self.PREFIX_ANALYSIS}{doc_hash}"

        try:
            # Add cache metadata
            result_to_cache = analysis_result.copy()
            result_to_cache["cached_at"] = result_to_cache.get("timestamp")
            result_to_cache["document_hash"] = doc_hash

            # Serialize to JSON
            cached_data = json.dumps(result_to_cache)

            # Store in cache with TTL
            await self.cache.set(
                cache_key,
                cached_data,
                ttl=int(self.ANALYSIS_RESULT_TTL.total_seconds())
            )

            logger.info(
                f"Cached analysis result for {doc_hash[:16]}... "
                f"(TTL: {self.ANALYSIS_RESULT_TTL.days} days)"
            )

        except Exception as e:
            logger.error(f"Cache storage error: {e}")

    async def invalidate_document_cache(
        self,
        document_text: str
    ):
        """
        Invalidate cached analysis for a document.

        Useful when document is updated or analysis needs to be re-run.
        """
        doc_hash = self._hash_document(document_text)
        cache_key = f"{self.PREFIX_ANALYSIS}{doc_hash}"

        try:
            await self.cache.delete(cache_key)
            logger.info(f"Invalidated cache for document {doc_hash[:16]}...")

        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.

        Returns:
            Dict with cache hit rate and other metrics
        """
        total_requests = self.cache_hits + self.cache_misses

        if total_requests == 0:
            hit_rate = 0.0
        else:
            hit_rate = (self.cache_hits / total_requests) * 100

        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 1),
            "target_hit_rate": "15-25%",
            "estimated_cost_savings": self._estimate_cost_savings()
        }

    def _estimate_cost_savings(self) -> float:
        """
        Estimate cost savings from cache hits.

        Assumes average cost of $0.0039/doc (blended two-stage).
        """
        average_cost_per_analysis = 0.0039
        savings = self.cache_hits * average_cost_per_analysis
        return round(savings, 4)

    def reset_stats(self):
        """Reset cache statistics (for testing or periodic resets)."""
        self.cache_hits = 0
        self.cache_misses = 0
        logger.info("Cache statistics reset")


class SmartCacheStrategy:
    """
    Advanced caching strategy with intelligent cache decisions.

    Decides when to cache based on:
    - Document length (don't cache very short docs)
    - Analysis cost (cache expensive Stage 2 results more aggressively)
    - Confidence (cache high-confidence results longer)
    """

    MIN_DOCUMENT_LENGTH = 1000  # Don't cache docs < 1000 chars
    HIGH_COST_THRESHOLD = 0.010  # Cache more aggressively if cost > $0.01
    HIGH_CONFIDENCE_THRESHOLD = 0.85  # Longer TTL for high confidence

    @staticmethod
    def should_cache(
        document_text: str,
        analysis_result: Dict[str, Any]
    ) -> bool:
        """
        Decide if result should be cached.

        Args:
            document_text: Document text
            analysis_result: Analysis result

        Returns:
            True if should cache, False otherwise
        """
        # Don't cache very short documents
        if len(document_text) < SmartCacheStrategy.MIN_DOCUMENT_LENGTH:
            logger.debug("Skipping cache: document too short")
            return False

        # Always cache expensive analyses (Stage 2)
        if analysis_result.get("cost", 0) > SmartCacheStrategy.HIGH_COST_THRESHOLD:
            logger.debug("Caching: expensive analysis")
            return True

        # Cache high-confidence results
        if analysis_result.get("confidence", 0) > SmartCacheStrategy.HIGH_CONFIDENCE_THRESHOLD:
            logger.debug("Caching: high confidence result")
            return True

        # Default: cache most results
        return True

    @staticmethod
    def get_ttl(
        analysis_result: Dict[str, Any]
    ) -> int:
        """
        Get appropriate TTL based on result characteristics.

        Args:
            analysis_result: Analysis result

        Returns:
            TTL in seconds
        """
        base_ttl = 7 * 24 * 60 * 60  # 7 days

        # Longer TTL for high-confidence results
        if analysis_result.get("confidence", 0) > SmartCacheStrategy.HIGH_CONFIDENCE_THRESHOLD:
            return base_ttl * 2  # 14 days

        # Longer TTL for expensive analyses
        if analysis_result.get("stage", 1) == 2:
            return base_ttl * 2  # 14 days

        return base_ttl


# Global cache manager instance
analysis_cache = AnalysisCacheManager()

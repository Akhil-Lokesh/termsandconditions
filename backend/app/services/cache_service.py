"""
Redis cache service for expensive operations.

Provides methods for:
- Connection management
- Get/set operations with TTL
- Embedding caching
- Query result caching
- JSON serialization
"""

import json
import logging
from typing import Any, Optional
import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.utils.exceptions import CacheServiceError

logger = logging.getLogger(__name__)


class CacheService:
    """Redis cache service for caching expensive operations."""

    def __init__(self):
        """Initialize cache service (connection happens in connect())."""
        self.client: Optional[Redis] = None
        self.default_ttl = settings.CACHE_TTL

    async def connect(self):
        """
        Connect to Redis server.

        This should be called during application startup.

        Raises:
            CacheServiceError: If connection fails
        """
        try:
            logger.info("Connecting to Redis...")

            self.client = await redis.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                encoding="utf-8",
                decode_responses=True,
            )

            # Test connection
            await self.client.ping()
            logger.info("Redis connection established successfully")

        except RedisError as e:
            logger.error(f"Redis connection error: {e}")
            raise CacheServiceError(f"Failed to connect to Redis: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {e}", exc_info=True)
            raise CacheServiceError(f"Unexpected error: {str(e)}") from e

    async def disconnect(self):
        """Disconnect from Redis server."""
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value (deserialized from JSON) or None if not found

        Raises:
            CacheServiceError: If get operation fails
        """
        if not self.client:
            logger.warning("Cache not connected, skipping get")
            return None

        try:
            value = await self.client.get(key)

            if value is None:
                logger.debug(f"Cache miss: {key}")
                return None

            # Deserialize JSON
            deserialized = json.loads(value)
            logger.debug(f"Cache hit: {key}")
            return deserialized

        except RedisError as e:
            logger.error(f"Redis get error for key '{key}': {e}")
            # Don't raise - cache failures shouldn't break the app
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for key '{key}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during get for key '{key}': {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time-to-live in seconds (uses default if not specified)

        Returns:
            True if successful, False otherwise

        Raises:
            CacheServiceError: If set operation fails critically
        """
        if not self.client:
            logger.warning("Cache not connected, skipping set")
            return False

        try:
            # Serialize to JSON
            serialized = json.dumps(value)

            # Set with TTL
            ttl = ttl or self.default_ttl
            await self.client.setex(key, ttl, serialized)

            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            return True

        except RedisError as e:
            logger.error(f"Redis set error for key '{key}': {e}")
            # Don't raise - cache failures shouldn't break the app
            return False
        except (TypeError, ValueError) as e:
            logger.error(f"JSON serialization error for key '{key}': {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during set for key '{key}': {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False otherwise
        """
        if not self.client:
            logger.warning("Cache not connected, skipping delete")
            return False

        try:
            result = await self.client.delete(key)
            logger.debug(f"Cache delete: {key} (existed: {bool(result)})")
            return bool(result)

        except RedisError as e:
            logger.error(f"Redis delete error for key '{key}': {e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        if not self.client:
            return False

        try:
            result = await self.client.exists(key)
            return bool(result)

        except RedisError as e:
            logger.error(f"Redis exists error for key '{key}': {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Key pattern (e.g., "embedding:*")

        Returns:
            Number of keys deleted

        Example:
            await cache.clear_pattern("embedding:*")  # Clear all embeddings
        """
        if not self.client:
            logger.warning("Cache not connected, skipping clear_pattern")
            return 0

        try:
            # Find matching keys
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)

            if not keys:
                logger.debug(f"No keys matching pattern: {pattern}")
                return 0

            # Delete all matching keys
            deleted = await self.client.delete(*keys)
            logger.info(f"Cleared {deleted} keys matching pattern: {pattern}")
            return deleted

        except RedisError as e:
            logger.error(f"Redis clear_pattern error for pattern '{pattern}': {e}")
            return 0

    async def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats (memory usage, keys, etc.)
        """
        if not self.client:
            return {"status": "disconnected"}

        try:
            info = await self.client.info()
            stats = {
                "status": "connected",
                "used_memory": info.get("used_memory_human", "unknown"),
                "total_keys": await self.client.dbsize(),
                "connected_clients": info.get("connected_clients", 0),
                "uptime_seconds": info.get("uptime_in_seconds", 0),
            }
            return stats

        except RedisError as e:
            logger.error(f"Redis stats error: {e}")
            return {"status": "error", "error": str(e)}

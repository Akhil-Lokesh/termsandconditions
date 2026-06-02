"""Shared SlowAPI rate limiter instance.

Import this in route modules to apply @limiter.limit() decorators.
The instance is registered on app.state in main.py lifespan.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# Use a shared storage backend (e.g. Redis) when configured so rate limits are
# enforced across all worker processes / instances. When unset, SlowAPI falls
# back to in-process memory — correct for a single worker, but each process
# keeps its OWN counters, so N workers effectively allow N× the configured rate.
_limiter_kwargs = {
    "key_func": get_remote_address,
    "default_limits": [f"{settings.RATE_LIMIT_PER_HOUR}/hour"],
}
if settings.RATE_LIMIT_STORAGE_URI:
    _limiter_kwargs["storage_uri"] = settings.RATE_LIMIT_STORAGE_URI

limiter = Limiter(**_limiter_kwargs)

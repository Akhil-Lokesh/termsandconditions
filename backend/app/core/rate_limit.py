"""Shared SlowAPI rate limiter instance.

Import this in route modules to apply @limiter.limit() decorators.
The instance is registered on app.state in main.py lifespan.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_HOUR}/hour"],
)

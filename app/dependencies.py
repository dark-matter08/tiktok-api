"""Authentication and rate limiting dependencies."""

import logging
from typing import List

from fastapi import Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# API Key configuration
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def get_api_key(api_key: str = Security(api_key_header)) -> str:
    """Validate API key from request headers."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Please provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    settings = get_settings()
    if api_key not in settings.api_keys_list:
        logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key. Access denied.",
        )

    logger.debug(f"Valid API key used: {api_key[:10]}...")
    return api_key


def get_rate_limiter() -> Limiter:
    """Get the rate limiter instance."""
    return limiter


def get_rate_limit_exceeded_handler():
    """Get the rate limit exceeded handler."""
    return _rate_limit_exceeded_handler


# Rate limiting decorators for different endpoints
def rate_limit_trending():
    """Rate limit for trending endpoints (higher limit)."""
    return limiter.limit("200/minute")


def rate_limit_user():
    """Rate limit for user endpoints."""
    return limiter.limit("100/minute")


def rate_limit_video():
    """Rate limit for video endpoints."""
    return limiter.limit("150/minute")


def rate_limit_hashtag():
    """Rate limit for hashtag endpoints."""
    return limiter.limit("100/minute")


def rate_limit_search():
    """Rate limit for search endpoints (lower limit due to complexity)."""
    return limiter.limit("50/minute")


def rate_limit_sound():
    """Rate limit for sound endpoints."""
    return limiter.limit("100/minute")


def rate_limit_health():
    """Rate limit for health check endpoint (very high limit)."""
    return limiter.limit("1000/minute")


# Authentication dependency that can be used with rate limiting
def get_authenticated_user(api_key: str = Depends(get_api_key)) -> str:
    """Get authenticated user (API key)."""
    return api_key


# Combined authentication and rate limiting dependencies
def auth_and_rate_limit_trending():
    """Authentication + rate limiting for trending endpoints."""
    return [Depends(get_authenticated_user), rate_limit_trending()]


def auth_and_rate_limit_user():
    """Authentication + rate limiting for user endpoints."""
    return [Depends(get_authenticated_user), rate_limit_user()]


def auth_and_rate_limit_video():
    """Authentication + rate limiting for video endpoints."""
    return [Depends(get_authenticated_user), rate_limit_video()]


def auth_and_rate_limit_hashtag():
    """Authentication + rate limiting for hashtag endpoints."""
    return [Depends(get_authenticated_user), rate_limit_hashtag()]


def auth_and_rate_limit_search():
    """Authentication + rate limiting for search endpoints."""
    return [Depends(get_authenticated_user), rate_limit_search()]


def auth_and_rate_limit_sound():
    """Authentication + rate limiting for sound endpoints."""
    return [Depends(get_authenticated_user), rate_limit_sound()]


def auth_and_rate_limit_health():
    """Authentication + rate limiting for health endpoints."""
    return [Depends(get_authenticated_user), rate_limit_health()]

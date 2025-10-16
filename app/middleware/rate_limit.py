"""Custom rate limiting middleware."""

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Custom rate limiting middleware."""

    def __init__(self, app, limiter: Limiter):
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        try:
            # Get client identifier (IP address or API key)
            client_id = self._get_client_identifier(request)

            # Apply rate limiting logic here if needed
            # The actual rate limiting is handled by slowapi decorators
            # This middleware can be used for additional logging or custom logic

            response = await call_next(request)
            return response

        except Exception as e:
            logger.error(f"Rate limit middleware error: {e}")
            # Continue with the request even if middleware fails
            return await call_next(request)

    def _get_client_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Try to get API key from headers first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key}"

        # Fall back to IP address
        return f"ip:{get_remote_address(request)}"


def create_rate_limit_middleware(limiter: Limiter) -> RateLimitMiddleware:
    """Create rate limiting middleware instance."""
    return RateLimitMiddleware

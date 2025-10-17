"""Proxy monitoring endpoints."""

import logging
from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.dependencies import get_authenticated_user
from app.services.tiktok_service import get_tiktok_service
from app.models.schemas import ErrorResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class ProxyStatusResponse(BaseModel):
    """Proxy status response model."""
    enabled: bool
    provider: str
    algorithm: str
    proxy_count: int


@router.get(
    "/status",
    response_model=ProxyStatusResponse,
    summary="Get Proxy Status",
    description="Get current proxy configuration status",
    responses={
        200: {"description": "Proxy status retrieved successfully"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
    },
    tags=["proxy"]
)
@limiter.limit("60/minute")
async def get_proxy_status(
    request: Request,
    api_key: str = Depends(get_authenticated_user)
) -> ProxyStatusResponse:
    """Get proxy configuration status."""
    tiktok_service = get_tiktok_service()

    proxy_count = 0
    if tiktok_service.proxy_provider:
        # Ensure proxies are fetched to get accurate count
        try:
            await tiktok_service.proxy_provider.ensure_initialized()
            proxy_count = len(tiktok_service.proxy_provider.list_proxies())
        except Exception:
            # If async call fails, just get current count
            proxy_count = len(tiktok_service.proxy_provider.list_proxies())

    return ProxyStatusResponse(
        enabled=tiktok_service.proxy_provider is not None,
        provider="webshare" if tiktok_service.proxy_provider else "none",
        algorithm=tiktok_service.settings.proxy_algorithm if tiktok_service.proxy_provider else "none",
        proxy_count=proxy_count
    )

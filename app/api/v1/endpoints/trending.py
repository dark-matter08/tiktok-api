"""Trending videos endpoints."""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.dependencies import get_authenticated_user, rate_limit_trending
from app.models.schemas import (
    ErrorResponse,
    TrendingVideosResponse,
    TikTokVideo,
    create_tiktok_video
)
from app.services.tiktok_service import get_tiktok_service, TikTokService

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get(
    "/videos",
    response_model=TrendingVideosResponse,
    summary="Get Trending Videos",
    description="Retrieve trending videos from TikTok",
    responses={
        200: {"description": "Successfully retrieved trending videos"},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    tags=["trending"]
)
@limiter.limit("200/minute")
async def get_trending_videos(
    request: Request,
    count: int = Query(
        default=30,
        ge=1,
        le=100,
        description="Number of trending videos to retrieve (1-100)"
    ),
    api_key: str = Depends(get_authenticated_user),
    tiktok_service: TikTokService = Depends(get_tiktok_service)
) -> TrendingVideosResponse:
    """
    Get trending videos from TikTok.

    This endpoint retrieves the most popular videos currently trending on TikTok.
    The videos are returned in order of popularity.

    Args:
        count: Number of videos to retrieve (1-100, default: 30)
        api_key: API key for authentication
        tiktok_service: TikTok service instance

    Returns:
        TrendingVideosResponse: List of trending videos with metadata

    Raises:
        HTTPException: If the request fails or rate limit is exceeded
    """
    try:
        logger.info(
            f"Fetching {count} trending videos for API key: {api_key[:10]}...")

        # Get trending videos from TikTok service
        videos_data = await tiktok_service.get_trending_videos(count=count)

        # Convert to Pydantic models
        videos = [create_tiktok_video(video_data)
                  for video_data in videos_data]

        logger.info(f"Successfully fetched {len(videos)} trending videos")

        return TrendingVideosResponse(
            videos=videos,
            count=len(videos)
        )

    except Exception as e:
        logger.error(f"Error fetching trending videos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch trending videos: {str(e)}"
        )

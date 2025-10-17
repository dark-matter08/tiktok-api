"""Hashtag-related endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.dependencies import get_authenticated_user, rate_limit_hashtag, get_ms_token
from app.models.schemas import (
    ErrorResponse,
    HashtagVideosResponse,
    HashtagInfoResponse,
    TikTokVideo,
    TikTokHashtag,
    create_tiktok_video,
    create_tiktok_hashtag
)
from app.services.tiktok_service import get_tiktok_service, TikTokService

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get(
    "/{hashtag}/videos",
    response_model=HashtagVideosResponse,
    summary="Get Hashtag Videos",
    description="Retrieve videos associated with a specific hashtag. Optionally provide X-MS-Token header to use a custom MS token instead of environment-configured tokens.",
    responses={
        200: {"description": "Successfully retrieved hashtag videos"},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        404: {"description": "Hashtag not found", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    tags=["hashtag"]
)
@limiter.limit("100/minute")
async def get_hashtag_videos(
    request: Request,
    hashtag: str = Path(..., description="Hashtag name (without #)"),
    count: int = Query(
        default=30,
        ge=1,
        le=100,
        description="Number of videos to retrieve (1-100)"
    ),
    api_key: str = Depends(get_authenticated_user),
    ms_token: Optional[str] = Depends(get_ms_token),
    tiktok_service: TikTokService = Depends(get_tiktok_service)
) -> HashtagVideosResponse:
    """
    Get videos associated with a specific hashtag.

    Args:
        hashtag: Hashtag name (without # symbol)
        count: Number of videos to retrieve (1-100, default: 30)
        api_key: API key for authentication
        tiktok_service: TikTok service instance

    Returns:
        HashtagVideosResponse: List of videos with the hashtag and metadata

    Raises:
        HTTPException: If the request fails or hashtag is not found
    """
    try:
        # Remove # if present in hashtag
        clean_hashtag = hashtag.lstrip('#')

        logger.info(
            f"Fetching {count} videos for hashtag #{clean_hashtag} with API key: {api_key[:10]}...")

        # Get hashtag videos from TikTok service
        videos_data = await tiktok_service.get_hashtag_videos(clean_hashtag, count=count, custom_ms_token=ms_token)

        # Convert to Pydantic models
        videos = [create_tiktok_video(video_data)
                  for video_data in videos_data]

        logger.info(
            f"Successfully fetched {len(videos)} videos for hashtag #{clean_hashtag}")

        return HashtagVideosResponse(
            videos=videos,
            hashtag=clean_hashtag,
            count=len(videos)
        )

    except Exception as e:
        logger.error(f"Error fetching hashtag videos for #{hashtag}: {e}")
        if "not found" in str(e).lower() or "404" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hashtag '#{hashtag}' not found"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch hashtag videos: {str(e)}"
        )


@router.get(
    "/{hashtag}/info",
    response_model=HashtagInfoResponse,
    summary="Get Hashtag Information",
    description="Retrieve detailed information about a specific hashtag. Optionally provide X-MS-Token header to use a custom MS token instead of environment-configured tokens.",
    responses={
        200: {"description": "Successfully retrieved hashtag information"},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        404: {"description": "Hashtag not found", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    tags=["hashtag"]
)
@limiter.limit("100/minute")
async def get_hashtag_info(
    request: Request,
    hashtag: str = Path(..., description="Hashtag name (without #)"),
    api_key: str = Depends(get_authenticated_user),
    ms_token: Optional[str] = Depends(get_ms_token),
    tiktok_service: TikTokService = Depends(get_tiktok_service)
) -> HashtagInfoResponse:
    """
    Get detailed information about a specific hashtag.

    Args:
        hashtag: Hashtag name (without # symbol)
        api_key: API key for authentication
        tiktok_service: TikTok service instance

    Returns:
        HashtagInfoResponse: Hashtag information including stats and metadata

    Raises:
        HTTPException: If the request fails or hashtag is not found
    """
    try:
        # Remove # if present in hashtag
        clean_hashtag = hashtag.lstrip('#')

        logger.info(
            f"Fetching hashtag info for #{clean_hashtag} with API key: {api_key[:10]}...")

        # Get hashtag info from TikTok service
        hashtag_data = await tiktok_service.get_hashtag_info(clean_hashtag, custom_ms_token=ms_token)

        # Convert to Pydantic model
        hashtag_info = create_tiktok_hashtag(hashtag_data)

        logger.info(f"Successfully fetched hashtag info for #{clean_hashtag}")

        return HashtagInfoResponse(hashtag=hashtag_info)

    except Exception as e:
        logger.error(f"Error fetching hashtag info for #{hashtag}: {e}")
        if "not found" in str(e).lower() or "404" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hashtag '#{hashtag}' not found"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch hashtag info: {str(e)}"
        )

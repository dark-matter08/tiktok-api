"""Sound-related endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.dependencies import get_authenticated_user, rate_limit_sound
from app.models.schemas import (
    ErrorResponse,
    SoundVideosResponse,
    SoundInfoResponse,
    TikTokVideo,
    TikTokSound,
    create_tiktok_video,
    create_tiktok_sound
)
from app.services.tiktok_service import get_tiktok_service, TikTokService

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get(
    "/{sound_id}/videos",
    response_model=SoundVideosResponse,
    summary="Get Sound Videos",
    description="Retrieve videos using a specific sound",
    responses={
        200: {"description": "Successfully retrieved sound videos"},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        404: {"description": "Sound not found", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    tags=["sound"]
)
@limiter.limit("100/minute")
async def get_sound_videos(
    request: Request,
    sound_id: str = Path(..., description="TikTok sound ID"),
    count: int = Query(
        default=30,
        ge=1,
        le=100,
        description="Number of videos to retrieve (1-100)"
    ),
    api_key: str = Depends(get_authenticated_user),
    tiktok_service: TikTokService = Depends(get_tiktok_service)
) -> SoundVideosResponse:
    """
    Get videos using a specific sound.

    Args:
        sound_id: TikTok sound ID
        count: Number of videos to retrieve (1-100, default: 30)
        api_key: API key for authentication
        tiktok_service: TikTok service instance

    Returns:
        SoundVideosResponse: List of videos using the sound with metadata

    Raises:
        HTTPException: If the request fails or sound is not found
    """
    try:
        logger.info(
            f"Fetching {count} videos for sound {sound_id} with API key: {api_key[:10]}...")

        # Get sound videos from TikTok service
        videos_data = await tiktok_service.get_sound_videos(sound_id, count=count)

        # Convert to Pydantic models
        videos = [create_tiktok_video(video_data)
                  for video_data in videos_data]

        logger.info(
            f"Successfully fetched {len(videos)} videos for sound {sound_id}")

        return SoundVideosResponse(
            videos=videos,
            sound_id=sound_id,
            count=len(videos)
        )

    except Exception as e:
        logger.error(f"Error fetching sound videos for {sound_id}: {e}")
        if "not found" in str(e).lower() or "404" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sound '{sound_id}' not found"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch sound videos: {str(e)}"
        )


@router.get(
    "/{sound_id}/info",
    response_model=SoundInfoResponse,
    summary="Get Sound Information",
    description="Retrieve detailed information about a specific sound",
    responses={
        200: {"description": "Successfully retrieved sound information"},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        404: {"description": "Sound not found", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    tags=["sound"]
)
@limiter.limit("100/minute")
async def get_sound_info(
    request: Request,
    sound_id: str = Path(..., description="TikTok sound ID"),
    api_key: str = Depends(get_authenticated_user),
    tiktok_service: TikTokService = Depends(get_tiktok_service)
) -> SoundInfoResponse:
    """
    Get detailed information about a specific sound.

    Args:
        sound_id: TikTok sound ID
        api_key: API key for authentication
        tiktok_service: TikTok service instance

    Returns:
        SoundInfoResponse: Sound information including metadata and stats

    Raises:
        HTTPException: If the request fails or sound is not found
    """
    try:
        logger.info(
            f"Fetching sound info for {sound_id} with API key: {api_key[:10]}...")

        # Get sound info from TikTok service
        sound_data = await tiktok_service.get_sound_info(sound_id)

        # Convert to Pydantic model
        sound = create_tiktok_sound(sound_data)

        logger.info(f"Successfully fetched sound info for {sound_id}")

        return SoundInfoResponse(sound=sound)

    except Exception as e:
        logger.error(f"Error fetching sound info for {sound_id}: {e}")
        if "not found" in str(e).lower() or "404" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sound '{sound_id}' not found"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch sound info: {str(e)}"
        )

"""Search-related endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.dependencies import get_authenticated_user, rate_limit_search
from app.models.schemas import (
    ErrorResponse,
    SearchUsersResponse,
    SearchVideosResponse,
    TikTokUser,
    TikTokVideo,
    create_tiktok_user,
    create_tiktok_video
)
from app.services.tiktok_service import get_tiktok_service, TikTokService

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get(
    "/users",
    response_model=SearchUsersResponse,
    summary="Search Users",
    description="Search for TikTok users by query",
    responses={
        200: {"description": "Successfully retrieved user search results"},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    tags=["search"]
)
@limiter.limit("50/minute")
async def search_users(
    request: Request,
    q: str = Query(..., min_length=1, max_length=100,
                   description="Search query"),
    count: int = Query(
        default=30,
        ge=1,
        le=100,
        description="Number of users to retrieve (1-100)"
    ),
    api_key: str = Depends(get_authenticated_user),
    tiktok_service: TikTokService = Depends(get_tiktok_service)
) -> SearchUsersResponse:
    """
    Search for TikTok users by query.

    Args:
        q: Search query string
        count: Number of users to retrieve (1-100, default: 30)
        api_key: API key for authentication
        tiktok_service: TikTok service instance

    Returns:
        SearchUsersResponse: List of matching users with metadata

    Raises:
        HTTPException: If the request fails
    """
    try:
        logger.info(
            f"Searching users with query '{q}' (count: {count}) with API key: {api_key[:10]}...")

        # Search users from TikTok service
        users_data = await tiktok_service.search_users(q, count=count)

        # Convert to Pydantic models
        users = [create_tiktok_user(user_data) for user_data in users_data]

        logger.info(f"Successfully found {len(users)} users for query '{q}'")

        return SearchUsersResponse(
            users=users,
            query=q,
            count=len(users)
        )

    except Exception as e:
        logger.error(f"Error searching users with query '{q}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search users: {str(e)}"
        )


@router.get(
    "/videos",
    response_model=SearchVideosResponse,
    summary="Search Videos",
    description="Search for TikTok videos by query",
    responses={
        200: {"description": "Successfully retrieved video search results"},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    tags=["search"]
)
@limiter.limit("50/minute")
async def search_videos(
    request: Request,
    q: str = Query(..., min_length=1, max_length=100,
                   description="Search query"),
    count: int = Query(
        default=30,
        ge=1,
        le=100,
        description="Number of videos to retrieve (1-100)"
    ),
    api_key: str = Depends(get_authenticated_user),
    tiktok_service: TikTokService = Depends(get_tiktok_service)
) -> SearchVideosResponse:
    """
    Search for TikTok videos by query.

    Args:
        q: Search query string
        count: Number of videos to retrieve (1-100, default: 30)
        api_key: API key for authentication
        tiktok_service: TikTok service instance

    Returns:
        SearchVideosResponse: List of matching videos with metadata

    Raises:
        HTTPException: If the request fails
    """
    try:
        logger.info(
            f"Searching videos with query '{q}' (count: {count}) with API key: {api_key[:10]}...")

        # Search videos from TikTok service
        videos_data = await tiktok_service.search_videos(q, count=count)

        # Convert to Pydantic models
        videos = [create_tiktok_video(video_data)
                  for video_data in videos_data]

        logger.info(f"Successfully found {len(videos)} videos for query '{q}'")

        return SearchVideosResponse(
            videos=videos,
            query=q,
            count=len(videos)
        )

    except Exception as e:
        logger.error(f"Error searching videos with query '{q}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search videos: {str(e)}"
        )

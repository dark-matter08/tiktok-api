"""User-related endpoints."""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.dependencies import get_authenticated_user, rate_limit_user
from app.models.schemas import (
    ErrorResponse,
    UserInfoResponse,
    UserVideosResponse,
    UserFollowersResponse,
    UserFollowingResponse,
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
    "/{username}/info",
    response_model=UserInfoResponse,
    summary="Get User Information",
    description="Retrieve detailed information about a TikTok user",
    responses={
        200: {"description": "Successfully retrieved user information"},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        404: {"description": "User not found", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    tags=["user"]
)
@limiter.limit("100/minute")
async def get_user_info(
    request: Request,
    username: str = Path(..., description="TikTok username"),
    api_key: str = Depends(get_authenticated_user),
    tiktok_service: TikTokService = Depends(get_tiktok_service)
) -> UserInfoResponse:
    """
    Get detailed information about a TikTok user.

    Args:
        username: TikTok username (without @)
        api_key: API key for authentication
        tiktok_service: TikTok service instance

    Returns:
        UserInfoResponse: User information including stats and profile details

    Raises:
        HTTPException: If the request fails or user is not found
    """
    try:
        logger.info(
            f"Fetching user info for {username} with API key: {api_key[:10]}...")

        # Get user info from TikTok service
        user_data = await tiktok_service.get_user_info(username)

        # Convert to Pydantic model
        user = create_tiktok_user(user_data)

        logger.info(f"Successfully fetched user info for {username}")

        return UserInfoResponse(user=user)

    except Exception as e:
        logger.error(f"Error fetching user info for {username}: {e}")
        if "not found" in str(e).lower() or "404" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user info: {str(e)}"
        )


@router.get(
    "/{username}/videos",
    response_model=UserVideosResponse,
    summary="Get User Videos",
    description="Retrieve videos posted by a specific TikTok user",
    responses={
        200: {"description": "Successfully retrieved user videos"},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        404: {"description": "User not found", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    tags=["user"]
)
@limiter.limit("100/minute")
async def get_user_videos(
    request: Request,
    username: str = Path(..., description="TikTok username"),
    count: int = Query(
        default=30,
        ge=1,
        le=100,
        description="Number of videos to retrieve (1-100)"
    ),
    api_key: str = Depends(get_authenticated_user),
    tiktok_service: TikTokService = Depends(get_tiktok_service)
) -> UserVideosResponse:
    """
    Get videos posted by a specific TikTok user.

    Args:
        username: TikTok username (without @)
        count: Number of videos to retrieve (1-100, default: 30)
        api_key: API key for authentication
        tiktok_service: TikTok service instance

    Returns:
        UserVideosResponse: List of user's videos with metadata

    Raises:
        HTTPException: If the request fails or user is not found
    """
    try:
        logger.info(
            f"Fetching {count} videos for user {username} with API key: {api_key[:10]}...")

        # Get user videos from TikTok service
        videos_data = await tiktok_service.get_user_videos(username, count=count)

        # Convert to Pydantic models
        videos = [create_tiktok_video(video_data)
                  for video_data in videos_data]

        logger.info(
            f"Successfully fetched {len(videos)} videos for user {username}")

        return UserVideosResponse(
            videos=videos,
            count=len(videos),
            username=username
        )

    except Exception as e:
        logger.error(f"Error fetching user videos for {username}: {e}")
        if "not found" in str(e).lower() or "404" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user videos: {str(e)}"
        )


@router.get(
    "/{username}/followers",
    response_model=UserFollowersResponse,
    summary="Get User Followers",
    description="Retrieve followers of a specific TikTok user",
    responses={
        200: {"description": "Successfully retrieved user followers"},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        404: {"description": "User not found", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    tags=["user"]
)
@limiter.limit("100/minute")
async def get_user_followers(
    request: Request,
    username: str = Path(..., description="TikTok username"),
    count: int = Query(
        default=30,
        ge=1,
        le=100,
        description="Number of followers to retrieve (1-100)"
    ),
    api_key: str = Depends(get_authenticated_user),
    tiktok_service: TikTokService = Depends(get_tiktok_service)
) -> UserFollowersResponse:
    """
    Get followers of a specific TikTok user.

    Args:
        username: TikTok username (without @)
        count: Number of followers to retrieve (1-100, default: 30)
        api_key: API key for authentication
        tiktok_service: TikTok service instance

    Returns:
        UserFollowersResponse: List of user's followers with metadata

    Raises:
        HTTPException: If the request fails or user is not found
    """
    try:
        logger.info(
            f"Fetching {count} followers for user {username} with API key: {api_key[:10]}...")

        # Get user followers from TikTok service
        followers_data = await tiktok_service.get_user_followers(username, count=count)

        # Convert to Pydantic models
        followers = [create_tiktok_user(follower_data)
                     for follower_data in followers_data]

        logger.info(
            f"Successfully fetched {len(followers)} followers for user {username}")

        return UserFollowersResponse(
            followers=followers,
            count=len(followers),
            username=username
        )

    except Exception as e:
        logger.error(f"Error fetching user followers for {username}: {e}")
        if "not found" in str(e).lower() or "404" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user followers: {str(e)}"
        )


@router.get(
    "/{username}/following",
    response_model=UserFollowingResponse,
    summary="Get User Following",
    description="Retrieve users that a specific TikTok user is following",
    responses={
        200: {"description": "Successfully retrieved user following"},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        404: {"description": "User not found", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    tags=["user"]
)
@limiter.limit("100/minute")
async def get_user_following(
    request: Request,
    username: str = Path(..., description="TikTok username"),
    count: int = Query(
        default=30,
        ge=1,
        le=100,
        description="Number of users to retrieve (1-100)"
    ),
    api_key: str = Depends(get_authenticated_user),
    tiktok_service: TikTokService = Depends(get_tiktok_service)
) -> UserFollowingResponse:
    """
    Get users that a specific TikTok user is following.

    Args:
        username: TikTok username (without @)
        count: Number of users to retrieve (1-100, default: 30)
        api_key: API key for authentication
        tiktok_service: TikTok service instance

    Returns:
        UserFollowingResponse: List of users being followed with metadata

    Raises:
        HTTPException: If the request fails or user is not found
    """
    try:
        logger.info(
            f"Fetching {count} following for user {username} with API key: {api_key[:10]}...")

        # Get user following from TikTok service
        following_data = await tiktok_service.get_user_following(username, count=count)

        # Convert to Pydantic models
        following = [create_tiktok_user(user_data)
                     for user_data in following_data]

        logger.info(
            f"Successfully fetched {len(following)} following for user {username}")

        return UserFollowingResponse(
            following=following,
            count=len(following),
            username=username
        )

    except Exception as e:
        logger.error(f"Error fetching user following for {username}: {e}")
        if "not found" in str(e).lower() or "404" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user following: {str(e)}"
        )

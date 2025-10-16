"""Video-related endpoints."""

import logging
from urllib.parse import unquote

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.dependencies import get_authenticated_user, rate_limit_video
from app.models.schemas import (
    ErrorResponse,
    VideoInfoResponse,
    VideoCommentsResponse,
    VideoUrlRequest,
    VideoIdResponse,
    TikTokVideo,
    TikTokComment,
    create_tiktok_video,
    create_tiktok_comment
)
from app.services.tiktok_service import get_tiktok_service, TikTokService
from app.utils.url_parser import extract_video_id_from_url, is_tiktok_url, normalize_video_identifier

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/parse-url",
    response_model=VideoIdResponse,
    summary="Parse Video URL",
    description="Extract video ID from TikTok URL (supports standard and shortened URLs)",
    responses={
        200: {"description": "Successfully extracted video ID"},
        400: {"description": "Invalid URL or unable to extract ID", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    tags=["video"]
)
@limiter.limit("100/minute")
async def parse_video_url(
    request: Request,
    url_request: VideoUrlRequest = Body(...),
    api_key: str = Depends(get_authenticated_user)
) -> VideoIdResponse:
    """
    Extract video ID from a TikTok URL.

    Supports various URL formats:
    - Standard: https://www.tiktok.com/@username/video/1234567890123456789
    - Short: https://vm.tiktok.com/ZMxxx/
    - Alternative short: https://www.tiktok.com/t/ZMxxx/

    Args:
        url_request: Request containing the URL and resolution options
        api_key: API key for authentication

    Returns:
        VideoIdResponse: Extracted video ID and URL information

    Raises:
        HTTPException: If the URL is invalid or ID cannot be extracted
    """
    try:
        logger.info(f"Parsing video URL: {url_request.url}")

        # Extract video ID from URL
        video_id = await extract_video_id_from_url(
            url_request.url,
            resolve_redirects=url_request.resolve_redirects
        )

        if not video_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to extract video ID from URL: {url_request.url}"
            )

        logger.info(f"Successfully extracted video ID: {video_id}")

        return VideoIdResponse(
            video_id=video_id,
            original_url=url_request.url,
            resolved_url=None  # Could be enhanced to return the resolved URL
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error parsing video URL {url_request.url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse video URL: {str(e)}"
        )


@router.get(
    "/by-url",
    response_model=VideoInfoResponse,
    summary="Get Video Information by URL",
    description="Retrieve detailed information about a TikTok video using its URL",
    responses={
        200: {"description": "Successfully retrieved video information"},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        404: {"description": "Video not found", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    tags=["video"]
)
@limiter.limit("150/minute")
async def get_video_info_by_url(
    request: Request,
    url: str = Query(..., description="TikTok video URL"),
    resolve_redirects: bool = Query(
        True, description="Whether to resolve shortened URLs"),
    api_key: str = Depends(get_authenticated_user),
    tiktok_service: TikTokService = Depends(get_tiktok_service)
) -> VideoInfoResponse:
    """
    Get detailed information about a TikTok video using its URL.

    This endpoint accepts TikTok URLs in various formats:
    - Standard: https://www.tiktok.com/@username/video/1234567890123456789
    - Short: https://vm.tiktok.com/ZMxxx/
    - Alternative short: https://www.tiktok.com/t/ZMxxx/

    Args:
        url: TikTok video URL
        resolve_redirects: Whether to resolve shortened URLs
        api_key: API key for authentication
        tiktok_service: TikTok service instance

    Returns:
        VideoInfoResponse: Video information including stats and metadata

    Raises:
        HTTPException: If the request fails or video is not found
    """
    try:
        logger.info(f"Getting video info by URL: {url}")

        # Extract video ID from URL
        video_id = await extract_video_id_from_url(url, resolve_redirects=resolve_redirects)
        if not video_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to extract video ID from URL: {url}"
            )

        logger.info(f"Extracted video ID: {video_id}")

        # Get video info from TikTok service (pass the original URL if available)
        video_data = await tiktok_service.get_video_info(video_id, video_url=url)

        # Convert to Pydantic model
        video = create_tiktok_video(video_data)

        logger.info(f"Successfully fetched video info for {video_id}")

        return VideoInfoResponse(video=video)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching video info for URL {url}: {e}")
        if "not found" in str(e).lower() or "404" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video not found for URL: {url}"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch video info: {str(e)}"
        )


@router.get(
    "/{video_id}",
    response_model=VideoInfoResponse,
    summary="Get Video Information",
    description="Retrieve detailed information about a TikTok video by ID",
    responses={
        200: {"description": "Successfully retrieved video information"},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        404: {"description": "Video not found", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    tags=["video"]
)
@limiter.limit("150/minute")
async def get_video_info(
    request: Request,
    video_id: str = Path(..., description="TikTok video ID"),
    api_key: str = Depends(get_authenticated_user),
    tiktok_service: TikTokService = Depends(get_tiktok_service)
) -> VideoInfoResponse:
    """
    Get detailed information about a TikTok video.

    This endpoint accepts either:
    - A video ID (e.g., "1234567890123456789")
    - A TikTok URL (e.g., "https://www.tiktok.com/@user/video/1234567890123456789")

    If a URL is provided, the video ID will be automatically extracted.

    Args:
        video_id: TikTok video ID or URL
        api_key: API key for authentication
        tiktok_service: TikTok service instance

    Returns:
        VideoInfoResponse: Video information including stats and metadata

    Raises:
        HTTPException: If the request fails or video is not found
    """
    try:
        # URL-decode the parameter in case it's a URL-encoded TikTok URL
        decoded_video_id = unquote(video_id)
        logger.info(f"Original video_id: {video_id}")
        logger.info(f"Decoded video_id: {decoded_video_id}")

        original_url = None
        # Check if the decoded video_id is actually a URL and extract the ID
        if is_tiktok_url(decoded_video_id):
            logger.info(
                f"Detected URL format, extracting video ID from: {decoded_video_id}")
            original_url = decoded_video_id  # Store the original URL
            extracted_id = await extract_video_id_from_url(decoded_video_id, resolve_redirects=True)
            logger.info(f"Extracted video ID: {extracted_id}")
            if not extracted_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unable to extract video ID from URL: {decoded_video_id}"
                )
            video_id = extracted_id
            logger.info(f"Using extracted video ID: {video_id}")

        logger.info(
            f"Fetching video info for {video_id} with API key: {api_key[:10]}...")

        # Get video info from TikTok service (pass URL if available)
        video_data = await tiktok_service.get_video_info(video_id, video_url=original_url)

        # Convert to Pydantic model
        video = create_tiktok_video(video_data)

        logger.info(f"Successfully fetched video info for {video_id}")

        return VideoInfoResponse(video=video)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching video info for {video_id}: {e}")
        if "not found" in str(e).lower() or "404" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video '{video_id}' not found"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch video info: {str(e)}"
        )


@router.get(
    "/{video_id}/comments",
    response_model=VideoCommentsResponse,
    summary="Get Video Comments",
    description="Retrieve comments for a specific TikTok video",
    responses={
        200: {"description": "Successfully retrieved video comments"},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        404: {"description": "Video not found", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    tags=["video"]
)
@limiter.limit("150/minute")
async def get_video_comments(
    request: Request,
    video_id: str = Path(..., description="TikTok video ID"),
    count: int = Query(
        default=30,
        ge=1,
        le=100,
        description="Number of comments to retrieve (1-100)"
    ),
    api_key: str = Depends(get_authenticated_user),
    tiktok_service: TikTokService = Depends(get_tiktok_service)
) -> VideoCommentsResponse:
    """
    Get comments for a specific TikTok video.

    Args:
        video_id: TikTok video ID
        count: Number of comments to retrieve (1-100, default: 30)
        api_key: API key for authentication
        tiktok_service: TikTok service instance

    Returns:
        VideoCommentsResponse: List of video comments with metadata

    Raises:
        HTTPException: If the request fails or video is not found
    """
    try:
        logger.info(
            f"Fetching {count} comments for video {video_id} with API key: {api_key[:10]}...")

        # Get video comments from TikTok service
        comments_data = await tiktok_service.get_video_comments(video_id, count=count)

        # Convert to Pydantic models
        comments = [create_tiktok_comment(comment_data)
                    for comment_data in comments_data]

        logger.info(
            f"Successfully fetched {len(comments)} comments for video {video_id}")

        return VideoCommentsResponse(
            comments=comments,
            count=len(comments),
            video_id=video_id
        )

    except Exception as e:
        logger.error(f"Error fetching video comments for {video_id}: {e}")
        if "not found" in str(e).lower() or "404" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video '{video_id}' not found"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch video comments: {str(e)}"
        )

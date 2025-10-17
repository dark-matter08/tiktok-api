"""Video-related endpoints."""

import logging
from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request, status
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.dependencies import get_authenticated_user, rate_limit_video, get_ms_token
from app.models.schemas import (
    ErrorResponse,
    VideoInfoResponse,
    VideoCommentsResponse,
    VideoUrlRequest,
    VideoIdResponse,
    VideoDownloadRequest,
    VideoDownloadResponse,
    VideoDownloadUrls,
    VideoQuality,
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
    api_key: str = Depends(get_authenticated_user),
    ms_token: Optional[str] = Depends(get_ms_token)
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
        # Clean and validate URL
        url_request.url = url_request.url.strip()
        if not url_request.url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL parameter cannot be empty"
            )

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
    description="Retrieve detailed information about a TikTok video using its URL. Optionally provide X-MS-Token header to use a custom MS token instead of environment-configured tokens.",
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
    include_download_urls: bool = Query(
        False, description="Whether to include download URLs in response"),
    api_key: str = Depends(get_authenticated_user),
    ms_token: Optional[str] = Depends(get_ms_token),
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
        # Clean and validate URL
        url = url.strip()
        if not url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL parameter cannot be empty"
            )

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
        video_data = await tiktok_service.get_video_info(video_id, video_url=url, custom_ms_token=ms_token)

        # Convert to Pydantic model
        video = create_tiktok_video(
            video_data, include_download_urls=include_download_urls)

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
    description="Retrieve detailed information about a TikTok video by ID. Optionally provide X-MS-Token header to use a custom MS token instead of environment-configured tokens.",
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
    include_download_urls: bool = Query(
        False, description="Whether to include download URLs in response"),
    api_key: str = Depends(get_authenticated_user),
    ms_token: Optional[str] = Depends(get_ms_token),
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
        video_data = await tiktok_service.get_video_info(video_id, video_url=original_url, custom_ms_token=ms_token)

        # Convert to Pydantic model
        video = create_tiktok_video(
            video_data, include_download_urls=include_download_urls)

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
    description="Retrieve comments for a specific TikTok video. Optionally provide X-MS-Token header to use a custom MS token instead of environment-configured tokens.",
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
    ms_token: Optional[str] = Depends(get_ms_token),
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
        logger.debug(f"Custom MS token: {ms_token}")

        # Get video comments from TikTok service
        comments_data = await tiktok_service.get_video_comments(video_id, count=count, custom_ms_token=ms_token)

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


@router.get(
    "/download-info",
    response_model=VideoDownloadResponse,
    summary="Get Video Download Information",
    description="Get download URLs and metadata for a TikTok video by URL. Optionally provide X-MS-Token header to use a custom MS token instead of environment-configured tokens.",
    responses={
        200: {"description": "Successfully retrieved video download information"},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        404: {"description": "Video not found", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    tags=["video"]
)
@limiter.limit("50/minute")
async def get_video_download_info(
    request: Request,
    url: str = Query(..., description="TikTok video URL"),
    watermark: bool = Query(
        False, description="Whether to include watermark in download URLs"),
    quality: VideoQuality = Query(
        VideoQuality.AUTO, description="Video quality preference"),
    resolve_redirects: bool = Query(
        True, description="Whether to resolve shortened URLs"),
    api_key: str = Depends(get_authenticated_user),
    ms_token: Optional[str] = Depends(get_ms_token),
    tiktok_service: TikTokService = Depends(get_tiktok_service)
) -> VideoDownloadResponse:
    """
    Get download information for a TikTok video including URLs for different qualities and watermark options.

    This endpoint accepts TikTok URLs in various formats:
    - Standard: https://www.tiktok.com/@username/video/1234567890123456789
    - Short: https://vm.tiktok.com/ZMxxx/
    - Alternative short: https://www.tiktok.com/t/ZMxxx/

    Args:
        url: TikTok video URL
        watermark: Whether to include watermark in download URLs
        quality: Video quality preference (auto, hd, sd)
        resolve_redirects: Whether to resolve shortened URLs
        api_key: API key for authentication
        tiktok_service: TikTok service instance

    Returns:
        VideoDownloadResponse: Download URLs and metadata

    Raises:
        HTTPException: If the request fails or video is not found
    """
    try:
        # Clean and validate URL
        url = url.strip()
        if not url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL parameter cannot be empty"
            )

        logger.info(
            f"Download info request started - URL: {url}, Watermark: {watermark}, Quality: {quality}, Resolve redirects: {resolve_redirects}")

        # Extract video ID from URL
        logger.debug(f"Extracting video ID from URL: {url}")
        video_id = await extract_video_id_from_url(url, resolve_redirects=resolve_redirects)
        if not video_id:
            logger.error(f"Failed to extract video ID from URL: {url}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to extract video ID from URL: {url}"
            )

        logger.info(
            f"Successfully extracted video ID: {video_id} from URL: {url}")

        # Get download info from TikTok service
        logger.debug(
            f"Calling TikTok service for download info - Video ID: {video_id}")
        download_data = await tiktok_service.get_video_download_info(
            video_id,
            video_url=url,
            watermark=watermark,
            quality=quality.value,
            custom_ms_token=ms_token
        )
        logger.info(
            f"Received download data from TikTok service for {video_id}")

        # Convert to Pydantic models
        logger.debug(
            f"Converting download URLs to Pydantic model for {video_id}")
        download_urls = VideoDownloadUrls(**download_data["download_urls"])
        logger.debug(f"Successfully converted download URLs for {video_id}")

        # Create response
        response = VideoDownloadResponse(
            video_id=video_id,
            original_url=url,
            download_urls=download_urls,
            quality=quality,
            watermark=watermark,
            file_size=download_data.get("file_size"),
            duration=download_data.get("duration")
        )

        logger.info(
            f"Successfully prepared download info response for {video_id} - File size: {download_data.get('file_size')} bytes, Duration: {download_data.get('duration')} seconds")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching download info for URL {url}: {e}")
        error_message = str(e).lower()

        if "not found" in error_message or "404" in error_message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video not found for URL: {url}"
            )
        elif "invalid response structure" in error_message or "200" in error_message:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="TikTok API returned an unexpected response format. The video may be private, geo-restricted, or temporarily unavailable."
            )
        elif "rate limit" in error_message or "too many requests" in error_message:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )
        elif "token" in error_message or "session" in error_message:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="TikTok service temporarily unavailable. Please try again later."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch download info: {str(e)}"
            )


@router.get(
    "/download-stream",
    summary="Stream Video Download",
    description="Stream TikTok video bytes directly for download. Optionally provide X-MS-Token header to use a custom MS token instead of environment-configured tokens.",
    responses={
        200: {"description": "Video stream", "content": {"video/mp4": {}}},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        404: {"description": "Video not found", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    tags=["video"]
)
@limiter.limit("20/minute")
async def stream_video_download(
    request: Request,
    url: str = Query(..., description="TikTok video URL"),
    watermark: bool = Query(
        False, description="Whether to include watermark"),
    quality: VideoQuality = Query(
        VideoQuality.AUTO, description="Video quality preference"),
    resolve_redirects: bool = Query(
        True, description="Whether to resolve shortened URLs"),
    api_key: str = Depends(get_authenticated_user),
    ms_token: Optional[str] = Depends(get_ms_token),
    tiktok_service: TikTokService = Depends(get_tiktok_service)
) -> StreamingResponse:
    """
    Stream TikTok video bytes directly for download.

    This endpoint accepts TikTok URLs in various formats and streams the video
    content directly to the client with appropriate headers for file download.

    Args:
        url: TikTok video URL
        watermark: Whether to include watermark
        quality: Video quality preference (auto, hd, sd)
        resolve_redirects: Whether to resolve shortened URLs
        api_key: API key for authentication
        tiktok_service: TikTok service instance

    Returns:
        StreamingResponse: Video stream with appropriate headers

    Raises:
        HTTPException: If the request fails or video is not found
    """
    try:
        # Clean and validate URL
        url = url.strip()
        if not url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL parameter cannot be empty"
            )

        logger.info(
            f"Stream download request started - URL: {url}, Watermark: {watermark}, Quality: {quality}, Resolve redirects: {resolve_redirects}")

        # Extract video ID from URL
        logger.debug(f"Extracting video ID from URL: {url}")
        video_id = await extract_video_id_from_url(url, resolve_redirects=resolve_redirects)
        if not video_id:
            logger.error(f"Failed to extract video ID from URL: {url}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to extract video ID from URL: {url}"
            )

        logger.info(
            f"Successfully extracted video ID: {video_id} from URL: {url}")

        # Get video bytes from TikTok service
        logger.debug(
            f"Calling TikTok service for video bytes - Video ID: {video_id}")
        video_bytes = await tiktok_service.get_video_bytes(
            video_id,
            video_url=url,
            watermark=watermark,
            quality=quality.value,
            custom_ms_token=ms_token
        )
        logger.info(
            f"Successfully retrieved video bytes for {video_id}: {len(video_bytes)} bytes")

        # Create filename for download
        filename = f"tiktok_video_{video_id}.mp4"
        if watermark:
            filename = f"tiktok_video_{video_id}_watermarked.mp4"

        logger.debug(f"Created filename for download: {filename}")

        # Prepare streaming response headers
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(len(video_bytes)),
            "Cache-Control": "no-cache"
        }
        logger.debug(f"Prepared streaming response headers: {headers}")

        logger.info(
            f"Successfully prepared streaming response for {video_id} - {len(video_bytes)} bytes, filename: {filename}")

        # Return streaming response with appropriate headers
        return StreamingResponse(
            iter([video_bytes]),
            media_type="video/mp4",
            headers=headers
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming video for URL {url}: {e}")
        error_message = str(e).lower()

        if "not found" in error_message or "404" in error_message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video not found for URL: {url}"
            )
        elif "invalid response structure" in error_message or "200" in error_message:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="TikTok API returned an unexpected response format. The video may be private, geo-restricted, or temporarily unavailable."
            )
        elif "rate limit" in error_message or "too many requests" in error_message:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )
        elif "token" in error_message or "session" in error_message:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="TikTok service temporarily unavailable. Please try again later."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to stream video: {str(e)}"
            )

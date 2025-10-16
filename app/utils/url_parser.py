"""TikTok URL parsing utilities."""

import re
import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

# Regex patterns for TikTok URLs
STANDARD_URL_PATTERN = re.compile(
    r'(?:https?://)?(?:www\.)?tiktok\.com/@[\w.-]+/video/(\d+)'
)
SHORT_URL_PATTERNS = [
    re.compile(r'(?:https?://)?vm\.tiktok\.com/([\w-]+)'),
    re.compile(r'(?:https?://)?(?:www\.)?tiktok\.com/t/([\w-]+)'),
]


async def extract_video_id_from_url(url: str, resolve_redirects: bool = True) -> Optional[str]:
    """
    Extract video ID from TikTok URL.

    Args:
        url: TikTok video URL (various formats supported)
        resolve_redirects: Whether to resolve shortened URLs

    Returns:
        Video ID as string, or None if extraction fails

    Supported formats:
        - https://www.tiktok.com/@username/video/1234567890123456789
        - https://vm.tiktok.com/ZMxxx/ (requires resolution)
        - https://www.tiktok.com/t/ZMxxx/ (requires resolution)
    """
    # Try to extract from standard URL format
    match = STANDARD_URL_PATTERN.search(url)
    if match:
        return match.group(1)

    # Check if it's a short URL
    if resolve_redirects:
        for pattern in SHORT_URL_PATTERNS:
            if pattern.search(url):
                resolved_url = await resolve_short_url(url)
                if resolved_url:
                    # Try to extract from resolved URL
                    match = STANDARD_URL_PATTERN.search(resolved_url)
                    if match:
                        return match.group(1)

    # If URL is already just a video ID
    if url.isdigit():
        return url

    return None


async def resolve_short_url(short_url: str, max_redirects: int = 5) -> Optional[str]:
    """
    Resolve a shortened TikTok URL to its full form.

    Args:
        short_url: Shortened TikTok URL
        max_redirects: Maximum number of redirects to follow

    Returns:
        Resolved full URL, or None if resolution fails
    """
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            # Make a HEAD request to follow redirects without downloading content
            response = await client.head(short_url, follow_redirects=True)
            final_url = str(response.url)

            logger.info(f"Resolved {short_url} to {final_url}")
            return final_url

    except httpx.HTTPError as e:
        logger.error(f"Error resolving short URL {short_url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error resolving short URL {short_url}: {e}")
        return None


def extract_video_id_sync(url: str) -> Optional[str]:
    """
    Synchronously extract video ID from standard TikTok URL (no redirect resolution).

    Args:
        url: TikTok video URL

    Returns:
        Video ID as string, or None if extraction fails
    """
    # Try standard URL format
    match = STANDARD_URL_PATTERN.search(url)
    if match:
        return match.group(1)

    # If URL is already just a video ID
    if url.isdigit():
        return url

    return None


def is_tiktok_url(url: str) -> bool:
    """
    Check if a string is a TikTok URL.

    Args:
        url: String to check

    Returns:
        True if it's a TikTok URL, False otherwise
    """
    # Check for standard URL
    if STANDARD_URL_PATTERN.search(url):
        return True

    # Check for short URLs
    for pattern in SHORT_URL_PATTERNS:
        if pattern.search(url):
            return True

    return False


def normalize_video_identifier(identifier: str) -> str:
    """
    Normalize a video identifier (could be ID or URL).

    Args:
        identifier: Video ID or URL

    Returns:
        Just the video ID (without URL resolution)
    """
    # If it's already a video ID
    if identifier.isdigit():
        return identifier

    # Try to extract from URL
    video_id = extract_video_id_sync(identifier)
    if video_id:
        return video_id

    # Return as-is if we can't extract
    return identifier

"""TikTok API service layer wrapping TikTok-Api methods."""

import os
from app.config import get_settings
from app.services.token_manager import get_token_manager
import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, AsyncGenerator
from contextlib import asynccontextmanager
import httpx

from TikTokApi import TikTokApi
from TikTokApi.exceptions import EmptyResponseException, TikTokException as TikTokApiException

# Custom proxy providers imports
try:
    from app.services.proxy import Webshare, RoundRobin, Random, First
    # from proxyproviders import Webshare, BrightData
    # from proxyproviders.algorithms import RoundRobin, Random, First, Algorithm
    PROXY_PROVIDERS_AVAILABLE = True
except ImportError:
    PROXY_PROVIDERS_AVAILABLE = False

# Create our own TikTokException to avoid constructor issues


class TikTokException(Exception):
    """Custom TikTok API exception."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


logger = logging.getLogger(__name__)


class TikTokService:
    """Service layer for TikTok API operations."""

    def __init__(self):
        self.settings = get_settings()
        self.token_manager = get_token_manager()
        self._api_instance: Optional[TikTokApi] = None
        self._lock = asyncio.Lock()

        # Initialize proxy provider if enabled
        self.proxy_provider = None
        if (self.settings.enable_proxy and
            self.settings.webshare_api_key and
                PROXY_PROVIDERS_AVAILABLE):
            try:
                algorithm = self._get_proxy_algorithm()
                self.proxy_provider = Webshare(
                    api_key=self.settings.webshare_api_key,
                    algorithm=algorithm,
                    cookie=self.settings.webshare_cookie
                )
                logger.info("Initialized Webshare proxy provider")
            except Exception as e:
                logger.error(f"Failed to initialize proxy provider: {e}")
                self.proxy_provider = None
        elif self.settings.enable_proxy and not PROXY_PROVIDERS_AVAILABLE:
            logger.warning(
                "Proxy enabled but proxyproviders package not available")
        elif self.settings.enable_proxy and not self.settings.webshare_api_key:
            logger.warning("Proxy enabled but no Webshare API key provided")

    def _get_proxy_algorithm(self):
        """Get proxy algorithm based on configuration."""
        if not PROXY_PROVIDERS_AVAILABLE:
            return None

        algorithm_map = {
            "round-robin": RoundRobin(),
            "random": Random(),
            "first": First(),
        }
        return algorithm_map.get(self.settings.proxy_algorithm, RoundRobin())

    @asynccontextmanager
    async def get_api_instance(self):
        """Get TikTok API instance with token rotation."""
        token = None
        api = None
        try:
            # Get a healthy token
            token = await self.token_manager.get_token()
            if not token:
                raise TikTokException("No healthy MS tokens available")

            # Create API instance
            api = TikTokApi()

            # Ensure proxies are fetched before creating sessions
            if self.proxy_provider:
                await self.proxy_provider.ensure_initialized()
                if self.proxy_provider.list_proxies():
                    logger.info(
                        f"Using {len(self.proxy_provider.list_proxies())} proxies")

            # Create sessions with proxy provider
            await api.create_sessions(
                ms_tokens=[token],
                num_sessions=self.settings.tiktok_num_sessions,
                sleep_after=self.settings.tiktok_sleep_after,
                browser=self.settings.tiktok_browser,
                proxy_provider=self.proxy_provider if self.proxy_provider else None,
                headless=False
            )

            yield api

            # Mark token as successful
            await self.token_manager.mark_token_success(token)

        except Exception as e:
            # Mark token as failed
            if token:
                await self.token_manager.mark_token_failure(token, str(e))
            logger.error(f"Error in API instance: {e}")
            raise
        finally:
            if api:
                try:
                    await api.close_sessions()
                    await api.stop_playwright()
                except Exception as e:
                    logger.warning(f"Error closing TikTok API instance: {e}")

    async def get_trending_videos(self, count: int = 30) -> List[Dict[str, Any]]:
        """Get trending videos from TikTok."""
        try:
            async with self.get_api_instance() as api:
                videos = []
                async for video in api.trending.videos(count=count):
                    videos.append(video.as_dict)
                return videos
        except Exception as e:
            logger.error(f"Error fetching trending videos: {e}")
            raise TikTokException(f"Failed to fetch trending videos: {e}")

    async def get_user_info(self, username: str) -> Dict[str, Any]:
        """Get user information by username."""
        try:
            async with self.get_api_instance() as api:
                user = api.user(username)
                user_info = await user.info()
                return user_info.as_dict
        except Exception as e:
            logger.error(f"Error fetching user info for {username}: {e}")
            raise TikTokException(
                f"Failed to fetch user info for {username}: {e}")

    async def get_user_videos(self, username: str, count: int = 30) -> List[Dict[str, Any]]:
        """Get user's videos by username."""
        try:
            async with self.get_api_instance() as api:
                videos: List[Dict[str, Any]] = []
                async for video in api.user(username).videos(count=count):
                    if isinstance(video, dict):
                        videos.append(video)
                    elif hasattr(video, "as_dict"):
                        videos.append(video.as_dict)
                    else:
                        logger.warning(
                            "Unexpected video item type: %s", type(video))
                return videos
        except Exception as e:
            logger.error(f"Error fetching user videos for {username}: {e}")
            raise TikTokException(
                f"Failed to fetch user videos for {username}: {e}")

    async def get_video_info(self, video_id: str, video_url: str = None) -> Dict[str, Any]:
        """Get video information by video ID."""
        try:
            async with self.get_api_instance() as api:
                # Create video object with ID
                video = api.video(id=video_id)

                # If URL is provided, set it on the video object
                if video_url:
                    video.url = video_url
                    video_info = await video.info()
                else:
                    # If no URL provided, try to construct a generic URL or use a different approach
                    # Some TikTok-Api versions might work without URL, others might need it
                    try:
                        # First try without URL
                        video_info = await video.info()
                    except Exception as url_error:
                        if "url" in str(url_error).lower():
                            # If URL is required, construct a generic URL
                            generic_url = f"https://www.tiktok.com/@user/video/{video_id}"
                            video.url = generic_url
                            logger.info(
                                f"Using generic URL for video {video_id}: {generic_url}")
                            video_info = await video.info()
                        else:
                            raise url_error

                if isinstance(video_info, dict):
                    return video_info
                if hasattr(video_info, "as_dict"):
                    return video_info.as_dict
                logger.warning("Unexpected video_info type: %s",
                               type(video_info))
                # Best effort fallback
                return dict(video_info)  # may still fail if non-mapping
        except Exception as e:
            logger.error(f"Error fetching video info for {video_id}: {e}")
            raise TikTokException(
                f"Failed to fetch video info for {video_id}: {e}")

    async def get_hashtag_videos(self, hashtag: str, count: int = 30) -> List[Dict[str, Any]]:
        """Get videos for a specific hashtag."""
        try:
            async with self.get_api_instance() as api:
                videos = []
                async for video in api.hashtag(name=hashtag).videos(count=count):
                    videos.append(video.as_dict)
                return videos
        except Exception as e:
            logger.error(f"Error fetching hashtag videos for #{hashtag}: {e}")
            raise TikTokException(
                f"Failed to fetch hashtag videos for #{hashtag}: {e}")

    async def search_users(self, query: str, count: int = 30) -> List[Dict[str, Any]]:
        """Search for users by query."""
        try:
            async with self.get_api_instance() as api:
                users = []
                async for user in api.search.users(query, count=count):
                    users.append(user.as_dict)
                return users
        except Exception as e:
            logger.error(f"Error searching users for query '{query}': {e}")
            raise TikTokException(
                f"Failed to search users for query '{query}': {e}")

    async def search_videos(self, query: str, count: int = 30) -> List[Dict[str, Any]]:
        """Search for videos by query."""
        try:
            async with self.get_api_instance() as api:
                videos = []
                async for video in api.search.videos(query, count=count):
                    videos.append(video.as_dict)
                return videos
        except Exception as e:
            logger.error(f"Error searching videos for query '{query}': {e}")
            raise TikTokException(
                f"Failed to search videos for query '{query}': {e}")

    async def get_sound_videos(self, sound_id: str, count: int = 30) -> List[Dict[str, Any]]:
        """Get videos using a specific sound."""
        try:
            async with self.get_api_instance() as api:
                videos = []
                async for video in api.sound(id=sound_id).videos(count=count):
                    videos.append(video.as_dict)
                return videos
        except Exception as e:
            logger.error(
                f"Error fetching sound videos for sound {sound_id}: {e}")
            raise TikTokException(
                f"Failed to fetch sound videos for sound {sound_id}: {e}")

    async def get_sound_info(self, sound_id: str) -> Dict[str, Any]:
        """Get sound information by sound ID."""
        try:
            async with self.get_api_instance() as api:
                sound = api.sound(id=sound_id)
                sound_info = await sound.info()
                return sound_info.as_dict
        except Exception as e:
            logger.error(f"Error fetching sound info for {sound_id}: {e}")
            raise TikTokException(
                f"Failed to fetch sound info for {sound_id}: {e}")

    async def get_hashtag_info(self, hashtag: str) -> Dict[str, Any]:
        """Get hashtag information by hashtag name."""
        try:
            async with self.get_api_instance() as api:
                hashtag_obj = api.hashtag(name=hashtag)
                hashtag_info = await hashtag_obj.info()
                return hashtag_info.as_dict
        except Exception as e:
            logger.error(f"Error fetching hashtag info for #{hashtag}: {e}")
            raise TikTokException(
                f"Failed to fetch hashtag info for #{hashtag}: {e}")

    async def get_user_followers(self, username: str, count: int = 30) -> List[Dict[str, Any]]:
        """Get user's followers."""
        try:
            async with self.get_api_instance() as api:
                followers = []
                async for follower in api.user(username).followers(count=count):
                    followers.append(follower.as_dict)
                return followers
        except Exception as e:
            logger.error(f"Error fetching followers for {username}: {e}")
            raise TikTokException(
                f"Failed to fetch followers for {username}: {e}")

    async def get_user_following(self, username: str, count: int = 30) -> List[Dict[str, Any]]:
        """Get users that the user is following."""
        try:
            async with self.get_api_instance() as api:
                following = []
                async for user in api.user(username).following(count=count):
                    following.append(user.as_dict)
                return following
        except Exception as e:
            logger.error(f"Error fetching following for {username}: {e}")
            raise TikTokException(
                f"Failed to fetch following for {username}: {e}")

    async def get_video_comments(self, video_id: str, count: int = 30) -> List[Dict[str, Any]]:
        """Get comments for a video."""
        try:
            async with self.get_api_instance() as api:
                comments = []
                async for comment in api.video(id=video_id).comments(count=count):
                    comments.append(comment.as_dict)
                return comments
        except Exception as e:
            logger.error(f"Error fetching comments for video {video_id}: {e}")
            raise TikTokException(
                f"Failed to fetch comments for video {video_id}: {e}")

    async def get_video_download_info(self, video_id: str, video_url: str = None, watermark: bool = False, quality: str = "auto") -> Dict[str, Any]:
        """Get video download information including URLs for different qualities and watermark options."""
        start_time = time.time()
        logger.info(
            f"Starting video download info request - Video ID: {video_id}, URL: {video_url}, Watermark: {watermark}, Quality: {quality}")

        try:
            # Reuse the existing get_video_info method to avoid duplicating logic
            logger.debug(f"Fetching video info for {video_id}")
            video_data = await self.get_video_info(video_id, video_url=video_url)
            logger.info(f"Successfully retrieved video data for {video_id}")

            # Extract download URLs from video data
            logger.debug(
                f"Extracting download URLs for {video_id} with watermark={watermark}, quality={quality}")
            download_urls = self._extract_download_urls(
                video_data, watermark, quality)
            logger.info(
                f"Extracted download URLs for {video_id}: {len([url for url in download_urls.values() if url])} URLs found")

            # Estimate file size and get duration
            file_size = self._estimate_file_size(video_data)
            duration = video_data.get("video", {}).get("duration", 0)
            logger.info(
                f"Video metadata for {video_id}: File size: {file_size} bytes, Duration: {duration} seconds")

            result = {
                "video_id": video_id,
                "original_url": video_url,
                "download_urls": download_urls,
                "quality": quality,
                "watermark": watermark,
                "file_size": file_size,
                "duration": duration,
                "video_data": video_data
            }

            elapsed_time = time.time() - start_time
            logger.info(
                f"Successfully prepared download info for {video_id} in {elapsed_time:.2f} seconds")
            return result

        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(
                f"Error fetching video download info for {video_id} after {elapsed_time:.2f} seconds: {e}", exc_info=True)
            raise TikTokException(
                f"Failed to fetch video download info for {video_id}: {e}")

    async def get_video_bytes(self, video_id: str, video_url: str = None, watermark: bool = False, quality: str = "auto") -> bytes:
        """Get video bytes for streaming download."""
        start_time = time.time()
        logger.info(
            f"Starting video bytes download - Video ID: {video_id}, URL: {video_url}, Watermark: {watermark}, Quality: {quality}")

        try:
            # First get the download info to get the appropriate URL
            logger.debug(f"Getting download info for {video_id}")
            download_info = await self.get_video_download_info(video_id, video_url, watermark, quality)
            logger.info(f"Retrieved download info for {video_id}")

            # Select the appropriate download URL based on preferences
            download_urls = download_info["download_urls"]
            logger.debug(
                f"Selecting download URL for {video_id} with watermark={watermark}, quality={quality}")
            selected_url = self._select_download_url(
                download_urls, watermark, quality)
            logger.info(
                f"Selected download URL for {video_id}: {selected_url[:100]}..." if selected_url else "No URL selected")

            if not selected_url:
                logger.error(
                    f"No suitable download URL found for {video_id} with preferences: watermark={watermark}, quality={quality}")
                raise TikTokException(
                    "No suitable download URL found for the specified preferences")

            # Download the video bytes
            logger.info(f"Starting video download for {video_id} from URL")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(selected_url)
                response.raise_for_status()
                video_bytes = response.content
                elapsed_time = time.time() - start_time
                logger.info(
                    f"Successfully downloaded video {video_id}: {len(video_bytes)} bytes in {elapsed_time:.2f} seconds")
                return video_bytes

        except httpx.HTTPError as e:
            elapsed_time = time.time() - start_time
            logger.error(
                f"HTTP error downloading video {video_id} after {elapsed_time:.2f} seconds: {e}", exc_info=True)
            raise TikTokException(f"Failed to download video: {e}")
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(
                f"Error downloading video bytes for {video_id} after {elapsed_time:.2f} seconds: {e}", exc_info=True)
            raise TikTokException(
                f"Failed to download video bytes for {video_id}: {e}")

    def _extract_download_urls(self, video_data: Dict[str, Any], watermark: bool, quality: str) -> Dict[str, Any]:
        """Extract download URLs from video data."""
        video_info = video_data.get("video", {})

        # Log the video data structure for debugging
        logger.debug(f"Video data structure: {list(video_data.keys())}")
        logger.debug(f"Video info structure: {list(video_info.keys())}")

        # Extract URLs from different possible fields in TikTok API response
        play_addr = video_info.get("playAddr", "")
        download_addr = video_info.get("downloadAddr", "")

        # Log the extracted URLs
        logger.debug(f"PlayAddr: {play_addr}")
        logger.debug(f"DownloadAddr: {download_addr}")

        # Try to get URLs from bitrate info (different qualities)
        bitrate_info = video_info.get("bitrateInfo", {})
        hd_url = None
        sd_url = None
        auto_url = None

        if bitrate_info:
            logger.debug(f"Bitrate info found: {len(bitrate_info)} variants")
            # Look for different quality variants
            for i, bitrate in enumerate(bitrate_info):
                if isinstance(bitrate, dict):
                    quality_name = bitrate.get("GearName", "").lower()
                    url = bitrate.get("PlayAddr", {}).get("UrlList", [None])[0]
                    logger.debug(f"Bitrate {i}: {quality_name} -> {url}")
                    if url:
                        if "hd" in quality_name or "high" in quality_name:
                            hd_url = url
                        elif "sd" in quality_name or "standard" in quality_name:
                            sd_url = url
                        else:
                            auto_url = url

        # Fallback to main URLs if no bitrate info
        if not any([hd_url, sd_url, auto_url]):
            auto_url = play_addr or download_addr
            logger.debug(f"Using fallback auto_url: {auto_url}")

        # Determine watermark URLs
        # Note: This is a simplified approach - actual TikTok API may have different URLs
        with_watermark = play_addr or auto_url
        without_watermark = download_addr or auto_url

        logger.debug(
            f"Final URLs - with_watermark: {with_watermark}, without_watermark: {without_watermark}")

        return {
            "with_watermark": with_watermark,
            "without_watermark": without_watermark,
            "hd_url": hd_url,
            "sd_url": sd_url,
            "auto_url": auto_url,
        }

    def _select_download_url(self, download_urls: Dict[str, Any], watermark: bool, quality: str) -> Optional[str]:
        """Select the appropriate download URL based on preferences."""
        logger.debug(
            f"Selecting download URL with watermark={watermark}, quality={quality}")
        logger.debug(f"Available URLs: {list(download_urls.keys())}")

        # First select based on watermark preference
        if watermark:
            base_url = download_urls.get("with_watermark")
            logger.debug(
                f"Selected base URL (with watermark): {base_url[:100] if base_url else 'None'}...")
        else:
            base_url = download_urls.get("without_watermark")
            logger.debug(
                f"Selected base URL (without watermark): {base_url[:100] if base_url else 'None'}...")

        # Then select quality if available
        if quality == "hd" and download_urls.get("hd_url"):
            selected_url = download_urls["hd_url"]
            logger.debug(f"Selected HD URL: {selected_url[:100]}...")
            return selected_url
        elif quality == "sd" and download_urls.get("sd_url"):
            selected_url = download_urls["sd_url"]
            logger.debug(f"Selected SD URL: {selected_url[:100]}...")
            return selected_url
        elif quality == "auto" and download_urls.get("auto_url"):
            selected_url = download_urls["auto_url"]
            logger.debug(f"Selected auto URL: {selected_url[:100]}...")
            return selected_url

        # Fallback to base URL
        logger.debug(
            f"Using fallback base URL: {base_url[:100] if base_url else 'None'}...")
        return base_url

    def _estimate_file_size(self, video_data: Dict[str, Any]) -> Optional[int]:
        """Estimate file size from video data."""
        video_info = video_data.get("video", {})
        # Try to get file size from video metadata
        file_size = video_info.get("fileSize")
        if file_size:
            return int(file_size)

        # Estimate based on duration and quality (rough approximation)
        duration = video_info.get("duration", 0)
        if duration > 0:
            # Rough estimate: 1MB per 10 seconds for SD, 2MB per 10 seconds for HD
            estimated_size = (duration / 10) * 1024 * \
                1024  # 1MB per 10 seconds
            return int(estimated_size)

        return None

    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the TikTok service."""
        try:
            # Try to get a small number of trending videos as a health check
            videos = await self.get_trending_videos(count=1)
            return {
                "status": "healthy",
                "message": "TikTok service is operational",
                "test_videos_fetched": len(videos)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"TikTok service health check failed: {e}",
                "test_videos_fetched": 0
            }


# Global TikTok service instance
tiktok_service = TikTokService()


def get_tiktok_service() -> TikTokService:
    """Get the global TikTok service instance."""
    return tiktok_service

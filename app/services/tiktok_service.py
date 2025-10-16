"""TikTok API service layer wrapping TikTok-Api methods."""

from app.config import get_settings
from app.services.token_manager import get_token_manager
import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from contextlib import asynccontextmanager

from TikTokApi import TikTokApi
from TikTokApi.exceptions import EmptyResponseException, TikTokException as TikTokApiException

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
            await api.create_sessions(
                ms_tokens=[token],
                num_sessions=self.settings.tiktok_num_sessions,
                sleep_after=self.settings.tiktok_sleep_after,
                browser=self.settings.tiktok_browser
            )

            yield api

            # Mark token as successful
            await self.token_manager.mark_token_success(token)

        except Exception as e:
            # Mark token as failed
            if token:
                await self.token_manager.mark_token_failure(token, str(e))
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

"""Pydantic models for API responses."""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class VideoQuality(str, Enum):
    """Video quality options."""
    AUTO = "auto"
    HD = "hd"
    SD = "sd"


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(
        None, description="Detailed error information")
    status_code: int = Field(..., description="HTTP status code")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    message: str = Field(..., description="Status message")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp")
    version: str = Field(..., description="API version")


class TikTokUser(BaseModel):
    """TikTok user model."""
    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    nickname: str = Field(..., description="Display name")
    signature: Optional[str] = Field(None, description="User bio/signature")
    avatar_thumb: Optional[Dict[str, Any]] = Field(
        None, description="Avatar thumbnail")
    avatar_medium: Optional[Dict[str, Any]] = Field(
        None, description="Avatar medium size")
    avatar_larger: Optional[Dict[str, Any]] = Field(
        None, description="Avatar larger size")
    verified: bool = Field(False, description="Whether user is verified")
    follower_count: int = Field(0, description="Number of followers")
    following_count: int = Field(0, description="Number of users following")
    heart_count: int = Field(0, description="Total likes received")
    video_count: int = Field(0, description="Number of videos posted")
    digg_count: int = Field(0, description="Number of likes given")


class TikTokVideo(BaseModel):
    """TikTok video model."""
    id: str = Field(..., description="Video ID")
    desc: str = Field(..., description="Video description")
    create_time: int = Field(..., description="Creation timestamp")
    video: Dict[str, Any] = Field(..., description="Video details")
    author: TikTokUser = Field(..., description="Video author")
    music: Optional[Dict[str, Any]] = Field(
        None, description="Music/sound details")
    stats: Dict[str, Any] = Field(..., description="Video statistics")
    hashtags: List[str] = Field(
        default_factory=list, description="Hashtags in video")
    mentions: List[str] = Field(
        default_factory=list, description="Mentioned users")
    challenges: List[Dict[str, Any]] = Field(
        default_factory=list, description="Challenges/hashtags")
    download_urls: Optional["VideoDownloadUrls"] = Field(
        None, description="Video download URLs (included when requested)")


class TikTokHashtag(BaseModel):
    """TikTok hashtag model."""
    id: str = Field(..., description="Hashtag ID")
    name: str = Field(..., description="Hashtag name")
    title: str = Field(..., description="Hashtag title")
    desc: Optional[str] = Field(None, description="Hashtag description")
    video_count: int = Field(
        0, description="Number of videos with this hashtag")
    view_count: int = Field(0, description="Total views for this hashtag")


class TikTokSound(BaseModel):
    """TikTok sound model."""
    id: str = Field(..., description="Sound ID")
    title: str = Field(..., description="Sound title")
    play_url: Optional[str] = Field(None, description="Sound play URL")
    cover_thumb: Optional[Dict[str, Any]] = Field(
        None, description="Sound cover thumbnail")
    cover_medium: Optional[Dict[str, Any]] = Field(
        None, description="Sound cover medium")
    cover_large: Optional[Dict[str, Any]] = Field(
        None, description="Sound cover large")
    author_name: Optional[str] = Field(None, description="Sound author name")
    original: bool = Field(
        False, description="Whether this is an original sound")
    duration: int = Field(0, description="Sound duration in seconds")
    album: Optional[str] = Field(None, description="Album name")


class TikTokComment(BaseModel):
    """TikTok comment model."""
    id: str = Field(..., description="Comment ID")
    text: str = Field(..., description="Comment text")
    create_time: int = Field(..., description="Creation timestamp")
    user: TikTokUser = Field(..., description="Comment author")
    like_count: int = Field(0, description="Number of likes")
    reply_comment_total: int = Field(0, description="Number of replies")


# Response models for API endpoints
class TrendingVideosResponse(BaseModel):
    """Response model for trending videos."""
    videos: List[TikTokVideo] = Field(...,
                                      description="List of trending videos")
    count: int = Field(..., description="Number of videos returned")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp")


class UserInfoResponse(BaseModel):
    """Response model for user information."""
    user: TikTokUser = Field(..., description="User information")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp")


class UserVideosResponse(BaseModel):
    """Response model for user videos."""
    videos: List[TikTokVideo] = Field(..., description="List of user videos")
    count: int = Field(..., description="Number of videos returned")
    username: str = Field(..., description="Username")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp")


class VideoInfoResponse(BaseModel):
    """Response model for video information."""
    video: TikTokVideo = Field(..., description="Video information")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp")


class VideoUrlRequest(BaseModel):
    """Request model for parsing video URL."""
    url: str = Field(..., description="TikTok video URL", min_length=1)
    resolve_redirects: bool = Field(
        default=True,
        description="Whether to resolve shortened URLs"
    )


class VideoIdResponse(BaseModel):
    """Response model for extracted video ID."""
    video_id: str = Field(..., description="Extracted video ID")
    original_url: str = Field(..., description="Original URL provided")
    resolved_url: Optional[str] = Field(
        None, description="Resolved URL (if different)")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp")


class HashtagVideosResponse(BaseModel):
    """Response model for hashtag videos."""
    videos: List[TikTokVideo] = Field(...,
                                      description="List of videos with hashtag")
    hashtag: str = Field(..., description="Hashtag name")
    count: int = Field(..., description="Number of videos returned")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp")


class HashtagInfoResponse(BaseModel):
    """Response model for hashtag information."""
    hashtag: TikTokHashtag = Field(..., description="Hashtag information")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp")


class SearchUsersResponse(BaseModel):
    """Response model for user search results."""
    users: List[TikTokUser] = Field(..., description="List of matching users")
    query: str = Field(..., description="Search query")
    count: int = Field(..., description="Number of users returned")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp")


class SearchVideosResponse(BaseModel):
    """Response model for video search results."""
    videos: List[TikTokVideo] = Field(...,
                                      description="List of matching videos")
    query: str = Field(..., description="Search query")
    count: int = Field(..., description="Number of videos returned")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp")


class SoundVideosResponse(BaseModel):
    """Response model for sound videos."""
    videos: List[TikTokVideo] = Field(...,
                                      description="List of videos using the sound")
    sound_id: str = Field(..., description="Sound ID")
    count: int = Field(..., description="Number of videos returned")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp")


class SoundInfoResponse(BaseModel):
    """Response model for sound information."""
    sound: TikTokSound = Field(..., description="Sound information")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp")


class UserFollowersResponse(BaseModel):
    """Response model for user followers."""
    followers: List[TikTokUser] = Field(..., description="List of followers")
    username: str = Field(..., description="Username")
    count: int = Field(..., description="Number of followers returned")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp")


class UserFollowingResponse(BaseModel):
    """Response model for user following."""
    following: List[TikTokUser] = Field(...,
                                        description="List of users being followed")
    username: str = Field(..., description="Username")
    count: int = Field(..., description="Number of users returned")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp")


class VideoCommentsResponse(BaseModel):
    """Response model for video comments."""
    comments: List[TikTokComment] = Field(..., description="List of comments")
    video_id: str = Field(..., description="Video ID")
    count: int = Field(..., description="Number of comments returned")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp")


class TokenStatsResponse(BaseModel):
    """Response model for token statistics."""
    total_tokens: int = Field(..., description="Total number of tokens")
    healthy_tokens: int = Field(..., description="Number of healthy tokens")
    unhealthy_tokens: int = Field(...,
                                  description="Number of unhealthy tokens")
    health_percentage: float = Field(...,
                                     description="Percentage of healthy tokens")
    token_details: Dict[str, Dict[str, Any]
                        ] = Field(..., description="Detailed token information")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp")


class VideoDownloadRequest(BaseModel):
    """Request model for video download."""
    url: str = Field(..., description="TikTok video URL", min_length=1)
    watermark: bool = Field(
        default=False, description="Whether to include watermark")
    quality: VideoQuality = Field(
        default=VideoQuality.AUTO, description="Video quality preference")
    resolve_redirects: bool = Field(
        default=True, description="Whether to resolve shortened URLs"
    )


class VideoDownloadUrls(BaseModel):
    """Video download URLs for different qualities and watermark options."""
    with_watermark: Optional[str] = Field(
        None, description="Download URL with watermark")
    without_watermark: Optional[str] = Field(
        None, description="Download URL without watermark")
    hd_url: Optional[str] = Field(
        None, description="High definition download URL")
    sd_url: Optional[str] = Field(
        None, description="Standard definition download URL")
    auto_url: Optional[str] = Field(
        None, description="Auto-selected quality download URL")


class VideoDownloadResponse(BaseModel):
    """Response model for video download information."""
    video_id: str = Field(..., description="Video ID")
    original_url: str = Field(..., description="Original TikTok URL")
    download_urls: VideoDownloadUrls = Field(
        ..., description="Available download URLs")
    quality: VideoQuality = Field(..., description="Selected quality")
    watermark: bool = Field(..., description="Watermark preference")
    file_size: Optional[int] = Field(
        None, description="Estimated file size in bytes")
    duration: Optional[int] = Field(
        None, description="Video duration in seconds")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp")


# Utility functions for converting TikTok API data to Pydantic models
def create_tiktok_user(user_data: Dict[str, Any]) -> TikTokUser:
    """Create TikTokUser from API data."""
    # Handle avatar fields - they might be strings or dicts
    def normalize_avatar(avatar_data):
        if isinstance(avatar_data, str):
            return {"url": avatar_data}
        elif isinstance(avatar_data, dict):
            return avatar_data
        else:
            return {}

    return TikTokUser(
        id=str(user_data.get("id", "")),
        username=user_data.get("uniqueId", ""),
        nickname=user_data.get("nickname", ""),
        signature=user_data.get("signature", ""),
        avatar_thumb=normalize_avatar(user_data.get("avatarThumb", {})),
        avatar_medium=normalize_avatar(user_data.get("avatarMedium", {})),
        avatar_larger=normalize_avatar(user_data.get("avatarLarger", {})),
        verified=user_data.get("verified", False),
        follower_count=user_data.get("stats", {}).get("followerCount", 0),
        following_count=user_data.get("stats", {}).get("followingCount", 0),
        heart_count=user_data.get("stats", {}).get("heartCount", 0),
        video_count=user_data.get("stats", {}).get("videoCount", 0),
        digg_count=user_data.get("stats", {}).get("diggCount", 0),
    )


def create_tiktok_video(video_data: Dict[str, Any], include_download_urls: bool = False) -> TikTokVideo:
    """Create TikTokVideo from API data."""
    # Extract hashtags from description
    desc = video_data.get("desc", "")
    hashtags = []
    mentions = []

    if desc:
        import re
        hashtags = re.findall(r'#(\w+)', desc)
        mentions = re.findall(r'@(\w+)', desc)

    # Extract download URLs if requested
    download_urls = None
    if include_download_urls:
        download_urls = extract_download_urls_from_video_data(video_data)

    return TikTokVideo(
        id=str(video_data.get("id", "")),
        desc=desc,
        create_time=video_data.get("createTime", 0),
        video=video_data.get("video", {}),
        author=create_tiktok_user(video_data.get("author", {})),
        music=video_data.get("music", {}),
        stats=video_data.get("stats", {}),
        hashtags=hashtags,
        mentions=mentions,
        challenges=video_data.get("challenges", []),
        download_urls=download_urls,
    )


def create_tiktok_hashtag(hashtag_data: Dict[str, Any]) -> TikTokHashtag:
    """Create TikTokHashtag from API data."""
    return TikTokHashtag(
        id=str(hashtag_data.get("id", "")),
        name=hashtag_data.get("name", ""),
        title=hashtag_data.get("title", ""),
        desc=hashtag_data.get("desc", ""),
        video_count=hashtag_data.get("stats", {}).get("videoCount", 0),
        view_count=hashtag_data.get("stats", {}).get("viewCount", 0),
    )


def create_tiktok_sound(sound_data: Dict[str, Any]) -> TikTokSound:
    """Create TikTokSound from API data."""
    return TikTokSound(
        id=str(sound_data.get("id", "")),
        title=sound_data.get("title", ""),
        play_url=sound_data.get("playUrl", ""),
        cover_thumb=sound_data.get("coverThumb", {}),
        cover_medium=sound_data.get("coverMedium", {}),
        cover_large=sound_data.get("coverLarge", {}),
        author_name=sound_data.get("authorName", ""),
        original=sound_data.get("original", False),
        duration=sound_data.get("duration", 0),
        album=sound_data.get("album", ""),
    )


def create_tiktok_comment(comment_data: Dict[str, Any]) -> TikTokComment:
    """Create TikTokComment from API data."""
    return TikTokComment(
        id=str(comment_data.get("cid", "")),
        text=comment_data.get("text", ""),
        create_time=comment_data.get("createTime", 0),
        user=create_tiktok_user(comment_data.get("user", {})),
        like_count=comment_data.get("diggCount", 0),
        reply_comment_total=comment_data.get("replyCommentTotal", 0),
    )


def extract_download_urls_from_video_data(video_data: Dict[str, Any]) -> VideoDownloadUrls:
    """Extract download URLs from TikTok video data."""
    video_info = video_data.get("video", {})

    # Extract URLs from different possible fields in TikTok API response
    play_addr = video_info.get("playAddr", "")
    download_addr = video_info.get("downloadAddr", "")

    # Try to get URLs from bitrate info (different qualities)
    bitrate_info = video_info.get("bitrateInfo", {})
    hd_url = None
    sd_url = None
    auto_url = None

    if bitrate_info:
        # Look for different quality variants
        for bitrate in bitrate_info:
            if isinstance(bitrate, dict):
                quality = bitrate.get("GearName", "").lower()
                url = bitrate.get("PlayAddr", {}).get("UrlList", [None])[0]
                if url:
                    if "hd" in quality or "high" in quality:
                        hd_url = url
                    elif "sd" in quality or "standard" in quality:
                        sd_url = url
                    else:
                        auto_url = url

    # Fallback to main URLs if no bitrate info
    if not any([hd_url, sd_url, auto_url]):
        auto_url = play_addr or download_addr

    # Determine watermark URLs (this is a simplified approach)
    # In practice, TikTok API may provide different URLs for watermarked vs non-watermarked
    with_watermark = play_addr or auto_url
    without_watermark = download_addr or auto_url

    return VideoDownloadUrls(
        with_watermark=with_watermark,
        without_watermark=without_watermark,
        hd_url=hd_url,
        sd_url=sd_url,
        auto_url=auto_url,
    )

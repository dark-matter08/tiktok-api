"""Basic API tests."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.models.schemas import TikTokUser, TikTokVideo

client = TestClient(app)


@pytest.fixture
def mock_tiktok_service():
    """Mock TikTok service for testing."""
    with patch("app.services.tiktok_service.get_tiktok_service") as mock:
        service = AsyncMock()
        mock.return_value = service
        yield service


@pytest.fixture
def valid_api_key():
    """Valid API key for testing."""
    return "test-api-key"


def test_root_endpoint():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "endpoints" in data


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "message" in data
    assert "version" in data


def test_trending_videos_unauthorized():
    """Test trending videos endpoint without API key."""
    response = client.get("/api/v1/trending/videos")
    assert response.status_code == 401


def test_trending_videos_invalid_api_key():
    """Test trending videos endpoint with invalid API key."""
    response = client.get(
        "/api/v1/trending/videos",
        headers={"X-API-Key": "invalid-key"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_trending_videos_success(mock_tiktok_service, valid_api_key):
    """Test successful trending videos request."""
    # Mock the service response
    mock_video_data = {
        "id": "123456789",
        "desc": "Test video",
        "createTime": 1640995200,
        "video": {"playAddr": "http://example.com/video.mp4"},
        "author": {
            "id": "user123",
            "uniqueId": "testuser",
            "nickname": "Test User",
            "signature": "Test signature",
            "avatarThumb": {},
            "avatarMedium": {},
            "avatarLarger": {},
            "verified": False,
            "stats": {
                "followerCount": 1000,
                "followingCount": 100,
                "heartCount": 5000,
                "videoCount": 50,
                "diggCount": 200
            }
        },
        "music": {"title": "Test Music"},
        "stats": {"playCount": 10000, "shareCount": 100, "commentCount": 50, "diggCount": 500}
    }

    mock_tiktok_service.get_trending_videos.return_value = [mock_video_data]

    # Mock the API key validation
    with patch("app.dependencies.get_settings") as mock_settings:
        mock_settings.return_value.api_keys = [valid_api_key]

        response = client.get(
            "/api/v1/trending/videos",
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert "videos" in data
        assert "count" in data
        assert len(data["videos"]) == 1


def test_user_info_unauthorized():
    """Test user info endpoint without API key."""
    response = client.get("/api/v1/user/testuser/info")
    assert response.status_code == 401


def test_video_info_unauthorized():
    """Test video info endpoint without API key."""
    response = client.get("/api/v1/video/123456789")
    assert response.status_code == 401


def test_hashtag_videos_unauthorized():
    """Test hashtag videos endpoint without API key."""
    response = client.get("/api/v1/hashtag/test/videos")
    assert response.status_code == 401


def test_search_users_unauthorized():
    """Test search users endpoint without API key."""
    response = client.get("/api/v1/search/users?q=test")
    assert response.status_code == 401


def test_sound_videos_unauthorized():
    """Test sound videos endpoint without API key."""
    response = client.get("/api/v1/sound/123456789/videos")
    assert response.status_code == 401


def test_invalid_endpoint():
    """Test invalid endpoint returns 404."""
    response = client.get("/api/v1/invalid/endpoint")
    assert response.status_code == 404


def test_rate_limiting():
    """Test rate limiting functionality."""
    # This would require more complex setup with Redis
    # For now, just test that the endpoint exists
    response = client.get("/api/v1/trending/videos")
    # Either unauthorized or rate limited
    assert response.status_code in [401, 429]


if __name__ == "__main__":
    pytest.main([__file__])

"""API v1 router configuration."""

from fastapi import APIRouter

from app.api.v1.endpoints import trending, user, video, hashtag, search, sound

# Create the main API v1 router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    trending.router,
    prefix="/trending",
    tags=["trending"]
)

api_router.include_router(
    user.router,
    prefix="/user",
    tags=["user"]
)

api_router.include_router(
    video.router,
    prefix="/video",
    tags=["video"]
)

api_router.include_router(
    hashtag.router,
    prefix="/hashtag",
    tags=["hashtag"]
)

api_router.include_router(
    search.router,
    prefix="/search",
    tags=["search"]
)

api_router.include_router(
    sound.router,
    prefix="/sound",
    tags=["sound"]
)

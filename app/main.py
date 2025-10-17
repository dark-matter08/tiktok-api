"""FastAPI application main module."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.openapi.utils import get_openapi
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.api.v1.router import api_router
from app.models.schemas import ErrorResponse, HealthResponse
from app.services.tiktok_service import get_tiktok_service
from app.services.token_manager import get_token_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting TikTok API Backend...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"API Keys configured: {len(settings.api_keys_list)}")
    logger.info(f"MS Tokens configured: {len(settings.ms_tokens_list)}")

    # Health check on startup
    try:
        tiktok_service = get_tiktok_service()
        health_result = await tiktok_service.health_check()
        logger.info(f"TikTok service health check: {health_result['status']}")
    except Exception as e:
        logger.warning(f"TikTok service health check failed: {e}")

    yield

    # Shutdown
    logger.info("Shutting down TikTok API Backend...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_title,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
    openapi_url="/openapi.json" if settings.environment == "development" else None,
)


def custom_openapi():
    """Custom OpenAPI schema with X-MS-Token header documentation."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add X-MS-Token header to global security schemes
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}

    # Add X-MS-Token header scheme
    openapi_schema["components"]["securitySchemes"]["MS-Token"] = {
        "type": "apiKey",
        "in": "header",
        "name": "X-MS-Token",
        "description": "Optional custom MS token to override environment-configured tokens for individual requests"
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Add CORS middleware for development
if settings.environment == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get(
    "/",
    response_model=dict,
    summary="API Root",
    description="Get API information and available endpoints"
)
async def root():
    """Get API root information."""
    return {
        "message": "TikTok API Backend",
        "version": settings.app_version,
        "environment": settings.environment,
        "docs_url": "/docs" if settings.environment == "development" else "disabled",
        "redoc_url": "/redoc" if settings.environment == "development" else "disabled",
        "endpoints": {
            "trending": "/api/v1/trending",
            "user": "/api/v1/user",
            "video": "/api/v1/video",
            "hashtag": "/api/v1/hashtag",
            "search": "/api/v1/search",
            "sound": "/api/v1/sound",
            "health": "/health"
        }
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check the health status of the API and TikTok service"
)
async def health_check():
    """Perform health check on the API and TikTok service."""
    try:
        # Check TikTok service health
        tiktok_service = get_tiktok_service()
        tiktok_health = await tiktok_service.health_check()

        # Check token manager health
        token_manager = get_token_manager()
        token_stats = token_manager.get_token_stats()

        # Determine overall health
        overall_status = "healthy" if tiktok_health["status"] == "healthy" else "unhealthy"

        return HealthResponse(
            status=overall_status,
            message=f"API is {overall_status}. TikTok service: {tiktok_health['status']}. "
            f"Token health: {token_stats['health_percentage']:.1f}%",
            version=settings.app_version
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            message=f"Health check failed: {str(e)}",
            version=settings.app_version
        )


@app.get(
    "/token-stats",
    response_model=dict,
    summary="Token Statistics",
    description="Get statistics about MS token health and usage"
)
async def get_token_stats():
    """Get token statistics (for monitoring purposes)."""
    try:
        token_manager = get_token_manager()
        stats = token_manager.get_token_stats()
        return {
            "token_stats": stats,
            "timestamp": stats.get("timestamp")
        }
    except Exception as e:
        logger.error(f"Failed to get token stats: {e}")
        return {"error": str(e)}


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.warning(f"Validation error on {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="Validation Error",
            detail=str(exc),
            status_code=422
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal Server Error",
            detail="An unexpected error occurred",
            status_code=500
        ).dict()
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        log_level="info"
    )

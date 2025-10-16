"""Configuration management using Pydantic Settings."""

import os
from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    api_keys: str = Field(
        default="default-api-key",
        description="Comma-separated list of valid API keys for authentication"
    )

    # TikTok Configuration
    ms_tokens: str = Field(
        default="",
        description="Comma-separated list of MS tokens for TikTok API rotation"
    )

    # Rate Limiting
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis URL for rate limiting storage"
    )
    rate_limit_per_minute: int = Field(
        default=100,
        description="Rate limit per minute per API key"
    )

    # Environment
    environment: str = Field(
        default="development",
        description="Environment (development, production)"
    )

    # FastAPI Configuration
    app_title: str = Field(
        default="TikTok API Backend",
        description="FastAPI application title"
    )
    app_description: str = Field(
        default="A FastAPI backend for TikTok API interactions with full endpoint coverage",
        description="FastAPI application description"
    )
    app_version: str = Field(
        default="1.0.0",
        description="Application version"
    )

    # TikTok API Configuration
    tiktok_browser: str = Field(
        default="chromium",
        description="Browser to use for TikTok API (chromium, firefox, webkit)"
    )
    tiktok_sleep_after: int = Field(
        default=3,
        description="Sleep time after creating TikTok sessions"
    )
    tiktok_num_sessions: int = Field(
        default=1,
        description="Number of TikTok sessions to create"
    )

    @property
    def api_keys_list(self) -> List[str]:
        """Get API keys as a list."""
        return [key.strip() for key in self.api_keys.split(",") if key.strip()]

    @property
    def ms_tokens_list(self) -> List[str]:
        """Get MS tokens as a list."""
        return [token.strip() for token in self.ms_tokens.split(",") if token.strip()]

    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment value."""
        allowed_envs = ["development", "production", "testing"]
        if v not in allowed_envs:
            raise ValueError(f"Environment must be one of {allowed_envs}")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings

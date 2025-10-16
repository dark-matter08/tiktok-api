"""MS Token management service with rotation support."""

import asyncio
import logging
import random
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.config import get_settings

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages MS tokens with rotation and health tracking."""

    def __init__(self):
        self.settings = get_settings()
        self.tokens: List[str] = self.settings.ms_tokens_list.copy()
        self.token_health: Dict[str, Dict[str, Any]] = {}
        self.current_index = 0
        self._lock = asyncio.Lock()

        # Initialize token health tracking
        for token in self.tokens:
            self.token_health[token] = {
                "is_healthy": True,
                "last_used": None,
                "failure_count": 0,
                "last_failure": None,
                "consecutive_failures": 0
            }

    def add_token(self, token: str) -> None:
        """Add a new token to the pool."""
        if token not in self.tokens:
            self.tokens.append(token)
            self.token_health[token] = {
                "is_healthy": True,
                "last_used": None,
                "failure_count": 0,
                "last_failure": None,
                "consecutive_failures": 0
            }
            logger.info(
                f"Added new token to pool. Total tokens: {len(self.tokens)}")

    def remove_token(self, token: str) -> None:
        """Remove a token from the pool."""
        if token in self.tokens:
            self.tokens.remove(token)
            if token in self.token_health:
                del self.token_health[token]
            logger.info(
                f"Removed token from pool. Total tokens: {len(self.tokens)}")

    def get_healthy_tokens(self) -> List[str]:
        """Get list of healthy tokens."""
        return [
            token for token in self.tokens
            if self.token_health.get(token, {}).get("is_healthy", False)
        ]

    async def get_token(self, strategy: str = "round_robin") -> Optional[str]:
        """Get a token using the specified strategy."""
        async with self._lock:
            healthy_tokens = self.get_healthy_tokens()

            if not healthy_tokens:
                logger.warning("No healthy tokens available")
                return None

            if strategy == "round_robin":
                token = self._get_round_robin_token(healthy_tokens)
            elif strategy == "random":
                token = self._get_random_token(healthy_tokens)
            elif strategy == "least_used":
                token = self._get_least_used_token(healthy_tokens)
            else:
                token = self._get_round_robin_token(healthy_tokens)

            # Update last used timestamp
            if token:
                self.token_health[token]["last_used"] = datetime.utcnow()

            return token

    def _get_round_robin_token(self, healthy_tokens: List[str]) -> str:
        """Get token using round-robin strategy."""
        if not healthy_tokens:
            return None

        token = healthy_tokens[self.current_index % len(healthy_tokens)]
        self.current_index = (self.current_index + 1) % len(healthy_tokens)
        return token

    def _get_random_token(self, healthy_tokens: List[str]) -> str:
        """Get token using random strategy."""
        return random.choice(healthy_tokens) if healthy_tokens else None

    def _get_least_used_token(self, healthy_tokens: List[str]) -> str:
        """Get token that was used least recently."""
        if not healthy_tokens:
            return None

        least_used_token = min(
            healthy_tokens,
            key=lambda t: self.token_health[t]["last_used"] or datetime.min
        )
        return least_used_token

    async def mark_token_success(self, token: str) -> None:
        """Mark a token as successful."""
        if token in self.token_health:
            self.token_health[token]["consecutive_failures"] = 0
            self.token_health[token]["is_healthy"] = True
            logger.debug(f"Token marked as successful: {token[:10]}...")

    async def mark_token_failure(self, token: str, error: Optional[str] = None) -> None:
        """Mark a token as failed."""
        if token not in self.token_health:
            return

        health_info = self.token_health[token]
        health_info["failure_count"] += 1
        health_info["consecutive_failures"] += 1
        health_info["last_failure"] = datetime.utcnow()

        # Mark as unhealthy if too many consecutive failures
        max_consecutive_failures = 3
        if health_info["consecutive_failures"] >= max_consecutive_failures:
            health_info["is_healthy"] = False
            logger.warning(
                f"Token marked as unhealthy due to {health_info['consecutive_failures']} "
                f"consecutive failures: {token[:10]}..."
            )

        logger.debug(
            f"Token failure recorded: {token[:10]}... (Error: {error})")

    async def reset_token_health(self, token: str) -> None:
        """Reset a token's health status."""
        if token in self.token_health:
            self.token_health[token] = {
                "is_healthy": True,
                "last_used": None,
                "failure_count": 0,
                "last_failure": None,
                "consecutive_failures": 0
            }
            logger.info(f"Token health reset: {token[:10]}...")

    async def cleanup_unhealthy_tokens(self, max_age_hours: int = 24) -> None:
        """Remove tokens that have been unhealthy for too long."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

        tokens_to_remove = []
        for token, health_info in self.token_health.items():
            if (not health_info["is_healthy"] and
                health_info["last_failure"] and
                    health_info["last_failure"] < cutoff_time):
                tokens_to_remove.append(token)

        for token in tokens_to_remove:
            self.remove_token(token)
            logger.info(f"Removed unhealthy token: {token[:10]}...")

    def get_token_stats(self) -> Dict[str, Any]:
        """Get statistics about token usage."""
        total_tokens = len(self.tokens)
        healthy_tokens = len(self.get_healthy_tokens())
        unhealthy_tokens = total_tokens - healthy_tokens

        return {
            "total_tokens": total_tokens,
            "healthy_tokens": healthy_tokens,
            "unhealthy_tokens": unhealthy_tokens,
            "health_percentage": (healthy_tokens / total_tokens * 100) if total_tokens > 0 else 0,
            "token_details": {
                token: {
                    "is_healthy": health_info["is_healthy"],
                    "failure_count": health_info["failure_count"],
                    "consecutive_failures": health_info["consecutive_failures"],
                    "last_used": health_info["last_used"].isoformat() if health_info["last_used"] else None,
                    "last_failure": health_info["last_failure"].isoformat() if health_info["last_failure"] else None
                }
                for token, health_info in self.token_health.items()
            }
        }


# Global token manager instance
token_manager = TokenManager()


def get_token_manager() -> TokenManager:
    """Get the global token manager instance."""
    return token_manager

"""Proxy models for proxy management."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Proxy:
    """Proxy data model."""

    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    country_code: Optional[str] = None

    def to_playwright_format(self) -> dict:
        """Convert proxy to Playwright format for TikTok-Api."""
        proxy_dict = {
            "server": f"http://{self.host}:{self.port}"
        }

        if self.username and self.password:
            proxy_dict["username"] = self.username
            proxy_dict["password"] = self.password

        return proxy_dict

    def __str__(self) -> str:
        if self.username and self.password:
            return f"http://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"http://{self.host}:{self.port}"


class ProxyFormat:
    """Proxy format constants."""
    PLAYWRIGHT = "playwright"
    STRING = "string"


class ProxyObject:
    """Proxy object that TikTok-Api expects with format() method."""

    def __init__(self, proxy: Proxy):
        self.proxy = proxy

    def format(self, format_type: str = ProxyFormat.PLAYWRIGHT) -> dict:
        """Format proxy for different use cases."""
        if format_type == ProxyFormat.PLAYWRIGHT:
            return self.proxy.to_playwright_format()
        elif format_type == ProxyFormat.STRING:
            return {"proxy": str(self.proxy)}
        else:
            return self.proxy.to_playwright_format()

    def __str__(self) -> str:
        return str(self.proxy)

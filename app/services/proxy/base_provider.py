"""Base proxy provider interface."""

from abc import ABC, abstractmethod
from typing import List, Optional
from app.services.proxy.models import Proxy, ProxyObject
from app.services.proxy.algorithms import Algorithm, RoundRobin


class ProxyProvider(ABC):
    """Abstract base class for proxy providers."""

    def __init__(self, algorithm: Optional[Algorithm] = None):
        self.algorithm = algorithm or RoundRobin()
        self._proxies: List[Proxy] = []

    @abstractmethod
    async def fetch_proxies(self) -> List[Proxy]:
        """Fetch proxies from the provider."""
        pass

    def list_proxies(self) -> List[Proxy]:
        """Get list of available proxies."""
        return self._proxies

    def get_proxy(self, *args, **kwargs) -> Optional[ProxyObject]:
        """Get next proxy as ProxyObject with format() method."""
        if not self._proxies:
            return None

        proxy = self.algorithm.select(self._proxies)
        if proxy:
            return ProxyObject(proxy)
        return None

    def get_proxy_dict(self) -> Optional[dict]:
        """Get next proxy in Playwright format."""
        if not self._proxies:
            return None

        proxy = self.algorithm.select(self._proxies)
        if proxy:
            return proxy.to_playwright_format()
        return None

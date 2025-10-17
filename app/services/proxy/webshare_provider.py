"""Webshare proxy provider implementation."""

import logging
from typing import List, Optional
import httpx

from app.services.proxy.base_provider import ProxyProvider
from app.services.proxy.models import Proxy
from app.services.proxy.algorithms import Algorithm

logger = logging.getLogger(__name__)


class Webshare(ProxyProvider):
    """Webshare proxy provider."""

    WEBSHARE_API_URL = "https://proxy.webshare.io/api/v2/proxy/list/"

    def __init__(self, api_key: str, algorithm: Optional[Algorithm] = None, cookie: Optional[str] = None):
        super().__init__(algorithm)
        self.api_key = api_key
        self.cookie = cookie or "_tid=53ee2bfc-4e7f-4752-a718-e72fd5db7e3c"
        self._initialized = False

    async def fetch_proxies(self) -> List[Proxy]:
        """Fetch proxies from Webshare API."""
        try:
            headers = {
                "Authorization": f"Token {self.api_key}",
                "Cookie": self.cookie
            }

            # Add query parameters like in the working curl
            params = {
                "mode": "direct",
                "page": 1,
                "page_size": 100
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.WEBSHARE_API_URL, headers=headers, params=params)
                response.raise_for_status()

                data = response.json()
                proxies = []

                for result in data.get("results", []):
                    proxy = Proxy(
                        host=result["proxy_address"],
                        port=result["port"],
                        username=result.get("username"),
                        password=result.get("password"),
                        country_code=result.get("country_code")
                    )
                    proxies.append(proxy)

                self._proxies = proxies
                self._initialized = True
                logger.info(f"Fetched {len(proxies)} proxies from Webshare")
                return proxies

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch proxies from Webshare: {e}")
            logger.error(
                f"API Key: {self.api_key[:10]}...{self.api_key[-10:] if len(self.api_key) > 20 else self.api_key}")
            logger.error(f"Cookie: {self.cookie}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching proxies: {e}")
            return []

    async def ensure_initialized(self):
        """Ensure proxies are fetched before use."""
        if not self._initialized:
            await self.fetch_proxies()

"""Proxy rotation algorithms."""

import random
from abc import ABC, abstractmethod
from typing import List, Optional
from app.services.proxy.models import Proxy


class Algorithm(ABC):
    """Base algorithm class for proxy selection."""

    @abstractmethod
    def select(self, proxies: List[Proxy]) -> Optional[Proxy]:
        """Select a proxy from the list."""
        pass


class RoundRobin(Algorithm):
    """Round-robin proxy selection algorithm."""

    def __init__(self):
        self.current_index = 0

    def select(self, proxies: List[Proxy]) -> Optional[Proxy]:
        """Select next proxy in rotation."""
        if not proxies:
            return None

        proxy = proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(proxies)
        return proxy


class Random(Algorithm):
    """Random proxy selection algorithm."""

    def select(self, proxies: List[Proxy]) -> Optional[Proxy]:
        """Select random proxy from list."""
        if not proxies:
            return None
        return random.choice(proxies)


class First(Algorithm):
    """Always select first proxy."""

    def select(self, proxies: List[Proxy]) -> Optional[Proxy]:
        """Select first proxy."""
        if not proxies:
            return None
        return proxies[0]

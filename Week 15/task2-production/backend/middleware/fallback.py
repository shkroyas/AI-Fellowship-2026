"""
Fallback Manager Module.

Manages LLM provider fallback chains for high availability.
When the primary provider fails, automatically switches to
alternative providers in priority order.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class FallbackManager:
    """
    Manages fallback provider chains for high availability.

    Maintains an ordered list of LLM providers and tracks
    their health status. When a provider fails, provides
    the next healthy alternative.
    """

    def __init__(self):
        self._providers: list[str] = []
        self._health: dict[str, bool] = {}
        self._failure_counts: dict[str, int] = {}
        self._max_failures: int = 3  # Mark unhealthy after N consecutive failures

    def register_providers(self, providers: list[str]) -> None:
        """Register providers in priority order."""
        self._providers = providers
        for p in providers:
            self._health[p] = True
            self._failure_counts[p] = 0
        logger.info(f"Fallback chain: {' → '.join(providers)}")

    def get_next_fallback(self, failed_provider: Optional[str] = None) -> Optional[str]:
        """
        Get the next available fallback provider.

        Args:
            failed_provider: The provider that just failed.

        Returns:
            Name of the next available provider, or None if all failed.
        """
        if failed_provider:
            self._failure_counts[failed_provider] = self._failure_counts.get(failed_provider, 0) + 1

            if self._failure_counts[failed_provider] >= self._max_failures:
                self._health[failed_provider] = False
                logger.warning(f"Provider '{failed_provider}' marked unhealthy after {self._max_failures} failures")

        # Find next healthy provider (skip the failed one)
        for provider in self._providers:
            if provider != failed_provider and self._health.get(provider, False):
                logger.info(f"Fallback: {failed_provider} → {provider}")
                return provider

        logger.error("All providers have failed!")
        return None

    def mark_healthy(self, provider: str) -> None:
        """Mark a provider as healthy (e.g., after successful request)."""
        self._health[provider] = True
        self._failure_counts[provider] = 0

    def mark_unhealthy(self, provider: str) -> None:
        """Explicitly mark a provider as unhealthy."""
        self._health[provider] = False

    def reset(self) -> None:
        """Reset all providers to healthy state."""
        for p in self._providers:
            self._health[p] = True
            self._failure_counts[p] = 0

    def status(self) -> dict:
        """Get current fallback chain status."""
        return {
            "providers": [
                {
                    "name": p,
                    "healthy": self._health.get(p, False),
                    "failures": self._failure_counts.get(p, 0),
                }
                for p in self._providers
            ],
        }

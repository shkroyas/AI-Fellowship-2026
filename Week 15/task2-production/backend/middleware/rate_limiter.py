"""
Rate Limiter Middleware.

Implements token bucket rate limiting to prevent API abuse
and ensure fair resource usage across clients.
"""

import time
import logging
from collections import defaultdict
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket algorithm for rate limiting."""

    def __init__(self, rate: float, burst: int):
        """
        Args:
            rate: Tokens added per second
            burst: Maximum bucket capacity
        """
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = time.monotonic()

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if allowed."""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.last_update = now

        # Add tokens based on elapsed time
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    @property
    def remaining(self) -> int:
        """Number of remaining tokens."""
        return max(0, int(self.tokens))


class RateLimiter:
    """Per-client rate limiter using token buckets."""

    def __init__(self, requests_per_minute: int = 60, burst_size: int = 10):
        self.rate = requests_per_minute / 60.0  # tokens per second
        self.burst = burst_size
        self._buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(self.rate, self.burst)
        )
        self._total_requests = 0
        self._total_limited = 0

    def is_allowed(self, client_id: str) -> bool:
        """Check if a request from this client is allowed."""
        self._total_requests += 1
        allowed = self._buckets[client_id].consume()
        if not allowed:
            self._total_limited += 1
            logger.warning(f"Rate limited client: {client_id}")
        return allowed

    def remaining(self, client_id: str) -> int:
        """Get remaining requests for a client."""
        return self._buckets[client_id].remaining

    def stats(self) -> dict:
        """Get rate limiter statistics."""
        return {
            "total_requests": self._total_requests,
            "total_limited": self._total_limited,
            "active_clients": len(self._buckets),
            "rate_per_minute": int(self.rate * 60),
            "burst_size": self.burst,
        }


# Global rate limiter instance
rate_limiter: Optional[RateLimiter] = None


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(self, app, requests_per_minute: int = 60, burst_size: int = 10):
        super().__init__(app)
        global rate_limiter
        rate_limiter = RateLimiter(requests_per_minute, burst_size)

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ("/health", "/docs", "/openapi.json"):
            return await call_next(request)

        # Get client identifier (IP address)
        client_ip = request.client.host if request.client else "unknown"

        if not rate_limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please wait before trying again.",
                    "retry_after_seconds": 60 / (rate_limiter.rate * 60),
                },
                headers={
                    "Retry-After": str(int(60 / (rate_limiter.rate * 60))),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)

        # Add rate limit headers
        remaining = rate_limiter.remaining(client_ip)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Limit"] = str(int(rate_limiter.rate * 60))

        return response

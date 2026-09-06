"""
HTTP Session — Shared aiohttp session with connection pooling and retry.

REL-01: Centralizes HTTP management for connection reuse, timeout, retry.
"""

import asyncio
import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# Default timeout configuration
DEFAULT_TOTAL_TIMEOUT = 300  # 5 minutes
DEFAULT_CONNECT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0
DEFAULT_RETRY_BACKOFF = 2.0

# Shared session singleton
_session: aiohttp.ClientSession | None = None
_session_lock = asyncio.Lock()


class HTTPError(Exception):
    """HTTP request failed after all retries."""

    def __init__(self, url: str, status: int | None, message: str, attempts: int):
        self.url = url
        self.status = status
        self.message = message
        self.attempts = attempts
        super().__init__(f"HTTP {status} after {attempts} attempts: {url} — {message}")


class HTTPTimeoutError(HTTPError):
    """HTTP request timed out after all retries."""


async def get_session(
    *,
    total_timeout: int = DEFAULT_TOTAL_TIMEOUT,
    connect_timeout: int = DEFAULT_CONNECT_TIMEOUT,
) -> aiohttp.ClientSession:
    """Get or create the shared aiohttp session (singleton)."""
    global _session
    if _session is not None and not _session.closed:
        return _session

    async with _session_lock:
        # Double-check after acquiring lock
        if _session is not None and not _session.closed:
            return _session

        timeout = aiohttp.ClientTimeout(total=total_timeout, connect=connect_timeout)
        connector = aiohttp.TCPConnector(
            limit=10,  # Max simultaneous connections
            limit_per_host=5,  # Max per host
            ttl_dns_cache=300,  # DNS cache TTL
            enable_cleanup_closed=True,
        )
        _session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
        )
        logger.info(
            "HTTP session created (timeout=%ds, connect=%ds)", total_timeout, connect_timeout
        )
        return _session


async def close_session() -> None:
    """Close the shared session (call on shutdown)."""
    global _session
    if _session is not None and not _session.closed:
        await _session.close()
        _session = None
        logger.info("HTTP session closed")


async def post_json(
    url: str,
    json: dict[str, Any] | None = None,
    *,
    total_timeout: int = DEFAULT_TOTAL_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    retry_backoff: float = DEFAULT_RETRY_BACKOFF,
) -> dict[str, Any]:
    """
    POST JSON with retry and exponential backoff.

    Returns parsed JSON response.
    Raises HTTPError or HTTPTimeoutError on failure.
    """
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            session = await get_session(total_timeout=total_timeout)
            async with session.post(url, json=json) as resp:
                if resp.status >= 500:
                    # Server error — retry
                    body = await resp.text()
                    last_error = HTTPError(url, resp.status, body[:200], attempt)
                    logger.warning(
                        "POST %s returned %d (attempt %d/%d): %s",
                        url,
                        resp.status,
                        attempt,
                        max_retries,
                        body[:100],
                    )
                    await asyncio.sleep(retry_delay * (retry_backoff ** (attempt - 1)))
                    continue
                if resp.status >= 400:
                    # Client error — don't retry
                    body = await resp.text()
                    raise HTTPError(url, resp.status, body[:200], attempt)
                return await resp.json()
        except TimeoutError:
            last_error = HTTPTimeoutError(url, None, "timeout", attempt)
            logger.warning(
                "POST %s timed out (attempt %d/%d)",
                url,
                attempt,
                max_retries,
            )
            await asyncio.sleep(retry_delay * (retry_backoff ** (attempt - 1)))
        except aiohttp.ClientError as e:
            last_error = HTTPError(url, None, str(e)[:200], attempt)
            logger.warning(
                "POST %s client error (attempt %d/%d): %s",
                url,
                attempt,
                max_retries,
                str(e)[:100],
            )
            await asyncio.sleep(retry_delay * (retry_backoff ** (attempt - 1)))

    # All retries exhausted
    if last_error:
        raise last_error
    raise HTTPError(url, None, "unknown error", max_retries)

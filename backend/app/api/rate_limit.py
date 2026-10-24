import math
import threading
import time
from collections import deque

from fastapi import HTTPException, Request

from app.core.config import settings

_WINDOW_SECONDS = 60.0


class SlidingWindowLimiter:
    """At most `settings.rate_limit_per_minute` requests per client in any 60-second span.

    Kept in memory, so the count is per process: enough for the single-process deployment this app
    targets. Behind the frontend's nginx, uvicorn runs with --proxy-headers, which replaces the
    proxy's address in `request.client` with the client's from X-Forwarded-For. A client that stops
    sending keeps a small entry until restart, which is acceptable at this scale.
    """

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def wait_seconds(self, client: str) -> float | None:
        """Record a request from `client`; None if it is allowed, else the seconds until it would be."""
        now = self._clock()
        with self._lock:
            hits = self._hits.setdefault(client, deque())
            while hits and now - hits[0] >= _WINDOW_SECONDS:
                hits.popleft()
            if len(hits) >= settings.rate_limit_per_minute:
                return _WINDOW_SECONDS - (now - hits[0])
            hits.append(now)
            return None


_limiter = SlidingWindowLimiter()


def rate_limit(request: Request) -> None:
    """Route dependency: every request on these endpoints runs the LLM pipeline, so each one is metered."""
    client = request.client.host if request.client else "unknown"
    wait = _limiter.wait_seconds(client)
    if wait is not None:
        raise HTTPException(
            status_code=429,
            detail={"code": "rate_limited", "message": "Too many requests; please wait a moment and try again."},
            headers={"Retry-After": str(math.ceil(wait))},
        )

"""Per-client request rate limiting (sliding one-minute window, in memory, no external store).

Protects the API, and through it the data.gov.in quota, from bursts. In-memory state is per
process; that is sufficient for a single-instance deployment (see ADR-021).
"""

from __future__ import annotations

import time
from collections import deque
from threading import Lock

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

EXEMPT_PATHS = {"/api/v1/health", "/", "/docs", "/openapi.json", "/redoc"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, per_minute: int) -> None:
        super().__init__(app)
        self.per_minute = per_minute
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def _allow(self, client: str) -> tuple[bool, int]:
        now = time.monotonic()
        with self._lock:
            q = self._hits.setdefault(client, deque())
            while q and now - q[0] >= 60:
                q.popleft()
            if len(q) >= self.per_minute:
                return False, max(1, int(60 - (now - q[0])) + 1)
            q.append(now)
            if len(self._hits) > 10_000:  # bound memory: drop idle clients
                for k in [k for k, v in self._hits.items() if not v]:
                    del self._hits[k]
            return True, 0

    async def dispatch(self, request: Request, call_next):
        if self.per_minute <= 0 or request.url.path in EXEMPT_PATHS or request.method == "OPTIONS":
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        ok, retry_after = self._allow(client)
        if not ok:
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={
                    "error": {
                        "code": "rate_limited",
                        "message": f"Too many requests. Limit is {self.per_minute} per minute.",
                        "details": {"retry_after_seconds": retry_after},
                    }
                },
            )
        return await call_next(request)

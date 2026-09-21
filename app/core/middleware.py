import time
import uuid
import logging
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger("api.access")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class RequestLoggingAndTimingMiddleware(BaseHTTPMiddleware):
    """
    Twelve-Factor compliance: Logs structured access records to stdout,
    generates or propagates X-Request-ID, and measures execution timing.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}s"

        client_ip = request.client.host if request.client else "unknown"
        logger.info(
            f"{request.method} {request.url.path} "
            f"-> {response.status_code} ({process_time:.4f}s) "
            f"[ip: {client_ip}] [req_id: {request_id}]"
        )
        return response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Rate limiter for public endpoints and brute-force protection on /auth/login.
    Returns 429 Too Many Requests + Retry-After header.
    """
    def __init__(self, app):
        super().__init__(app)
        # Store timestamp lists: ip -> list of request timestamps
        self._login_hits: Dict[str, List[float]] = defaultdict(list)
        self._general_hits: Dict[str, List[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Exclude OpenAPI documentation and stream endpoints from aggressive rate limits
        path = request.url.path
        if path.startswith("/docs") or path.startswith("/openapi.json") or path.endswith("/stream"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        window = 60.0  # 1 minute sliding window

        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

        # 1. Login rate limiting (brute-force defense: 5/min)
        if path.endswith("/auth/login") and request.method == "POST":
            timestamps = [t for t in self._login_hits[client_ip] if now - t < window]
            if len(timestamps) >= settings.RATE_LIMIT_LOGIN_PER_MINUTE:
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": "60"},
                    content={
                        "error": {
                            "code": "RATE_LIMITED",
                            "message": "Too many failed login attempts. Please retry in 60 seconds.",
                            "request_id": request_id,
                        }
                    },
                )
            timestamps.append(now)
            self._login_hits[client_ip] = timestamps

        # 2. General public rate limiting (60/min)
        timestamps = [t for t in self._general_hits[client_ip] if now - t < window]
        if len(timestamps) >= settings.RATE_LIMIT_PUBLIC_PER_MINUTE:
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": "60"},
                content={
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "Rate limit exceeded. Please retry in 60 seconds.",
                        "request_id": request_id,
                    }
                },
            )
        timestamps.append(now)
        self._general_hits[client_ip] = timestamps

        return await call_next(request)

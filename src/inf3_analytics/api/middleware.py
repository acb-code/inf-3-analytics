"""Security middleware for defense-in-depth."""

import logging
import os

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

# Paths that bypass API key auth (health check for Docker probes)
_PUBLIC_PATHS = frozenset({"/health"})


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Defense-in-depth auth: requires API key if configured.

    If INF3_API_KEY is set, all requests (except health) must include
    a matching ``X-API-Key`` header. When the env var is unset the
    middleware is a no-op, preserving the current proxy-only auth flow.
    """

    def __init__(self, app, api_key: str | None = None) -> None:  # noqa: ANN001
        super().__init__(app)
        self.api_key = api_key or os.environ.get("INF3_API_KEY")

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if self.api_key is None:
            return await call_next(request)

        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        provided = request.headers.get("X-API-Key")
        if provided != self.api_key:
            logger.warning("Rejected request to %s: missing or invalid API key", request.url.path)
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})

        return await call_next(request)

"""CSRF defence for cookie-authenticated requests (MVP FR-3).

State-changing requests that carry the session cookie must come from an allowed Origin and use a
JSON (or multipart upload) body. Requests without the cookie cannot act as a user, so they pass.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ovas_api.auth import COOKIE
from ovas_api.config import get_settings

UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}
BODY_TYPES = ("application/json", "multipart/form-data")


class OriginGuard(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in UNSAFE and COOKIE in request.cookies:
            origin = request.headers.get("origin")
            if origin not in get_settings().allowed_origins:
                return JSONResponse({"detail": "Request origin is not allowed."}, status_code=403)
            content_type = request.headers.get("content-type", "")
            has_body = request.headers.get("content-length", "0") != "0"
            if has_body and not content_type.startswith(BODY_TYPES):
                return JSONResponse({"detail": "Send JSON."}, status_code=415)
        return await call_next(request)

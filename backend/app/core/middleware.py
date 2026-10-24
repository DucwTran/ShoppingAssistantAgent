import re
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import log_event, logger, request_id_var
from app.guards.input_guard import InvalidQueryError


_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")
_UNLOGGED_PREFIX = "/health"  # polled every few seconds by the container runtime


class RequestContextMiddleware:
    """Give each request an id, carried by every log line it causes and returned as X-Request-ID.

    The caller's X-Request-ID is reused when well-formed, so one id can follow a request from the
    proxy through the API. One access line per request records method, path, status and duration;
    for a stream the duration runs until the stream ends. Pure ASGI rather than BaseHTTPMiddleware,
    so streamed responses pass through untouched.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = dict(scope["headers"]).get(b"x-request-id", b"").decode("latin-1")
        request_id = incoming if _VALID_REQUEST_ID.fullmatch(incoming) else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status = 500

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message["headers"] = [*message.get("headers", []), (b"x-request-id", request_id.encode())]
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            if not scope["path"].startswith(_UNLOGGED_PREFIX):
                log_event(node="api", event="request", status="warning" if status >= 500 else "info",
                          method=scope["method"], path=scope["path"], status_code=status,
                          duration_ms=round((time.perf_counter() - started) * 1000))
            request_id_var.reset(token)


def add_request_context(app: FastAPI) -> None:
    # Added last, so it is the outermost middleware and wraps CORS and the error handlers too
    app.add_middleware(RequestContextMiddleware)


def add_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["POST"],
        allow_headers=["Content-Type"],
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidQueryError)
    async def _invalid_query_handler(request: Request, exc: InvalidQueryError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"error": {"code": "invalid_query", "message": str(exc)}})

    @app.exception_handler(AppError)
    async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content=exc.body())

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail and "message" in detail:
            body = {"error": detail}
        else:
            body = {"error": {"code": "http_error", "message": str(detail)}}
        return JSONResponse(status_code=exc.status_code, content=body, headers=getattr(exc, "headers", None))

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception while handling %s %s", request.method, request.url.path)
        # bare-Exception handlers run in Starlette's ServerErrorMiddleware, which sits outside
        # CORSMiddleware — its response never passes through CORS, so the header must be set here
        origin = request.headers.get("origin")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "An unexpected error occurred."}},
            headers={"Access-Control-Allow-Origin": origin} if origin in settings.cors_origins else {},
        )

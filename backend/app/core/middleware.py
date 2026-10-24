from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError
from app.core.logging import logger
from app.guards.input_guard import InvalidQueryError

# The Vite dev server - the only client this API is meant to serve
FRONTEND_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def add_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=FRONTEND_ORIGINS,
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
            headers={"Access-Control-Allow-Origin": origin} if origin in FRONTEND_ORIGINS else {},
        )

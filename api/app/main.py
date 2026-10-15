"""Application factory."""

import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.auth import TokenVerifier, http_jwks_fetcher
from app.config import Settings, get_settings
from app.db import Database
from app.routers import health, me, practice

logger = logging.getLogger("prepmate")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "same-site",
    "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
}
# This API only ever returns JSON, so nothing may be loaded or framed from it.
API_CSP = "default-src 'none'; frame-ancestors 'none'"
HSTS = "max-age=63072000; includeSubDomains"


def _error(status_code: int, code: str, message: str, request: Request) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


def create_app(
    settings: Settings | None = None,
    *,
    verifier: TokenVerifier | None = None,
    database: Database | None = None,
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await app.state.database.open()
        try:
            yield
        finally:
            await app.state.database.close()

    app = FastAPI(
        title="PrepMate AI API",
        version="0.1.0",
        lifespan=lifespan,
        # Interactive docs are a development convenience, not a public surface.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    app.state.settings = settings
    app.state.database = database or Database(
        settings.database_url.get_secret_value(), max_size=settings.db_pool_max_size
    )
    app.state.verifier = verifier or TokenVerifier(
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        fetch_jwks=http_jwks_fetcher(settings.jwks_url),
    )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = uuid.uuid4().hex
        try:
            response = await call_next(request)
        except Exception:
            # Log the detail for us; give the caller nothing but a reference.
            logger.exception("Unhandled error [request_id=%s]", request.state.request_id)
            response = _error(500, "internal_error", "Something went wrong on our side.", request)
        response.headers["X-Request-ID"] = request.state.request_id
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if request.url.path.startswith("/v1"):
            response.headers["Cache-Control"] = "no-store"
        if settings.is_production:
            response.headers.setdefault("Content-Security-Policy", API_CSP)
            response.headers.setdefault("Strict-Transport-Security", HSTS)
        return response

    # Added last so it wraps everything: even error responses carry CORS headers.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,  # we use Bearer tokens, never cookies
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        codes = {
            401: "unauthenticated",
            403: "forbidden",
            404: "not_found",
            422: "invalid_request",
            429: "rate_limited",
            503: "unavailable",
        }
        response = _error(
            exc.status_code,
            codes.get(exc.status_code, "request_failed"),
            str(exc.detail),
            request,
        )
        if exc.headers:
            response.headers.update(exc.headers)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(part) for part in first.get("loc", ())[1:])
        message = first.get("msg", "Invalid request.")
        return _error(422, "invalid_request", f"{field}: {message}" if field else message, request)

    app.include_router(health.router)
    app.include_router(me.router)
    app.include_router(practice.router)
    return app

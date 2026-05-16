# app/main.py
# ─────────────────────────────────────────────
# QUORUM — FastAPI Application Factory
# Entry point for uvicorn: uvicorn app.main:app
# ─────────────────────────────────────────────

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

import sentry_sdk

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging import configure_logging
from app.api.routers import (
    auth,
    orgs,
    users,
    meetings,
    surveys,
    sessions,
    decisions,
    outcomes,
    intelligence,
    webhooks,
    gdpr,
)

log = structlog.get_logger()


# ── Lifespan (startup/shutdown) ────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run on startup and shutdown."""
    # Startup
    configure_logging()
    log.info("quorum.startup", env=settings.APP_ENV, version=settings.APP_VERSION)

    # Verify DB connection
    try:
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        log.info("quorum.db.connected")
    except Exception as e:
        log.error("quorum.db.connection_failed", error=str(e))
        raise

    yield

    # Shutdown
    await engine.dispose()
    log.info("quorum.shutdown")


# ── Sentry (production only) ───────────────────
if settings.SENTRY_DSN and settings.APP_ENV == "production":
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.APP_ENV,
        traces_sample_rate=0.1,       # 10% of requests traced
        profiles_sample_rate=0.1,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            StarletteIntegration(transaction_style="endpoint"),
        ],
        before_send=_scrub_sensitive_data,
    )


def _scrub_sensitive_data(event, hint):
    """Remove sensitive fields from Sentry events before sending."""
    # Never send these to Sentry
    sensitive_keys = {
        "password", "token", "secret", "key", "authorization",
        "respondent_hash", "speaker_hash", "api_key"
    }
    if "request" in event and "headers" in event["request"]:
        event["request"]["headers"] = {
            k: "***" if k.lower() in sensitive_keys else v
            for k, v in event["request"]["headers"].items()
        }
    return event


# ── App factory ────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title="Quorum API",
        description="Collective Intelligence Platform — REST API",
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.APP_ENV != "production" else None,
        redoc_url="/redoc" if settings.APP_ENV != "production" else None,
        openapi_url="/openapi.json" if settings.APP_ENV != "production" else None,
        lifespan=lifespan,
    )

    _add_middleware(app)
    _add_exception_handlers(app)
    _add_routers(app)
    _add_health_check(app)

    return app


def _add_middleware(app: FastAPI) -> None:
    # CORS — exact origins only (never *)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Survey-Token"],
    )

    # Gzip responses over 1KB
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Request ID + structured logging
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # Bind request context to all log calls within this request
        with structlog.contextvars.bound_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        ):
            start_time = time.perf_counter()
            response: Response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            log.info(
                "http.request",
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

            response.headers["X-Request-ID"] = request_id
            return response

    # Set org_id in DB session for Row Level Security
    @app.middleware("http")
    async def rls_middleware(request: Request, call_next):
        """
        Sets app.current_org_id PostgreSQL session variable.
        This enables Row Level Security policies on all tables.
        The org_id comes from the verified JWT — not from user input.
        """
        # JWT validation happens in individual route dependencies.
        # The DB session variable is set inside route handlers after
        # auth is verified, using: await set_rls_org_id(db, org_id)
        return await call_next(request)


def _add_exception_handlers(app: FastAPI) -> None:
    from fastapi import HTTPException
    from app.core.exceptions import (
        QuorumError, NotFoundError, ForbiddenError,
        ValidationError, RateLimitError
    )

    @app.exception_handler(QuorumError)
    async def quorum_error_handler(request: Request, exc: QuorumError):
        log.warning("quorum.error", error_code=exc.code, message=exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.code,
                "message": exc.message,
                "request_id": getattr(request.state, "request_id", None),
            }
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "message": exc.detail,
                "request_id": getattr(request.state, "request_id", None),
            }
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        log.error(
            "quorum.unhandled_error",
            error=str(exc),
            path=request.url.path,
            exc_info=True,
        )
        # NEVER expose internal error details in production
        message = str(exc) if settings.APP_ENV == "development" else "Internal server error"
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": message,
                "request_id": getattr(request.state, "request_id", None),
            }
        )


def _add_routers(app: FastAPI) -> None:
    prefix = "/v1"
    app.include_router(auth.router,         prefix=f"{prefix}/auth",         tags=["auth"])
    app.include_router(orgs.router,         prefix=f"{prefix}/org",          tags=["organization"])
    app.include_router(users.router,        prefix=f"{prefix}/users",        tags=["users"])
    app.include_router(meetings.router,     prefix=f"{prefix}/meetings",     tags=["meetings"])
    app.include_router(surveys.router,      prefix=f"{prefix}/meetings",     tags=["surveys"])
    app.include_router(sessions.router,     prefix=f"{prefix}/meetings",     tags=["live-session"])
    app.include_router(decisions.router,    prefix=f"{prefix}/decisions",    tags=["decisions"])
    app.include_router(outcomes.router,     prefix=f"{prefix}/decisions",    tags=["outcomes"])
    app.include_router(intelligence.router, prefix=f"{prefix}/intelligence", tags=["intelligence"])
    app.include_router(webhooks.router,     prefix="/webhooks",              tags=["webhooks"])
    app.include_router(gdpr.router,         prefix=f"{prefix}/gdpr",         tags=["gdpr"])


def _add_health_check(app: FastAPI) -> None:
    from app.core.database import engine
    import redis.asyncio as aioredis

    @app.get("/health", include_in_schema=False)
    async def health():
        checks = {"status": "ok", "version": settings.APP_VERSION}

        # DB check
        try:
            async with engine.begin() as conn:
                await conn.execute("SELECT 1")
            checks["db"] = "ok"
        except Exception:
            checks["db"] = "error"
            checks["status"] = "degraded"

        # Redis check
        try:
            r = aioredis.from_url(settings.REDIS_URL)
            await r.ping()
            await r.aclose()
            checks["redis"] = "ok"
        except Exception:
            checks["redis"] = "error"
            checks["status"] = "degraded"

        status_code = 200 if checks["status"] == "ok" else 503
        return JSONResponse(content=checks, status_code=status_code)


# ── App instance ───────────────────────────────
app = create_app()

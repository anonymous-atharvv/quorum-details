# ═══════════════════════════════════════════════════════════════
# app/core/config.py — Application settings from environment
# ═══════════════════════════════════════════════════════════════
from __future__ import annotations
from functools import lru_cache
from typing import Literal
from pydantic import field_validator, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # ── Auth0 ──────────────────────────────────
    AUTH0_DOMAIN: str
    AUTH0_CLIENT_ID: str
    AUTH0_CLIENT_SECRET: str
    AUTH0_AUDIENCE: str

    @property
    def AUTH0_ISSUER(self) -> str:
        return f"https://{self.AUTH0_DOMAIN}/"

    @property
    def AUTH0_JWKS_URL(self) -> str:
        return f"https://{self.AUTH0_DOMAIN}/.well-known/jwks.json"

    # ── Database ───────────────────────────────
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ── Redis ──────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10

    # ── InfluxDB ───────────────────────────────
    INFLUXDB_URL: str = ""
    INFLUXDB_TOKEN: str = ""
    INFLUXDB_ORG: str = "quorum"
    INFLUXDB_BUCKET: str = "meeting_metrics"

    # ── AI ─────────────────────────────────────
    ANTHROPIC_API_KEY: str
    OPENAI_API_KEY: str
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX: str = "quorum-decisions"
    DEEPGRAM_API_KEY: str = ""

    # ── Anonymization (NEVER change in production without RB-08) ──
    SPEAKER_HASH_SECRET: str
    RESPONDENT_HASH_SECRET: str

    # ── Integrations ───────────────────────────
    ZOOM_CLIENT_ID: str = ""
    ZOOM_CLIENT_SECRET: str = ""
    ZOOM_WEBHOOK_SECRET: str = ""
    TEAMS_APP_ID: str = ""
    TEAMS_APP_PASSWORD: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # ── Email ──────────────────────────────────
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "hello@quorum.ai"
    SENDGRID_FROM_NAME: str = "Quorum"

    # ── Billing ────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # ── AWS ────────────────────────────────────
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET: str = ""

    # ── Observability ──────────────────────────
    SENTRY_DSN: str = ""
    DATADOG_API_KEY: str = ""

    # ── Feature flags ──────────────────────────
    FEATURE_LIVE_MEETING: bool = True
    FEATURE_RECORDING: bool = False
    FEATURE_PATTERN_DETECTOR: bool = True
    FEATURE_SLACK_INTEGRATION: bool = True

    # ── Celery ─────────────────────────────────
    CELERY_TASK_ALWAYS_EAGER: bool = False

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()


# ═══════════════════════════════════════════════════════════════
# app/core/database.py — Async SQLAlchemy setup + RLS helper
# ═══════════════════════════════════════════════════════════════
from __future__ import annotations
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text, event


engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,           # reconnect on stale connections
    pool_recycle=3600,            # recycle connections every hour
    echo=settings.is_development, # log SQL in dev only
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: yields an async DB session.
    Usage: db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def set_rls_org_id(db: AsyncSession, org_id: str) -> None:
    """
    Set the PostgreSQL session variable for Row Level Security.
    Must be called in every route handler that accesses org-scoped data.

    Usage:
        async def my_route(db: AsyncSession = Depends(get_db), ...):
            await set_rls_org_id(db, current_user.org_id)
            # Now all queries are scoped to this org via RLS
    """
    await db.execute(
        text("SET LOCAL app.current_org_id = :org_id"),
        {"org_id": str(org_id)}
    )


# ═══════════════════════════════════════════════════════════════
# app/core/security.py — JWT validation + anonymization
# ═══════════════════════════════════════════════════════════════
from __future__ import annotations
import hashlib
import hmac
import time
from typing import Any
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=True)

# Cache JWKS (refresh every hour)
_jwks_cache: dict = {}
_jwks_cached_at: float = 0.0
_JWKS_TTL = 3600  # 1 hour


async def _get_jwks() -> dict:
    """Fetch and cache Auth0 JWKS (public keys for JWT verification)."""
    global _jwks_cache, _jwks_cached_at
    if time.time() - _jwks_cached_at < _JWKS_TTL and _jwks_cache:
        return _jwks_cache
    async with httpx.AsyncClient() as client:
        resp = await client.get(settings.AUTH0_JWKS_URL, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_cached_at = time.time()
    return _jwks_cache


async def verify_jwt(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> dict[str, Any]:
    """
    Verify Auth0 JWT. Returns decoded payload if valid.
    Raises 401 on any validation failure.
    """
    token = credentials.credentials
    try:
        jwks = await _get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header.get("kid"):
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n":   key["n"],
                    "e":   key["e"],
                }
                break

        if not rsa_key:
            raise HTTPException(status_code=401, detail="Invalid token key")

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.AUTH0_AUDIENCE,
            issuer=settings.AUTH0_ISSUER,
        )
        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


class CurrentUser:
    """
    Dependency: validates JWT and returns current user context.
    Usage: user: CurrentUser = Depends(get_current_user)
    """
    def __init__(self, user_id: UUID, org_id: UUID, email: str, role: str):
        self.user_id = user_id
        self.org_id = org_id
        self.email = email
        self.role = role

    @property
    def is_admin(self) -> bool:
        return self.role in ("admin", "owner")

    @property
    def is_facilitator(self) -> bool:
        return self.role in ("facilitator", "admin", "owner")


async def get_current_user(
    payload: dict = Depends(verify_jwt),
    db: "AsyncSession" = Depends(get_db),
) -> CurrentUser:
    """
    Resolve JWT payload to a CurrentUser.
    Fetches user record from DB to get org_id and role.
    """
    from app.services.user_service import get_user_by_auth0_id

    auth0_id = payload.get("sub")
    if not auth0_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing sub")

    user = await get_user_by_auth0_id(db, auth0_id)
    if not user or user.deleted_at:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    await set_rls_org_id(db, user.org_id)

    return CurrentUser(
        user_id=user.id,
        org_id=user.org_id,
        email=user.email,
        role=user.role,
    )


def require_role(*roles: str):
    """
    Dependency factory: require user to have one of the specified roles.
    Usage: user = Depends(require_role("admin", "facilitator"))
    """
    async def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' not authorized. Required: {roles}",
            )
        return user
    return _check


# ── Anonymization ──────────────────────────────────────────────
def anonymize_respondent(user_id: str, meeting_id: str) -> str:
    """
    One-way HMAC-SHA256 for survey respondents.
    Properties:
    - Deterministic: same user+meeting → same hash
    - Irreversible: cannot recover user_id from hash
    - Meeting-scoped: same user gets different hash in different meetings
    - Secret-protected: requires RESPONDENT_HASH_SECRET to compute

    See adversarial tests in tests/unit/test_anonymization.py
    """
    secret = settings.RESPONDENT_HASH_SECRET.encode()
    message = f"{user_id}:{meeting_id}".encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()[:20]


def anonymize_speaker(speaker_platform_id: str, meeting_id: str) -> str:
    """
    One-way HMAC-SHA256 for live meeting speakers.
    Meeting-scoped: same person gets different hash in different meetings.
    """
    secret = settings.SPEAKER_HASH_SECRET.encode()
    message = f"{speaker_platform_id}:{meeting_id}".encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()[:16]


def verify_survey_token(token: str, db_token: str | None) -> bool:
    """Constant-time comparison to prevent timing attacks on survey tokens."""
    if not db_token:
        return False
    return hmac.compare_digest(token.encode(), db_token.encode())


# ═══════════════════════════════════════════════════════════════
# app/core/exceptions.py — Custom exception hierarchy
# ═══════════════════════════════════════════════════════════════
from __future__ import annotations


class QuorumError(Exception):
    """Base exception for all Quorum-specific errors."""
    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, code: str | None = None):
        self.message = message
        if code:
            self.code = code
        super().__init__(message)


class NotFoundError(QuorumError):
    status_code = 404
    code = "not_found"


class ForbiddenError(QuorumError):
    status_code = 403
    code = "forbidden"


class ValidationError(QuorumError):
    status_code = 422
    code = "validation_error"


class RateLimitError(QuorumError):
    status_code = 429
    code = "rate_limit_exceeded"


class InsufficientDataError(QuorumError):
    """Raised when there's not enough data to generate intelligence."""
    status_code = 422
    code = "insufficient_data"


class IntegrationError(QuorumError):
    """Raised when an external integration (Zoom, Deepgram) fails."""
    status_code = 502
    code = "integration_error"


# ═══════════════════════════════════════════════════════════════
# app/core/logging.py — Structured logging with structlog
# ═══════════════════════════════════════════════════════════════
from __future__ import annotations
import logging
import sys
import structlog


def configure_logging() -> None:
    """Configure structlog for structured JSON logging in production."""
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.is_production:
        # JSON output for log aggregation (Datadog, CloudWatch)
        renderer = structlog.processors.JSONRenderer()
    else:
        # Pretty console output for development
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.LOG_LEVEL)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging to go through structlog
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=renderer,
            foreign_pre_chain=shared_processors,
        )
    )
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(settings.LOG_LEVEL)

    # Silence noisy libraries in production
    if settings.is_production:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

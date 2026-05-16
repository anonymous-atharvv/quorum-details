# ─────────────────────────────────────────────
# QUORUM API — Production Dockerfile
# Multi-stage build: development → builder → production
#
# Build:   docker build --target production -t quorum-api .
# Dev:     docker build --target development -t quorum-api-dev .
# ─────────────────────────────────────────────

# ── Stage 1: Base ─────────────────────────────
FROM python:3.12-slim AS base

# System deps — minimal, specific versions
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl=7.88.1-10+deb12u6 \
    libpq-dev=15.6-0+deb12u1 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN groupadd --gid 1001 quorum && \
    useradd --uid 1001 --gid quorum --shell /bin/bash --create-home quorum

WORKDIR /app

# Environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1


# ── Stage 2: Builder ──────────────────────────
FROM base AS builder

# Install Poetry
RUN pip install poetry==1.8.3

# Copy dependency files only (cache layer)
COPY pyproject.toml poetry.lock ./

# Install dependencies (no dev deps, no virtualenv)
RUN poetry config virtualenvs.create false && \
    poetry install --only=main --no-root --no-interaction

# Copy application source
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./


# ── Stage 3: Development ──────────────────────
FROM builder AS development

# Install dev dependencies (testing, debugging)
RUN poetry install --no-root --no-interaction

# Install development tools
RUN pip install watchdog[watchmedo]==4.0.1

# Keep as root in dev (for volume mount permissions)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


# ── Stage 4: Production ───────────────────────
FROM base AS production

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy app (owned by non-root user)
COPY --from=builder --chown=quorum:quorum /app /app

# Switch to non-root user
USER quorum

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production server: uvicorn with gunicorn process manager
# Workers = 2 × CPU cores + 1 (standard formula)
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--access-log", \
     "--log-level", "info", \
     "--timeout-keep-alive", "30"]

EXPOSE 8000

# Labels for container registry
LABEL org.opencontainers.image.title="Quorum API" \
      org.opencontainers.image.description="Collective Intelligence Platform API" \
      org.opencontainers.image.vendor="Quorum" \
      org.opencontainers.image.version="1.0.0"

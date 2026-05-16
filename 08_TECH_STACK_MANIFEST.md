# QUORUM — Tech Stack Manifest
## Every dependency, exact version, rationale, and alternative considered

---

## Philosophy
Every tool in this stack was chosen by answering three questions:
1. Is it the best tool for this specific job?
2. Will it survive to Series B without a painful migration?
3. Does it compound — does using it make adjacent decisions easier?

No "trendy" tools. No over-engineering. Every choice is defensible.

---

## Backend

### Python 3.12
**Why:** Type system improvements (PEP 695), performance gains (+10% over 3.11),
async improvements. Python is the clear winner for AI/ML adjacent stacks — 
libraries, hiring, ecosystem.
**Alternatives considered:** Node.js (worse AI library support), Go (faster but 
hiring harder, worse LLM integration)

### FastAPI 0.111.0
**Why:** Best async Python API framework. Automatic OpenAPI generation. 
Pydantic v2 native. WebSocket support built-in. Best performance among 
Python frameworks.
**Alternatives considered:** Django REST (heavier, synchronous by default), 
Flask (too minimal, manual everything)

### Pydantic 2.7.0
**Why:** v2 is 5-17x faster than v1. Core to Instructor library for LLM output 
validation. First-class FastAPI integration. Runtime type safety.
**Note:** Pin to 2.7.x — Instructor has compatibility constraints.

### SQLAlchemy 2.0.30 (async)
**Why:** Async support with asyncpg driver. Best ORM ecosystem in Python. 
Type-safe queries with 2.0 style. Works perfectly with FastAPI's async model.
**Alternatives considered:** Tortoise ORM (smaller ecosystem), raw asyncpg (no ORM 
abstractions, too much boilerplate)

### Alembic 1.13.1
**Why:** De facto standard for SQLAlchemy migrations. Autogenerate from models. 
Rollback support. Required for production DB management.

### Celery 5.4.0
**Why:** Battle-tested distributed task queue. Redis broker support. Beat scheduler 
built-in. Rich monitoring via Flower. Large community.
**Alternatives considered:** ARQ (lighter but less mature), RQ (simpler but fewer 
features), Dramatiq (good but smaller community)

### Redis 7.2 (via redis-py 5.0.4)
**Why:** Celery broker + result backend. Session/rate limit cache. Real-time meeting 
state. WebSocket connection registry. Sorted sets for leaderboards. One tool, 
multiple jobs.
**Client:** `redis[hiredis]` — C parser, 5-10x faster than pure Python

### APScheduler 4.0.0a4
**Why:** In-process scheduler for fixed schedules (pattern detector weekly, 
outcome check-ins daily). Integrates cleanly with Celery Beat.
**Note:** 4.0 is alpha but stable enough for these use cases. Pin tightly.

### asyncpg 0.29.0
**Why:** Fastest PostgreSQL driver for Python (pure C, async). Required by 
SQLAlchemy async. 3x faster than psycopg2.

### httpx 0.27.0
**Why:** Async HTTP client. Used for Zoom/Teams webhook calls, Deepgram HTTP 
(non-streaming), internal service calls. Replaces requests in async context.

---

## AI & ML

### anthropic 0.28.0
**Why:** Claude claude-sonnet-4-20250514 is the primary reasoning model. 
Best-in-class for structured reasoning, nuanced analysis, and following 
complex instructions. Streaming support. Excellent Instructor compatibility.
**Model:** `claude-sonnet-4-20250514` for all reasoning tasks
**Fallback:** `claude-haiku-4-5-20251001` for low-stakes, high-volume tasks 
(survey question validation, quick summaries)

### instructor 1.4.3
**Why:** Forces LLM outputs into Pydantic schemas with automatic retry on 
validation failure. Eliminates all JSON parsing fragility. 
**Critical:** All five AI agents use Instructor. Never call Claude directly 
without it — raw JSON parsing is a production disaster.

### openai 1.35.0
**Why:** text-embedding-3-large (1536 dimensions) for decision embeddings. 
Best embedding quality for semantic search. Only used for embeddings — 
not for reasoning (Claude handles that).
**Cost:** ~$0.13 per million tokens. Negligible for decision library size.

### deepgram 3.5.0
**Why:** Best accuracy + lowest latency for real-time streaming STT. 
Nova-2 model: 300-400ms latency, best accuracy on meeting audio (multiple 
speakers, accents, technical vocabulary). Built-in speaker diarization.
**Alternatives considered:** Whisper (no streaming, too slow for real-time), 
AssemblyAI (good but Deepgram better for meetings), Rev.ai (enterprise 
pricing, overkill at seed stage)
**Pricing:** $0.0059/min for Nova-2 streaming. 60-min meeting = $0.354.

### pinecone-client 4.1.0
**Why:** Managed vector database. No infrastructure to run. Serverless tier 
free up to 2M vectors. Handles similarity search for decision library 
("find decisions similar to this one").
**Index config:** dimension=1536, metric=cosine, serverless on AWS us-east-1
**Alternatives considered:** pgvector (PostgreSQL extension) — viable but 
requires PostgreSQL 16+ and more setup. Migrate to pgvector at Series B 
to reduce vendor dependency.

### langgraph 0.2.0
**Why:** Correct abstraction for multi-agent workflows with cycles and 
conditional edges. The pattern detector's multi-step pipeline (pre-compute → 
LLM → validate → retry) fits naturally.
**Note:** Not used for simple single-agent calls (Survey Designer, Tension 
Analyst) — those use Instructor directly. LangGraph only where multi-step 
orchestration is genuinely needed.

### influxdb-client 1.44.0
**Why:** Time-series database for speaking time metrics, alert frequency, 
participation rates. Native Python async client. InfluxDB Cloud free tier 
is generous.
**Alternatives considered:** TimescaleDB (PostgreSQL extension) — viable but 
adds complexity. InfluxDB is purpose-built and the client is excellent.

---

## Frontend

### Next.js 14.2.4 (App Router)
**Why:** App Router is the correct paradigm for this product — server components 
for dashboard data, client components for real-time WebSocket UI. 
React Server Components reduce bundle size significantly.
**Note:** Not 15.x — too new, breaking changes still settling.

### TypeScript 5.5.0
**Why:** Non-negotiable for a product this complex. Catches integration bugs 
between API and frontend at compile time. Required for team scaling.

### Tailwind CSS 3.4.4
**Why:** Best utility-first CSS framework. No stylesheet bloat. Excellent with 
shadcn/ui. JIT compilation keeps bundles small.

### shadcn/ui (latest)
**Why:** Not a component library — it's a component registry. You own the code. 
No upgrade breaking changes. Tailwind-native. Radix UI primitives under the hood 
(accessible by default). This is the right call for a startup — fast to build, 
easy to customize.
**Components used:** Button, Card, Dialog, Drawer, Input, Label, Select, 
Separator, Sheet, Skeleton, Tabs, Toast, Tooltip, Progress

### Zustand 4.5.2
**Why:** Minimal, fast React state management. No boilerplate. Devtools support. 
Works perfectly alongside React Query (server state vs. client state separation).
**Pattern:** Zustand for client state (WebSocket connection, live meeting state, 
UI state). TanStack Query for server state (API data, caching, refetching).

### TanStack Query 5.50.0 (@tanstack/react-query)
**Why:** Best server state management for React. Automatic caching, background 
refetching, optimistic updates, stale-while-revalidate. Replaces Redux for 
API data.

### Recharts 2.12.7
**Why:** React-native charts built on D3. Best documentation. Group Intelligence 
Profile dashboard needs: radar charts (domain accuracy), line charts (accuracy 
over time), bar charts (speaking distribution).

### Zod 3.23.8
**Why:** Runtime schema validation for all API responses on the frontend. 
Matches Pydantic schemas on the backend. Catches API contract violations 
at runtime with helpful error messages.

### React Hook Form 7.52.1
**Why:** Best form library for React. Zero re-renders on keystroke. Zod 
integration via @hookform/resolvers. Survey form, post-mortem form, 
decision capture — all forms benefit.

---

## Mobile (Phase 2 — Zoom/Teams sidebar runs in mobile context)

### Expo SDK 51 / React Native 0.74
**Why:** If native mobile app is added (Phase 3+), Expo is the fastest path. 
The Zoom App SDK sidebar already runs in a web context so native mobile 
is a later consideration.

---

## Infrastructure

### Docker 25+ / Docker Compose 2.27+
**Why:** Reproducible local dev environment. Exact parity with production. 
Every engineer runs the same stack from day one.

### AWS (primary cloud)
**Why:** Most enterprise customers require AWS for data residency. Largest 
ecosystem of managed services. Best Fargate + RDS + ElastiCache integration.
**Services:**
- ECS Fargate: API + worker containers (no EC2 to manage)
- RDS PostgreSQL 16 Multi-AZ: primary database
- ElastiCache Redis 7: cache + Celery broker
- S3: audio recordings (optional), static assets
- CloudFront: CDN for Next.js static
- ALB: load balancing + SSL termination
- Route53: DNS
- ACM: SSL certificates (free)
- Secrets Manager: all secrets (not SSM — Secrets Manager has auto-rotation)
- CloudWatch: logs + alarms
- ECR: container registry

### Terraform 1.9.0
**Why:** Infrastructure as Code. Reproducible across staging + production. 
State in S3 with DynamoDB locking.
**Alternative considered:** Pulumi (TypeScript-native but smaller community), 
AWS CDK (good but more verbose)

### GitHub Actions
**Why:** Native to GitHub. Free for public repos, cheap for private. 
Best ecosystem of actions. No additional tool to manage.

---

## Observability

### Datadog (APM + Infrastructure + Logs)
**Why:** Unified observability — traces, metrics, logs in one place. 
Agent-based, works with ECS Fargate. Best dashboards for business metrics.
**Cost:** ~$35/host/month. At 5 hosts: $175/month. 
Acceptable at seed stage. Move to self-hosted Grafana+Prometheus at Series B.
**Key integrations:** PostgreSQL metrics, Redis metrics, Celery task metrics, 
custom business metrics (decisions tracked, alerts actioned)

### Sentry 8.x (sentry-sdk)
**Why:** Error tracking with full stack traces and context. 
Session replay for frontend bugs. Performance monitoring.
**Separate from Datadog:** Sentry catches application errors; 
Datadog monitors infrastructure and business metrics.
**Cost:** Free tier covers seed stage (<5K errors/month).

### Flower 2.0.1
**Why:** Celery task monitoring UI. See task queue depth, failures, 
execution times. Deploy alongside workers, internal network only.

---

## Security

### Auth0 (via python-jose 3.3.0 + authlib 1.3.1)
**Why:** Managed identity. SAML/SSO for enterprise without building it. 
MFA support. SOC 2 Type II certified. OAuth 2.0 + PKCE for web.
**Alternative considered:** Clerk (better DX but less enterprise-ready), 
Cognito (AWS-native but poor DX)

### passlib 1.7.4 + bcrypt 4.1.3
**Why:** Password hashing for API keys. bcrypt is the industry standard.
**Note:** bcrypt only used for API key hashing — user passwords handled by Auth0.

### cryptography 42.0.8
**Why:** Field-level encryption for audio recording paths. 
AES-256-GCM implementation. Also used for HMAC anonymization functions.

---

## Testing

### pytest 8.2.2
**Why:** The Python testing standard. Rich plugin ecosystem.
**Key plugins:**
- pytest-asyncio 0.23.7: async test support
- pytest-mock 3.14.0: mocking
- pytest-cov 5.0.0: coverage reporting (target: 80% on services/)
- pytest-xdist 3.5.0: parallel test execution

### factory-boy 3.3.0
**Why:** Test fixtures. Build complex object graphs (Org → User → Meeting → 
SurveyResponse) without verbose setUp code.

### httpx (test client)
**Why:** FastAPI's TestClient is built on httpx. Async test support.

### Playwright 1.45.0
**Why:** End-to-end browser testing. Tests the full survey submission flow, 
live meeting sidebar, facilitator brief view. Better than Cypress for async.

---

## Linting & Formatting

### ruff 0.5.0
**Why:** Replaces flake8 + isort + black. 100x faster. One tool for all 
Python code quality. Non-negotiable — enforced in CI.

### mypy 1.10.0
**Why:** Static type checking. Catches bugs before runtime. Required for 
a codebase this complex.
**Config:** `--strict` mode. No `# type: ignore` without justification.

### pre-commit 3.7.1
**Why:** Runs ruff + mypy on every commit. Prevents bad code from entering 
the repo. Setup once, enforced forever.

---

## Email & Communications

### SendGrid (via sendgrid 6.11.0)
**Why:** Transactional email. Survey invitations, outcome reminders, 
facilitator briefs. Best deliverability. Template engine.
**Alternatives considered:** Postmark (better for transactional, slightly 
more expensive), Resend (newer, good DX but less battle-tested)

### Slack SDK (slack-sdk 3.29.0)
**Why:** Intervention notifications to Slack. Many teams prefer Slack 
notifications over email for real-time alerts.
**Integration:** Org-level Slack webhook, not per-user.

---

## Billing

### Stripe (stripe 10.6.0)
**Why:** Standard. Best API. Webhooks for seat management. 
Handles VAT for EU customers automatically.
**Products configured:**
- Starter plan: $49/seat/month
- Growth plan: $99/seat/month
- Enterprise plan: custom (manual Stripe dashboard)
**Metered billing:** Seat-based. Webhook updates seat count on user invite/remove.

---

## Complete pyproject.toml

```toml
[tool.poetry]
name = "quorum-api"
version = "1.0.0"
description = "Quorum Collective Intelligence Platform — API"
python = "^3.12"

[tool.poetry.dependencies]
# API framework
fastapi = "0.111.0"
uvicorn = {extras = ["standard"], version = "0.30.1"}
pydantic = {extras = ["email"], version = "2.7.4"}
pydantic-settings = "2.3.4"

# Database
sqlalchemy = {extras = ["asyncio"], version = "2.0.30"}
asyncpg = "0.29.0"
alembic = "1.13.1"
redis = {extras = ["hiredis"], version = "5.0.7"}

# Task queue
celery = {extras = ["redis"], version = "5.4.0"}
apscheduler = "4.0.0a4"
flower = "2.0.1"

# HTTP
httpx = "0.27.0"

# AI
anthropic = "0.28.0"
openai = "1.35.0"
instructor = "1.4.3"
langgraph = "0.2.0"
langchain-core = "0.2.23"     # langgraph dependency

# Vector & time-series
pinecone-client = "4.1.0"
influxdb-client = {extras = ["async"], version = "1.44.0"}

# Speech
deepgram-sdk = "3.5.0"

# Auth & security
python-jose = {extras = ["cryptography"], version = "3.3.0"}
authlib = "1.3.1"
passlib = {extras = ["bcrypt"], version = "1.7.4"}
cryptography = "42.0.8"

# Email & comms
sendgrid = "6.11.0"
slack-sdk = "3.29.0"

# Billing
stripe = "10.6.0"

# Utilities
python-multipart = "0.0.9"    # file uploads
python-dotenv = "1.0.1"
orjson = "3.10.6"             # faster JSON serialization
structlog = "24.4.0"          # structured logging
tenacity = "8.5.0"            # retry logic
sentry-sdk = {extras = ["fastapi"], version = "2.10.0"}

[tool.poetry.group.dev.dependencies]
pytest = "8.2.2"
pytest-asyncio = "0.23.7"
pytest-mock = "3.14.0"
pytest-cov = "5.0.0"
pytest-xdist = "3.5.0"
factory-boy = "3.3.0"
ruff = "0.5.0"
mypy = "1.10.0"
pre-commit = "3.7.1"
ipython = "*"

[tool.ruff]
line-length = 88
target-version = "py312"
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "PT", "SIM", "RUF"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy", "sqlalchemy.ext.mypy.plugin"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "--cov=app --cov-report=term-missing --cov-fail-under=80"
```

---

## Frontend package.json

```json
{
  "name": "quorum-web",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint && tsc --noEmit",
    "test": "playwright test",
    "test:unit": "vitest"
  },
  "dependencies": {
    "next": "14.2.4",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "typescript": "5.5.3",

    "@tanstack/react-query": "5.50.0",
    "@tanstack/react-query-devtools": "5.50.0",
    "zustand": "4.5.2",

    "tailwindcss": "3.4.4",
    "postcss": "8.4.39",
    "autoprefixer": "10.4.19",

    "recharts": "2.12.7",
    "lucide-react": "0.408.0",
    "class-variance-authority": "0.7.0",
    "clsx": "2.1.1",
    "tailwind-merge": "2.4.0",

    "react-hook-form": "7.52.1",
    "@hookform/resolvers": "3.9.0",
    "zod": "3.23.8",

    "@auth0/nextjs-auth0": "3.5.0",

    "date-fns": "3.6.0",
    "socket.io-client": "4.7.5",
    "sonner": "1.5.0",
    "@radix-ui/react-dialog": "1.1.1",
    "@radix-ui/react-dropdown-menu": "2.1.1",
    "@radix-ui/react-tabs": "1.1.0",
    "@radix-ui/react-tooltip": "1.1.2",
    "@radix-ui/react-progress": "1.1.0",
    "@radix-ui/react-select": "2.1.1",
    "@radix-ui/react-separator": "1.1.0",
    "@radix-ui/react-avatar": "1.1.0",
    "@radix-ui/react-switch": "1.1.0",

    "@sentry/nextjs": "8.18.0"
  },
  "devDependencies": {
    "@playwright/test": "1.45.0",
    "vitest": "2.0.3",
    "@vitejs/plugin-react": "4.3.1",
    "@testing-library/react": "16.0.0",
    "@types/node": "20.14.10",
    "@types/react": "18.3.3",
    "@types/react-dom": "18.3.0",
    "eslint": "8.57.0",
    "eslint-config-next": "14.2.4"
  }
}
```

---

## Version Pinning Policy

All dependencies are pinned to exact versions (`==` in pip, no `^` in npm for critical packages).

**Why:** A startup cannot afford a breaking dependency update taking down production at 2am.

**Upgrade schedule:**
- Security patches: within 48 hours of CVE publication
- Minor versions: monthly, in a dedicated PR with full test suite
- Major versions: quarterly, with dedicated spike ticket

**Automated:** Dependabot configured for security alerts only (not auto-PRs for all updates).

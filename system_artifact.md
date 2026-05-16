# QUORUM — MASTER SYSTEM PROMPT
## God-Tier Production Build Specification v2.0

> **HOW TO USE**: Feed this entire document as the system context to any frontier AI coding agent (Claude Code, Cursor, GPT-4o). Every architectural decision, AI behavior, data model, API, and build constraint is defined here. Build in the exact sequence in Section 10. Do not deviate. Do not simplify.

---

## SECTION 1: IDENTITY & MISSION

### Product
**QUORUM** — Collective Intelligence Platform

### One-Line Definition
Quorum is a B2B AI platform that makes organizational group decisions measurably better by combining pre-meeting anonymous elicitation, real-time meeting intelligence, and longitudinal outcome tracking with compounding intelligence.

### The Core Problem
Organizations lose $37B annually in the US to decisions made poorly in meetings. The root cause is not intelligence — it is **social dynamics**:
- **HiPPO Effect**: Highest-paid person's opinion dominates and suppresses others
- **Groupthink**: Social pressure kills honest dissent before it's voiced
- **Information Pooling Failure**: People in the room have the answer but never say it
- **Anchoring Bias**: First speaker frames the entire conversation

Every existing meeting tool (Otter.ai, Fireflies, Slido) solves **efficiency**. Quorum is the first product designed to solve **decision quality** — a fundamentally different and more valuable problem.

### What Quorum Is NOT
- Not a transcription tool
- Not a task manager
- Not a performance evaluation tool — **NEVER used to assess individuals**
- Not surveillance — all individual input is architecturally anonymized

---

## SECTION 2: THREE-PHASE PRODUCT BEHAVIOR

### Phase 1 — Before the Meeting (24–48 hours prior)
1. Facilitator creates a meeting in Quorum and connects it to their calendar
2. AI generates 4–6 targeted anonymous survey questions from the meeting agenda
3. Survey links sent to all participants — **no Quorum account required to respond**
4. Responses collected with one-way HMAC anonymization at point of collection
5. AI Tension Analyst synthesizes responses into a Tension Map (requires ≥50% response rate)
6. Facilitator receives a private brief with tension map, recommended questions, and meeting strategy
7. Participants never see the facilitator brief — ever

### Phase 2 — During the Meeting (real-time)
1. Facilitator starts a Quorum live session (bot joins Zoom/Teams/Meet)
2. Deepgram Nova-2 streams real-time transcription with speaker diarization
3. Speakers are immediately anonymized via meeting-scoped HMAC hash
4. Every 30 seconds, the Live Intelligence Agent evaluates:
   - **HiPPO Check** (rule-based, ~1ms): speaking time exceeds 40% threshold?
   - **Groupthink Precheck** (rule-based): consensus signals while tension map shows disagreement?
   - **Missing Perspective** (semantic): tension map topic not surfaced after 55% of time elapsed?
   - **LLM Evaluation** (Claude, <3s): full nuanced assessment if precheck fires
5. Alerts appear only in the facilitator's private sidebar — never broadcast to participants
6. Maximum 2 HiPPO alerts + 3 missing-perspective alerts per meeting (anti-fatigue cap)
7. Facilitator can mark decisions in real-time via sidebar

### Phase 3 — After the Meeting (days, months, years)
1. Post-mortem auto-generated within 24 hours (facilitator edits then publishes)
2. Decisions captured with: title, description, options considered, key assumptions, team confidence score, dissenting views (anonymous, from survey data)
3. Outcome check-in emails sent automatically at 30d, 90d, 180d
4. Outcome verdicts feed into Group Intelligence Profile (GIP)
5. Pattern Detector runs weekly (LangGraph multi-agent, Sunday 03:00 UTC)
6. GIP surfaces domain accuracy, overconfidence patterns, meeting health metrics
7. Pre-meeting intelligence on next meeting uses GIP patterns to warn: "Your team has the Senior Leader Anchor pattern — start with anonymous input"

---

## SECTION 3: SYSTEM ARCHITECTURE

```
┌────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                               │
│   Web App (Next.js 14)  │  Zoom Sidebar  │  Teams Bot  │  Meet Ext │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ HTTPS / WSS
┌──────────────────────────────▼─────────────────────────────────────┐
│              API GATEWAY (FastAPI 0.111.0 + Nginx)                 │
│         Auth0 JWT · RLS injection · Rate limiting · CORS           │
└────┬──────────┬──────────────┬──────────────┬──────────────┬───────┘
     │          │              │              │              │
  Survey    Meeting        AI Engine      Decision      GDPR/
  Engine    Stream         (5 agents)     Library       Billing
  Service   Ingester                      Service       Service
     │          │              │              │              │
┌────▼──────────▼──────────────▼──────────────▼──────────────▼───────┐
│                          DATA LAYER                                 │
│  PostgreSQL 16 (RLS)  ·  Redis 7  ·  Pinecone  ·  InfluxDB 2.7    │
│  S3 (recordings, opt-in)  ·  AWS Secrets Manager                   │
└────────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼─────────────────────────────────────┐
│                        WORKER LAYER                                 │
│      Celery 5 + Redis broker  ·  Celery Beat scheduler             │
│   survey-worker(×2)  ·  intelligence-worker(×4)  ·  scheduled      │
└────────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼─────────────────────────────────────┐
│                     INTEGRATION LAYER                               │
│  Zoom Apps SDK  ·  Teams Bot Framework  ·  Google Meet Extension   │
│  Deepgram Nova-2 (STT)  ·  Stripe  ·  SendGrid  ·  Slack SDK      │
└────────────────────────────────────────────────────────────────────┘
```

### Architecture Principles (Non-Negotiable)
1. **Privacy by default, not by configuration** — anonymization happens at collection; cannot be toggled off
2. **Fail silent in live meetings** — a Quorum outage must not disrupt the meeting; circuit breakers on all real-time components
3. **Phase 1 has no dependencies on Phase 2** — survey + tension map works standalone, deploy and charge for it first
4. **RLS before any production data enters the DB** — PostgreSQL Row Level Security is the last line of defense
5. **Never call Claude directly without Instructor** — raw JSON parsing is a production disaster

---

## SECTION 4: TECH STACK (EXACT VERSIONS, ALL PINNED)

### Backend (Python 3.12)
```toml
fastapi = "0.111.0"
uvicorn = { extras = ["standard"], version = "0.30.1" }
pydantic = { extras = ["email"], version = "2.7.4" }
pydantic-settings = "2.3.4"
python-multipart = "0.0.9"
sqlalchemy = { extras = ["asyncio"], version = "2.0.30" }
asyncpg = "0.29.0"
alembic = "1.13.1"
redis = { extras = ["hiredis"], version = "5.0.7" }
celery = { extras = ["redis"], version = "5.4.0" }
apscheduler = "4.0.0a4"
flower = "2.0.1"
httpx = "0.27.0"
anthropic = "0.28.0"           # Claude Sonnet 4 primary model
openai = "1.35.0"              # text-embedding-3-large only
instructor = "1.4.3"           # MANDATORY for all LLM calls
langgraph = "0.2.0"            # pattern detector only
langchain-core = "0.2.23"
pinecone-client = "4.1.0"
influxdb-client = { extras = ["async"], version = "1.44.0" }
deepgram-sdk = "3.5.0"
python-jose = { extras = ["cryptography"], version = "3.3.0" }
authlib = "1.3.1"
passlib = { extras = ["bcrypt"], version = "1.7.4" }
cryptography = "42.0.8"
sendgrid = "6.11.0"
slack-sdk = "3.29.0"
stripe = "10.6.0"
orjson = "3.10.6"
structlog = "24.4.0"
tenacity = "8.5.0"
sentry-sdk = { extras = ["fastapi"], version = "2.10.0" }
```

### AI Models (Pinned)
- **Primary reasoning**: `claude-sonnet-4-20250514` — all 5 AI agents
- **Fallback (low-stakes)**: `claude-haiku-4-5-20251001` — survey validation, quick summaries
- **Embeddings**: `text-embedding-3-large` (OpenAI, 1536 dimensions) — decision library semantic search
- **Speech-to-text**: Deepgram Nova-2 — 300-400ms latency, speaker diarization built-in

### Frontend (Next.js 14 App Router)
```json
{
  "next": "14.2.4",
  "react": "18.3.1",
  "typescript": "5.5.3",
  "@tanstack/react-query": "5.50.0",
  "zustand": "4.5.2",
  "tailwindcss": "3.4.4",
  "recharts": "2.12.7",
  "react-hook-form": "7.52.1",
  "zod": "3.23.8",
  "@auth0/nextjs-auth0": "3.5.0",
  "socket.io-client": "4.7.5"
}
```

### Infrastructure (AWS)
- **Compute**: ECS Fargate (API + workers, auto-scale on CPU + queue depth)
- **Database**: RDS PostgreSQL 16 Multi-AZ, r7g.xlarge (primary) + r7g.large (read replica)
- **Cache/Queue**: ElastiCache Redis 7, r7g.large
- **CDN**: CloudFront for Next.js static assets
- **Load Balancer**: ALB with WAF rules, SSL termination
- **Secrets**: AWS Secrets Manager (never .env in production)
- **Monitoring**: Datadog APM + Sentry error tracking

---

## SECTION 5: COMPLETE DATA MODELS

### 5.1 Organization & Users
```python
class Organization(Base):
    __tablename__ = "organizations"
    id: UUID (PK, gen_random_uuid())
    name: str (NOT NULL)
    domain: str (nullable)              # "acme.com" for SSO enforcement
    plan: Enum["starter","growth","enterprise"] (DEFAULT "starter")
    seat_count: int (DEFAULT 5)
    stripe_customer_id: str (UNIQUE, nullable)
    stripe_sub_id: str (UNIQUE, nullable)
    auth0_org_id: str (UNIQUE, nullable)
    settings: JSONB (DEFAULT '{}')
    # settings schema:
    # {
    #   "recording_consent_enabled": bool,
    #   "slack_webhook_url": str | null,
    #   "ai_context": str,              ← injected into ALL AI prompts for org context
    #   "outcome_check_in_day": int,    ← 0=Mon, 6=Sun
    #   "meeting_platforms": [str],
    #   "min_survey_response_rate": float  ← default 0.5
    # }
    created_at: TIMESTAMPTZ (DEFAULT NOW())
    updated_at: TIMESTAMPTZ (DEFAULT NOW(), auto-trigger)

class User(Base):
    __tablename__ = "users"
    id: UUID (PK)
    org_id: UUID (FK → organizations, CASCADE DELETE)
    auth0_id: str (UNIQUE, NOT NULL)
    email: str (NOT NULL)
    display_name: str (nullable)
    role: Enum["admin","facilitator","member"] (DEFAULT "member")
    last_active_at: TIMESTAMPTZ (nullable)
    created_at: TIMESTAMPTZ
    updated_at: TIMESTAMPTZ
    UNIQUE(org_id, email)
    # CRITICAL: No individual performance data EVER stored here
```

### 5.2 Meetings (Core Entity)
```python
class Meeting(Base):
    __tablename__ = "meetings"
    id: UUID (PK)
    org_id: UUID (FK, CASCADE DELETE)
    created_by: UUID (FK → users)       # the facilitator
    title: str (NOT NULL)
    description: str (nullable)
    scheduled_at: TIMESTAMPTZ (NOT NULL)
    duration_minutes: int (DEFAULT 60)
    platform: Enum["zoom","teams","meet","other"] (DEFAULT "other")
    platform_meeting_id: str (nullable)
    platform_join_url: str (nullable)
    status: Enum["draft","survey_open","survey_closed","live","ended",
                 "post_mortem_pending","post_mortem_done","cancelled"]

    # Calendar integration
    calendar_event_id: str (nullable)
    calendar_provider: str (nullable)   # "google" | "outlook"

    # Agenda
    agenda_items: JSONB (DEFAULT '[]')
    # [{title: str, description: str, duration_mins: int, type: str}]

    # Phase 1: Survey
    survey_sent_at: TIMESTAMPTZ (nullable)
    survey_deadline: TIMESTAMPTZ (nullable)
    survey_participant_count: int (DEFAULT 0)
    survey_response_count: int (DEFAULT 0, auto-trigger on insert/delete)
    generated_questions: JSONB (nullable)  # full GeneratedSurvey JSON

    # Phase 1: Tension Map
    tension_map: JSONB (nullable)          # full TensionMapOutput JSON
    tension_map_generated_at: TIMESTAMPTZ (nullable)
    facilitator_brief: TEXT (nullable)     # markdown, facilitator-only

    # Phase 2: Live session
    live_session_started_at: TIMESTAMPTZ (nullable)
    live_session_ended_at: TIMESTAMPTZ (nullable)

    # Metadata
    tags: TEXT[] (DEFAULT '{}')
    domain: str (nullable)               # "product"|"hiring"|"strategy"|etc.

    created_at: TIMESTAMPTZ
    updated_at: TIMESTAMPTZ

# INDEXES (performance-critical):
# CREATE INDEX idx_meetings_org_status ON meetings(org_id, status)
# CREATE INDEX idx_meetings_scheduled ON meetings(scheduled_at)
# CREATE INDEX idx_meetings_platform_id ON meetings(platform, platform_meeting_id)
# CREATE INDEX idx_meetings_title_trgm ON meetings USING gin(title gin_trgm_ops)
```

### 5.3 Survey System (CRITICAL — anonymization enforced here)
```python
class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"
    id: UUID (PK)
    meeting_id: UUID (FK, CASCADE DELETE)
    user_id: UUID (FK, CASCADE DELETE)
    role: Enum["facilitator","participant"] (DEFAULT "participant")
    invited_at: TIMESTAMPTZ (DEFAULT NOW())
    survey_sent_at: TIMESTAMPTZ (nullable)
    survey_token: str (UNIQUE, nullable)    # UUID token in survey email link
    survey_completed_at: TIMESTAMPTZ (nullable)
    joined_live_at: TIMESTAMPTZ (nullable)
    left_live_at: TIMESTAMPTZ (nullable)
    UNIQUE(meeting_id, user_id)

# CRITICAL INDEX: idx_participants_token ON meeting_participants(survey_token)

class SurveyResponse(Base):
    __tablename__ = "survey_responses"
    id: UUID (PK)
    meeting_id: UUID (FK, CASCADE DELETE)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CRITICAL ANONYMIZATION: respondent_hash is HMAC-SHA256
    # of (user_id + ":" + meeting_id) using RESPONDENT_HASH_SECRET
    # - Deterministic: same user+meeting → same hash
    # - Irreversible: cannot recover user_id from hash
    # - Meeting-scoped: different hash per meeting (no cross-meeting tracking)
    # - Secret-protected: requires server secret to compute
    # - The secret is in AWS Secrets Manager ONLY — never in DB
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    respondent_hash: str (NOT NULL)

    submitted_at: TIMESTAMPTZ (DEFAULT NOW())
    updated_at: TIMESTAMPTZ (DEFAULT NOW())
    responses: JSONB (NOT NULL)
    # [{
    #   question_id: str,
    #   question_text: str,
    #   answer: str | int | list[str],
    #   confidence: int | null    ← 1-10, how strongly they hold this view
    # }]
    UNIQUE(meeting_id, respondent_hash)  # one response per person per meeting

# NO index on respondent_hash — we NEVER query "responses by this person"
# Only query: "all responses for this meeting"
```

### 5.4 Live Session (Real-time intelligence)
```python
class LiveMeetingSession(Base):
    __tablename__ = "live_meeting_sessions"
    id: UUID (PK)
    meeting_id: UUID (FK, UNIQUE)           # one session per meeting
    started_at: TIMESTAMPTZ (DEFAULT NOW())
    ended_at: TIMESTAMPTZ (nullable)
    total_seconds: int (DEFAULT 0)

    # All speaker data uses hashes — NEVER names or user IDs
    speaking_distribution: JSONB (DEFAULT '{}')
    # {speaker_hash: seconds_speaking}

    hippo_events: JSONB (DEFAULT '[]')
    # [{timestamp_seconds, speaker_hash, pct_speaking, alert_id}]
    groupthink_events: JSONB (DEFAULT '[]')
    # [{timestamp_seconds, topic, tension_topic_matched, alert_id}]
    missing_perspective_events: JSONB (DEFAULT '[]')
    # [{timestamp_seconds, tension_area, alert_id}]

    total_alerts_delivered: int (DEFAULT 0)
    alerts_actioned: int (DEFAULT 0)

class LiveTranscriptChunk(Base):
    __tablename__ = "live_transcript_chunks"
    id: UUID (PK)
    session_id: UUID (FK, CASCADE DELETE)
    chunk_index: int (NOT NULL)
    start_seconds: int (NOT NULL)
    end_seconds: int (NOT NULL)
    speaker_hash: str (NOT NULL)            # anonymized, meeting-scoped ONLY
    text: str (NOT NULL)
    word_count: int (nullable)
    embedding_id: str (nullable)            # Pinecone vector ID
    created_at: TIMESTAMPTZ
    UNIQUE(session_id, chunk_index)

class IntelligenceAlert(Base):
    __tablename__ = "intelligence_alerts"
    id: UUID (PK)
    session_id: UUID (FK, CASCADE DELETE)
    alert_type: Enum["hippo","groupthink","missing_perspective",
                     "assumption_blindspot","momentum_trap"]
    urgency: Enum["low","medium","high"] (DEFAULT "medium")
    triggered_at_seconds: int (NOT NULL)
    message: str (NOT NULL)                 # max 2 sentences, facilitator-facing
    suggested_question: str (nullable)      # exact 1-sentence question to ask
    internal_reasoning: str (nullable)      # stored for model eval/debugging

    # Facilitator response tracking
    acknowledged_at: TIMESTAMPTZ (nullable)
    response: str (nullable)                # "handle_it"|"aware"|"dismissed"|null
    created_at: TIMESTAMPTZ
```

### 5.5 Decision Library & Outcome Tracking
```python
class Decision(Base):
    __tablename__ = "decisions"
    id: UUID (PK)
    org_id: UUID (FK, CASCADE DELETE)
    meeting_id: UUID (FK, SET NULL, nullable)   # can create outside meetings
    created_by: UUID (FK → users)

    title: str (NOT NULL)
    description: TEXT (NOT NULL)
    domain: str (NOT NULL, DEFAULT "other")     # product|hiring|strategy|financial|etc.
    decision_type: Enum["go_no_go","selection","prioritization",
                        "commitment","strategy","process","other"]

    # Context at decision time
    options_considered: JSONB (DEFAULT '[]')
    # [{option: str, rationale: str, pros: [str], cons: [str], was_chosen: bool}]
    key_assumptions: JSONB (DEFAULT '[]')
    # [{assumption: str, confidence: float, how_to_verify: str, check_in_question: str}]
    dissenting_views: JSONB (DEFAULT '[]')
    # [{view: str, source: "survey"|"meeting"|"manual"}] ← ALWAYS anonymous
    team_confidence: float (nullable)           # 0.0-1.0 stated at decision time

    # Post-mortem
    post_mortem_status: Enum["pending","in_progress","completed","skipped"]
    post_mortem_notes: TEXT (nullable)
    post_mortem_completed_at: TIMESTAMPTZ (nullable)

    # Outcome check-in schedule (SET BY DB TRIGGER on INSERT)
    check_in_30d_at: TIMESTAMPTZ (= created_at + 30 days)
    check_in_90d_at: TIMESTAMPTZ (= created_at + 90 days)
    check_in_180d_at: TIMESTAMPTZ (= created_at + 180 days)
    check_in_30d_sent: bool (DEFAULT false)
    check_in_90d_sent: bool (DEFAULT false)
    check_in_180d_sent: bool (DEFAULT false)

    embedding_id: str (nullable)                # Pinecone vector ID
    tags: TEXT[] (DEFAULT '{}')
    created_at: TIMESTAMPTZ
    updated_at: TIMESTAMPTZ

class DecisionOutcome(Base):
    __tablename__ = "decision_outcomes"
    id: UUID (PK)
    decision_id: UUID (FK, CASCADE DELETE)
    recorded_by: UUID (FK → users)
    check_in_period: Enum["30d","90d","180d","adhoc"]
    recorded_at: TIMESTAMPTZ

    outcome_verdict: Enum["correct","partially_correct","incorrect",
                          "too_early_to_tell","decision_no_longer_relevant"]
    outcome_description: TEXT (NOT NULL)
    what_we_got_right: TEXT (nullable)
    what_we_missed: TEXT (nullable)
    key_assumptions_that_failed: JSONB (DEFAULT '[]')
    # [assumption_text strings that were wrong]

    # Auto-computed by DB trigger:
    # correct=1.0, partially_correct=0.5, incorrect=0.0, others=null
    prediction_accuracy_score: float (nullable)
    lessons_learned: TEXT (nullable)
    created_at: TIMESTAMPTZ

class GroupIntelligenceProfile(Base):
    __tablename__ = "group_intelligence_profiles"
    id: UUID (PK)
    org_id: UUID (FK, UNIQUE)               # one per organization

    total_decisions_tracked: int (DEFAULT 0)
    decisions_with_outcomes: int (DEFAULT 0)
    overall_accuracy_score: float (nullable)  # null until >= 5 outcomes
    confidence_calibration_score: float (nullable)

    identified_patterns: JSONB (DEFAULT '[]')
    domain_accuracy: JSONB (DEFAULT '{}')
    # {domain: {decisions, outcomes, accuracy, trend}}

    avg_survey_response_rate: float (nullable)
    avg_speaking_time_gini: float (nullable)  # 0=equal, 1=one person only
    hippo_frequency_score: float (nullable)
    groupthink_frequency_score: float (nullable)

    recommended_practices: JSONB (DEFAULT '[]')
    last_pattern_run_at: TIMESTAMPTZ (nullable)
    last_updated: TIMESTAMPTZ
    created_at: TIMESTAMPTZ
```

### 5.6 Database Infrastructure
```sql
-- REQUIRED EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ROW LEVEL SECURITY (enable before any production data)
ALTER TABLE meetings ENABLE ROW LEVEL SECURITY;
ALTER TABLE survey_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE decisions ENABLE ROW LEVEL SECURITY;
-- (repeat for all core tables)

CREATE POLICY meetings_org_isolation ON meetings
    USING (org_id = current_setting('app.current_org_id', TRUE)::UUID);

-- AUDIT LOG (immutable — revoke UPDATE/DELETE from app user)
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    org_id UUID NOT NULL,
    user_id UUID (nullable),
    action TEXT NOT NULL,           -- "meeting.created", "survey.responded"
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
REVOKE UPDATE, DELETE ON audit_log FROM quorum_app;

-- DB TRIGGERS (auto-managed)
-- 1. set_updated_at() → all core tables
-- 2. update_survey_response_count() → on INSERT/DELETE survey_responses
-- 3. set_decision_checkin_dates() → on INSERT decisions
-- 4. set_prediction_accuracy() → on INSERT/UPDATE decision_outcomes
```

---

## SECTION 6: ANONYMIZATION SYSTEM (CRYPTOGRAPHIC GUARANTEE)

```python
import hashlib
import hmac
from app.core.config import settings

def anonymize_respondent(user_id: str, meeting_id: str) -> str:
    """
    One-way HMAC-SHA256 for survey respondents.
    
    Properties guaranteed:
    - Deterministic: same user+meeting → same hash (needed for duplicate-check)
    - Irreversible: cannot recover user_id from hash (cryptographic guarantee)
    - Meeting-scoped: same user gets DIFFERENT hash in different meetings
    - Secret-protected: requires RESPONDENT_HASH_SECRET to compute
    - Truncated to 20 chars for storage efficiency
    
    The RESPONDENT_HASH_SECRET is stored ONLY in AWS Secrets Manager.
    It is NEVER in the database. Even with full DB read access,
    an attacker cannot de-anonymize without the secret.
    
    Rotation: annually. Old responses remain anonymized post-rotation
    because the hash is stored, not recomputed on read.
    
    WARNING: Never rotate while meetings have status = 'survey_open'
    """
    secret = settings.RESPONDENT_HASH_SECRET.encode()
    message = f"{user_id}:{meeting_id}".encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()[:20]


def anonymize_speaker(speaker_platform_id: str, meeting_id: str) -> str:
    """
    One-way HMAC-SHA256 for live meeting speakers.
    Meeting-scoped: same person gets different hash in different meetings.
    Truncated to 16 chars for InfluxDB tag efficiency.
    """
    secret = settings.SPEAKER_HASH_SECRET.encode()
    message = f"{speaker_platform_id}:{meeting_id}".encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()[:16]


def verify_survey_token(token: str, db_token: str | None) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    if not db_token:
        return False
    return hmac.compare_digest(token.encode(), db_token.encode())
```

### Adversarial Test Coverage (Required — tests/unit/test_anonymization.py)
```python
# All of the following MUST pass in CI:
# ✓ same_user_same_meeting → same hash (determinism)
# ✓ same_user_different_meetings → different hashes (no cross-meeting tracking)
# ✓ different_users_same_meeting → different hashes (no confusion)
# ✓ hash_length_fixed regardless of input length (no length leakage)
# ✓ brute_force_with_known_user_list fails without secret
# ✓ hash_does_not_appear_in_logs (no accidental PII logging)
# ✓ two_hashes_from_different_meetings_share_no_detectable_pattern
```

---

## SECTION 7: THE AI ENGINE (5 AGENTS)

### CRITICAL RULE: All agents use Instructor library
```python
import instructor
from anthropic import Anthropic

client = instructor.from_anthropic(Anthropic())

# NEVER do this (raw JSON fragility):
response = anthropic.messages.create(...)
data = json.loads(response.content[0].text)

# ALWAYS do this (schema-validated, auto-retry):
result = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1000,
    response_model=SurveyDesignerOutput,
    messages=[{"role": "user", "content": prompt}]
)
```

---

### Agent 1: Survey Designer

**Trigger**: Meeting created / agenda updated
**Latency target**: <30s
**Model**: claude-sonnet-4-20250514 via Instructor

```python
class SurveyQuestion(BaseModel):
    id: str
    text: str
    type: Literal["scale_1_10", "multiple_choice", "open_text", "ranked_choice"]
    options: list[str] | None
    include_confidence_rating: bool     # True for all opinion questions
    rationale: str                      # internal only, not shown to users
    tension_hypothesis: str             # what conflict this surfaces

class SurveyDesignerOutput(BaseModel):
    questions: list[SurveyQuestion]     # 4-6 questions, enforced
    design_rationale: str
    watch_for: list[str]                # what facilitator should watch in meeting

SURVEY_DESIGNER_SYSTEM_PROMPT = """
You are Quorum's Survey Designer. Generate anonymous pre-meeting survey questions
that reveal what participants ACTUALLY think before social dynamics suppress honest views.

RULES:
1. Never write generic questions ("What do you think about X?").
   Write questions with a specific hypothesis ("Is X the right priority given Y?").
2. Every substantive opinion question MUST have a confidence rating
   (how strongly do you hold this view, 1-10).
3. Always include exactly one "what are you worried nobody will say?" question.
4. Always include one "what would need to be true for you to change your mind?" question.
5. Frame all questions neutrally — no leading language.
6. If the org has known tension patterns (provided below), ask HARDER questions
   about those areas. Don't let them repeat past mistakes.

QUESTION TYPE GUIDE:
- scale_1_10: intensity of opinion or confidence
- multiple_choice: discrete options (max 5)
- open_text: open concerns ("what worries you about this?")
- ranked_choice: priority ordering (max 5 items)

Meeting: {meeting_title}
Description: {meeting_description}
Agenda: {agenda_items}
Team context: {org_context}
Known tension patterns from past meetings: {past_tension_patterns}
"""

# QUALITY GATES (enforced in code, retry on failure, max 2 retries):
def validate_survey(output: SurveyDesignerOutput) -> list[str]:
    issues = []
    if len(output.questions) < 4:
        issues.append("Too few questions — minimum 4 required")
    if not any("worried" in q.text.lower() or "concern" in q.text.lower()
               for q in output.questions):
        issues.append("Missing open-ended concern question")
    if not any("change your mind" in q.text.lower() or "wrong" in q.text.lower()
               for q in output.questions):
        issues.append("Missing falsifiability question")
    opinion_qs = [q for q in output.questions
                  if q.type in ("scale_1_10", "multiple_choice")]
    if opinion_qs and not all(q.include_confidence_rating for q in opinion_qs):
        issues.append("Opinion questions missing confidence rating")
    return issues
```

---

### Agent 2: Tension Analyst

**Trigger**: Survey closes (or deadline reached with ≥30% response rate)
**Latency target**: <45s
**Model**: claude-sonnet-4-20250514 via Instructor

```python
class ConsensusArea(BaseModel):
    topic: str
    agreement_score: float          # 1.0 = unanimous
    summary: str
    confidence_average: float
    caveat: str | None

class TensionArea(BaseModel):
    topic: str
    tension_score: float            # 1.0 = severe disagreement
    summary: str
    perspective_a: str              # "some participants believe..."
    perspective_b: str              # "others hold that..."
    perspective_c: str | None
    why_this_matters: str
    recommended_question: str       # exact 1-sentence question for facilitator

class TensionMapOutput(BaseModel):
    consensus_areas: list[ConsensusArea]
    tension_areas: list[TensionArea]
    missing_from_conversation: list[str]  # what nobody mentioned but is critical
    facilitator_opening_question: str     # the single best question to start with
    watch_list: list[str]
    confidence: float               # 0.0-1.0
    confidence_caveat: str | None

TENSION_ANALYST_SYSTEM_PROMPT = """
You are Quorum's Tension Analyst. Produce a Tension Map giving the facilitator
an honest picture of what the group really thinks.

ANONYMIZATION RULES — NON-NEGOTIABLE:
1. Never quote any response verbatim, not even partially.
2. Never say "one respondent said" or imply identifiability.
   Use "some participants" or "a perspective that emerged."
3. Groups of fewer than 5 people: aggregate more aggressively —
   even paraphrasing a unique view can de-anonymize.
4. Do NOT soften real disagreements. If views clash sharply, say so.
   Facilitators need the truth, not false harmony.

TENSION DETECTION:
Surface tension even when surface answers agree but confidence scores diverge.
Example: everyone says "yes" to proceeding but avg confidence is 4/10 —
that IS a tension area. Consensus requires: >70% agreement AND >6/10 avg confidence.

MISSING FROM CONVERSATION:
What question was never asked that this group needs to discuss?
What buried assumption in the agenda has nobody questioned?
This section is often the most valuable output.

Response rate: {response_rate}
Meeting context: {meeting_context}
Questions asked: {question_set}
Anonymous responses: {responses}
Recent meeting history: {past_tension_maps}
"""

# RESPONSE RATE HANDLING (enforced in service layer):
async def generate_tension_map(meeting_id: str) -> tuple[TensionMapOutput | None, str]:
    rate = await get_response_rate(meeting_id)

    if rate < 0.30:
        return None, "insufficient_responses"  # hard refuse

    output = await run_tension_analyst(meeting_id)

    if rate < 0.50:
        output.confidence = min(output.confidence, 0.40)
        output.confidence_caveat = (
            f"Only {int(rate*100)}% of participants responded. "
            "This map may not represent the full group."
        )
        return output, "low_confidence"

    return output, "ok"
```

---

### Agent 3: Live Intelligence Agent (Most Complex)

**Architecture**: 3-tier detection with LLM as final arbiter

```
EVERY 30 SECONDS DURING MEETING:

Tier 1: HiPPO Check (rule-based, ~1ms)
├── speaking_pct > 45%? → urgency=HIGH alert
├── speaking_pct > 38%? → urgency=MEDIUM alert
└── cap: 2 HiPPO alerts max per meeting

Tier 2: Groupthink Precheck (rule-based, ~1ms)
├── elapsed < 8 min? → skip
├── tension_map has no tension areas? → skip
├── max tension_score < 0.35? → skip
├── count consensus signals in last 20 transcript chunks ≥ 3? → FIRE LLM
└── consensus signals: ["i agree", "totally", "let's go with", "sounds good",
                        "we're aligned", "move forward", "same page", "let's do it"]

Tier 3: Missing Perspective (semantic, ~200ms)
├── elapsed < 55% of meeting time? → skip
├── mp_alerts_delivered ≥ 3? → skip
├── embed last 40 chunks as vector
├── embed each tension area topic
├── cosine_similarity < 0.35? → topic NOT discussed yet → ALERT
└── cap: 3 missing-perspective alerts max per meeting

LLM EVALUATION (only if Tier 2 or 3 fires):
```

```python
LIVE_INTELLIGENCE_SYSTEM_PROMPT = """
You are Quorum's Live Intelligence Agent. A meeting is in progress.

Detect ONLY the following:
1. GROUPTHINK — group converging on a decision but pre-survey showed
   significant reservations. Consensus forming faster than decision complexity warrants.
2. ASSUMPTION BLINDSPOT — decision forming around an unstated assumption
   nobody has questioned (discussing HOW without questioning WHETHER).
3. MISSING CONTEXT — key concern from tension map not raised with time running short.

STRICT RULES:
- Intervene ONLY when >80% confident. False positives destroy trust permanently.
- When in doubt: return {"action": "monitor"}.
- Never alert the same type within 10 minutes.
- Never reference specific individuals.
- Keep suggested questions to ONE sentence — facilitators read at a glance.
- Alerts already delivered this meeting: {alerts_so_far}

Pre-meeting tension map: {tension_map}
Speaking distribution: {speaking_distribution}
Time elapsed / scheduled: {time_context}
Recent transcript (last 5 min): {transcript_context}

Return ONLY:
{"action": "monitor"}
OR:
{
  "action": "intervene",
  "type": "groupthink|assumption_blindspot|missing_context",
  "urgency": "low|medium|high",
  "message": "Max 2 sentences for the facilitator",
  "suggested_question": "Exact question to ask — 1 sentence",
  "reasoning": "Internal rationale, not shown to facilitator"
}
"""

# CIRCUIT BREAKER (protects live meetings from API outages):
@circuit_breaker(failure_threshold=3, recovery_timeout=60)
async def call_claude(prompt: str, max_tokens: int) -> str | None:
    """
    On circuit OPEN: returns None
    Callers handle None gracefully — app degrades, meeting continues uninterrupted
    """
    try:
        response = await anthropic.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except anthropic.APIError:
        raise  # circuit breaker counts this as failure
```

---

### Agent 4: Post-Mortem Generator

**Trigger**: Meeting ends (within 24 hours)
**Latency target**: <60s

```python
POST_MORTEM_SYSTEM_PROMPT = """
You are Quorum's Post-Decision Analyst. Generate a structured post-mortem.

THREE PURPOSES:
1. Capture what was decided and why (accurate record)
2. Document key assumptions explicitly (most teams never do this)
3. Set up concrete outcome measurement

RULES:
1. Be honest about warning signs Quorum detected. Frame as learning, not blame.
2. Key assumptions must be SPECIFIC:
   Bad: "We assumed the market was ready."
   Good: "We assumed enterprise buyers in financial services would approve
         new vendor relationships within 60 days."
3. Success criteria must be measurable:
   Bad: "The product performs well."
   Good: "Activation rate exceeds 40% within 30 days of launch."
4. Dissenting views come from anonymous pre-survey ONLY. Never attributed.
5. Direct, clear prose. No padding.

Return JSON:
{
  "executive_summary": "2-3 sentence summary",
  "decisions": [{
    "title": str,
    "description": str,
    "options_considered": [str],
    "rationale": str,
    "key_assumptions": [str],
    "dissenting_views": str | null,
    "confidence_at_decision": float,
    "success_criteria": {
      "30_days": str,
      "90_days": str,
      "180_days": str
    }
  }],
  "process_observations": {
    "survey_participation": str,
    "warning_signs_detected": [str],
    "what_went_well": str,
    "suggested_improvement": str
  },
  "open_questions": [str]
}
"""
```

---

### Agent 5: Pattern Detector (LangGraph Multi-Agent)

**Trigger**: Weekly batch, Sunday 03:00 UTC (Celery Beat)
**Latency target**: <5 min

```python
# PRE-COMPUTATION before LLM call (required — reduces token cost, improves accuracy):
def compute_decision_statistics(decisions: list[Decision]) -> dict:
    stats = {}

    # Domain accuracy with Wilson confidence intervals
    by_domain: dict[str, list[float]] = defaultdict(list)
    for d in decisions:
        outcome = get_latest_outcome(d)
        if outcome:
            score = {"correct": 1.0, "partially_correct": 0.5,
                     "incorrect": 0.0}.get(outcome.outcome_verdict)
            if score is not None:
                by_domain[d.domain].append(score)

    stats["domain_accuracy"] = {
        domain: {
            "accuracy": sum(s) / len(s),
            "n": len(s),
            "ci_lower": wilson_ci(s)[0],
            "ci_upper": wilson_ci(s)[1]
        }
        for domain, s in by_domain.items() if len(s) >= 5  # MINIMUM 5 data points
    }

    # Overconfidence bias
    paired = [(d.team_confidence, get_outcome_score(d))
              for d in decisions if get_outcome_score(d) is not None]
    if len(paired) >= 10:
        avg_stated = sum(p[0] for p in paired) / len(paired)
        avg_actual = sum(p[1] for p in paired) / len(paired)
        stats["overconfidence_delta"] = avg_stated - avg_actual

    return stats

PATTERN_DETECTOR_SYSTEM_PROMPT = """
You are Quorum's Pattern Analyst.

RULES:
1. Only surface patterns with >= 5 supporting data points. Smaller samples = noise.
2. Patterns must be ACTIONABLE:
   Weak: "Your team sometimes makes bad decisions."
   Strong: "Hiring decisions for senior roles show 38% accuracy vs. 71% for junior —
            teams may be overweighting technical signals and underweighting culture fit."
3. Be honest about confidence. Small samples need uncertainty language.
4. Never surface patterns that could identify individuals.

PATTERN TYPES TO INVESTIGATE:
- Domain accuracy gaps (where is this team weakest?)
- Temporal patterns (day of week, time pressure, meeting length)
- Overconfidence (where does stated confidence exceed actual accuracy?)
- Assumption failure patterns (what types of assumptions consistently fail?)
- Participation correlation (does low survey response predict worse outcomes?)
"""
```

---

## SECTION 8: API SPECIFICATION

### Base URLs
- Production: `https://api.quorum.ai/v1`
- Staging: `https://staging.api.quorum.ai/v1`

### Authentication
- All protected endpoints: `Authorization: Bearer {access_token}` (Auth0 JWT, RS256)
- Survey submission: `X-Survey-Token: {token}` header (no auth required)
- Enterprise: SAML2 via Auth0 Organizations

### Complete Endpoint Reference

```
# ORGANIZATION
GET    /org                              get org profile
PATCH  /org                              update settings (ai_context, response_rate, etc.)
GET    /org/intelligence-profile         Group Intelligence Profile

# USERS
GET    /users                            list users (admin only)
POST   /users/invite                     invite by email
DELETE /users/{id}                       remove user

# MEETINGS
POST   /meetings                         create meeting
GET    /meetings                         list (status, domain, cursor, limit)
GET    /meetings/{id}                    full detail incl. tension map (facilitator only)
PATCH  /meetings/{id}                    update (not after status=live)
DELETE /meetings/{id}                    cancel (draft/survey_open only)

# SURVEY PHASE
POST   /meetings/{id}/survey/generate            trigger AI question generation → 202 + job_id
GET    /meetings/{id}/survey/generate/{job_id}   poll for result
GET    /meetings/{id}/survey                     get questions (participant, token auth)
POST   /meetings/{id}/survey/respond             submit anonymous response (token auth, NO JWT)
GET    /meetings/{id}/survey/status              response rate (facilitator only)
POST   /meetings/{id}/tension-map/generate       trigger tension map → 202 + job_id
GET    /meetings/{id}/tension-map                get tension map (facilitator only)
GET    /meetings/{id}/facilitator-brief          formatted markdown brief (facilitator only)

# LIVE SESSION
POST   /meetings/{id}/session/start      start session, bot joins meeting
WS     /meetings/{id}/session/stream     real-time WebSocket (see protocol below)
POST   /meetings/{id}/session/end        end session
GET    /meetings/{id}/session/summary    post-session report

# DECISIONS & OUTCOMES
POST   /meetings/{id}/decisions          create decision from meeting
POST   /decisions                        create decision (standalone)
GET    /decisions                        list with filters
GET    /decisions/{id}                   full detail + outcomes + similar decisions
PATCH  /decisions/{id}                   update
POST   /decisions/{id}/post-mortem       submit post-mortem
POST   /decisions/{id}/outcomes          record outcome check-in
GET    /decisions/{id}/outcomes          all outcomes

# INTELLIGENCE
GET    /intelligence/patterns            all GIP patterns
GET    /intelligence/domain/{domain}     domain-specific intelligence
GET    /intelligence/calibration         confidence vs. actual accuracy breakdown

# WEBHOOKS (verified via signature)
POST   /webhooks/zoom                    Zoom meeting lifecycle events
POST   /webhooks/stripe                  billing events

# GDPR
GET    /gdpr/export                      export all org data (admin)
DELETE /gdpr/erase                       delete all org data (admin, 24hr SLA)
```

### WebSocket Protocol (/meetings/{id}/session/stream)

```javascript
// CLIENT → SERVER
{"type": "ping"}
{"type": "acknowledge_alert", "alert_id": "uuid", "response": "handle_it|aware|dismissed"}
{"type": "mark_decision", "title": "...", "description": "...", "timestamp": 1234}
{"type": "request_question", "context": "We're discussing timeline now"}

// SERVER → CLIENT
{"type": "pong", "timestamp": 1234567890}
{"type": "transcript_chunk", "data": {
    "speaker_hash": "a1b2c3d4",       // anonymized, 16 chars
    "text": "I think we should...",
    "start_seconds": 342
}}
{"type": "speaking_update", "data": {
    "distribution": [{"hash": "a1b2", "seconds": 180, "pct": 0.42}]
}}
{"type": "intelligence_alert", "data": {
    "alert_id": "uuid",
    "type": "groupthink|hippo|missing_perspective|assumption_blindspot",
    "urgency": "low|medium|high",
    "message": "2 sentences max",
    "suggested_question": "1 sentence",
    "timestamp_seconds": 1840
}}
{"type": "decision_suggested", "data": {
    "title": "Shortlist to 3 features",
    "confidence": 0.85
}}
{"type": "session_ended", "data": {"total_seconds": 4200}}
```

### Rate Limits
```
Starter tier:    100 req/min per org
Growth tier:     500 req/min per org
Enterprise:     2000 req/min per org
Survey submit:    10 req/min per IP (unauthenticated endpoint)
AI generation:    10 req/min per org
```

---

## SECTION 9: REAL-TIME PIPELINE ARCHITECTURE

```
Meeting audio (Zoom/Teams/Meet)
       │
       ▼
Deepgram Nova-2 WebSocket (STT)
    latency: ~300ms
    features: diarization, interim_results=False, punctuate=True
       │
       ▼ transcript chunks (every ~3 seconds)
       │
       ├──► Speaker anonymization: anonymize_speaker(zoom_id, meeting_id)
       │
       ├──► InfluxDB: speaking_time_series
       │        measurement: speaking_time
       │        tags: {org_id, meeting_id, session_id, speaker_hash}
       │        fields: {seconds_speaking}
       │
       ├──► Redis: rolling_transcript_buffer
       │        key: quorum:session:{id}:buffer
       │        type: List (FIFO, maxlen=200 chunks ≈ 10 min)
       │        TTL: 4 hours
       │
       ├──► PostgreSQL: live_transcript_chunks (persisted)
       │
       └──► WebSocket broadcast: transcript_chunk event to facilitator

EVERY 30 SECONDS:
       │
       ▼
Intelligence Evaluation Loop (asyncio task)
       │
       ├── Tier 1: HiPPO Check (rule-based, O(n) speakers)
       │       if fires → IntelligenceAlert → WebSocket → facilitator sidebar
       │
       ├── Tier 2: Groupthink Precheck (rule-based, string matching)
       │       if fires → proceed to Tier 3 LLM
       │
       ├── Tier 3: Missing Perspective (Pinecone cosine similarity)
       │       embed(last 40 chunks) vs embed(tension_area topics)
       │       cosine_sim < 0.35 → topic unaddressed → proceed to LLM
       │
       └── LLM Evaluation (Claude, <3s)
               if action=intervene → IntelligenceAlert → WebSocket
               if action=monitor → nothing (the common case)
```

---

## SECTION 10: LLM COST MODEL (VALIDATED UNIT ECONOMICS)

| Component | Input tokens | Output tokens | Cost/call |
|---|---|---|---|
| Survey Designer | ~800 | ~600 | ~$0.004 |
| Tension Analyst | ~2,000 | ~1,000 | ~$0.009 |
| Live Agent (per 30s) | ~1,500 | ~200 | ~$0.005 |
| Post-Mortem | ~2,500 | ~1,500 | ~$0.012 |
| Pattern Detector | ~8,000 | ~2,000 | ~$0.030 |

**Example: Org with 5 meetings/month (10 seats × $49 = $490 MRR)**
```
Survey design:   5 × $0.004 = $0.02
Tension maps:    5 × $0.009 = $0.045
Live (60min avg): 5 × 120 evals × $0.005 = $3.00
Post-mortems:    5 × $0.012 = $0.06
Pattern detector: 4 × $0.030 = $0.12
────────────────────────────────────────
Total LLM cost:  ~$3.25/month
LLM cost %:      0.66% of revenue — healthy unit economics at scale
```

---

## SECTION 11: PROMPT VERSIONING & A/B TESTING

```python
class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    id: UUID (PK)
    prompt_type: str        # "survey_designer"|"tension_analyst"|etc.
    version: int
    content: TEXT
    is_active: bool
    experiment_traffic_pct: float   # 0.0=control, >0=A/B test cohort
    avg_quality_score: float        # from facilitator thumbs up/down
    avg_latency_ms: int
    error_rate: float
    created_at: TIMESTAMPTZ

async def get_prompt(prompt_type: str, org_id: str) -> str:
    """Consistent hashing for A/B test assignment (same org always same bucket)."""
    experiment = await db.get_experiment(prompt_type)
    if experiment and experiment.experiment_traffic_pct > 0:
        bucket = int(hashlib.md5(org_id.encode()).hexdigest(), 16) % 100
        if bucket < experiment.experiment_traffic_pct * 100:
            return experiment.content
    active = await db.get_active_prompt(prompt_type)
    return active.content
```

**CRITICAL**: All prompt changes go through A/B test before full rollout.
Eval suites must achieve minimum quality scores before promotion:
- Survey Designer: avg score ≥ 0.85
- Tension Analyst: avg score ≥ 0.80
- Live Agent: false positive rate < 10%
- Post-Mortem: key_assumptions populated ≥ 90%
- Pattern Detector: no patterns surfaced with n < 5 data points

---

## SECTION 12: SECURITY ARCHITECTURE

### Authentication Flow
```
1. User visits app.quorum.ai
2. Redirected to Auth0 (PKCE flow, no implicit grant)
3. Auth0 returns JWT (RS256 signed, 1-hour expiry)
4. API validates JWT on every request via JWKS (cached 1 hour)
5. Refresh token (7 days) in httpOnly cookie
6. Enterprise: SAML2 IdP via Auth0 Organizations
```

### Multi-Tenancy (Defense in Depth)
1. **JWT layer**: org_id extracted from verified token
2. **Application layer**: all queries include `WHERE org_id = {user.org_id}`
3. **Database layer**: PostgreSQL RLS `SET LOCAL app.current_org_id = {org_id}`
4. **Audit layer**: every data access logged to immutable audit_log

### Environment Variables (ALL REQUIRED)
```bash
APP_ENV=production|staging|development
SECRET_KEY=<openssl rand -hex 32>

# Auth
AUTH0_DOMAIN=quorum.auth0.com
AUTH0_CLIENT_ID=...
AUTH0_CLIENT_SECRET=...
AUTH0_AUDIENCE=https://api.quorum.ai

# Databases
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/quorum
REDIS_URL=redis://host:6379/0
INFLUXDB_URL=http://host:8086
INFLUXDB_TOKEN=...
INFLUXDB_ORG=quorum
INFLUXDB_BUCKET=meeting_metrics

# AI (REQUIRED)
ANTHROPIC_API_KEY=...         # Claude Sonnet 4 — all reasoning
OPENAI_API_KEY=...            # text-embedding-3-large — embeddings only
PINECONE_API_KEY=...          # decision library semantic search
DEEPGRAM_API_KEY=...          # Nova-2 real-time STT

# Anonymization (ROTATE ANNUALLY — NEVER commit to repo)
SPEAKER_HASH_SECRET=<openssl rand -hex 32>
RESPONDENT_HASH_SECRET=<openssl rand -hex 32>

# Meeting platforms
ZOOM_CLIENT_ID=...
ZOOM_CLIENT_SECRET=...
ZOOM_WEBHOOK_SECRET=...
TEAMS_APP_ID=...
TEAMS_APP_PASSWORD=...

# Communications
SENDGRID_API_KEY=...
SENDGRID_FROM_EMAIL=hello@quorum.ai
SLACK_BOT_TOKEN=...           # optional, org-level Slack notifications

# Infrastructure
AWS_REGION=us-east-1
S3_BUCKET=quorum-recordings
STRIPE_SECRET_KEY=...
STRIPE_WEBHOOK_SECRET=...
SENTRY_DSN=...
DATADOG_API_KEY=...

# Feature flags
FEATURE_LIVE_MEETING=true
FEATURE_RECORDING=false       # off by default, requires org consent flow
FEATURE_PATTERN_DETECTOR=true
FEATURE_SLACK_INTEGRATION=true

# Runtime
CELERY_TASK_ALWAYS_EAGER=false  # set true in test environments only
```

---

## SECTION 13: REDIS KEY SCHEMA

```
# Session state (TTL: 4 hours)
quorum:session:{session_id}:state          → JSON {session metadata}
quorum:session:{session_id}:speaking       → Hash {speaker_hash → seconds}
quorum:session:{session_id}:alerts         → List {delivered alert IDs}
quorum:session:{session_id}:buffer         → List {last 200 transcript chunks}

# WebSocket connections (TTL: 4 hours)
quorum:ws:{session_id}:connections         → Set {connection IDs}

# Rate limiting (TTL: 60s)
quorum:ratelimit:{org_id}:{endpoint}       → Counter

# Survey response lock (prevents race condition)
quorum:survey:{meeting_id}:lock            → Lock (TTL: 5s)

# LLM response cache (TTL: 1 hour)
quorum:llm:tension:{meeting_id}            → JSON {cached tension map}
```

---

## SECTION 14: CELERY TASK SCHEDULE

```python
CELERYBEAT_SCHEDULE = {
    # Daily — send outcome check-in emails
    "send_outcome_checkins": {
        "task": "tasks.send_outcome_checkins",
        "schedule": crontab(hour=9, minute=0),  # 09:00 UTC (per org timezone)
    },
    # Weekly — run pattern detector
    "run_pattern_detector": {
        "task": "tasks.run_pattern_detector",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),  # Sunday 03:00 UTC
    },
    # Daily — clean up expired audio recordings
    "cleanup_expired_audio": {
        "task": "tasks.cleanup_expired_audio",
        "schedule": crontab(hour=2, minute=0),  # 02:00 UTC
    },
    # Every 2 minutes — process pending tension map generation jobs
    "process_tension_map_queue": {
        "task": "tasks.process_tension_map_queue",
        "schedule": 120.0,
    },
}

# QUEUE ROUTING:
# default         → general tasks
# high-priority   → tension map generation (facilitators waiting)
# scheduled       → outcome check-ins, pattern detector
```

---

## SECTION 15: FILE STRUCTURE (COMPLETE)

```
quorum/
├── app/
│   ├── main.py                    # FastAPI factory, middleware, exception handlers
│   ├── api/
│   │   ├── auth.py               # Auth0 JWT middleware
│   │   └── routers/
│   │       ├── orgs.py
│   │       ├── users.py
│   │       ├── meetings.py
│   │       ├── surveys.py
│   │       ├── sessions.py       # WebSocket live session
│   │       ├── decisions.py
│   │       ├── outcomes.py
│   │       ├── intelligence.py
│   │       ├── webhooks.py       # Zoom, Stripe
│   │       └── gdpr.py
│   ├── models/                   # SQLAlchemy models
│   ├── schemas/                  # Pydantic request/response schemas
│   ├── services/
│   │   ├── survey_service.py
│   │   ├── tension_map_service.py
│   │   ├── stt_service.py        # Deepgram + MeetingStreamProcessor
│   │   ├── intelligence_service.py
│   │   ├── decision_service.py
│   │   ├── outcome_service.py
│   │   ├── pattern_service.py
│   │   └── user_service.py
│   ├── workers/
│   │   ├── celery_app.py
│   │   └── tasks/
│   │       ├── send_survey_invitations.py
│   │       ├── generate_tension_map.py
│   │       ├── schedule_outcome_checkins.py
│   │       ├── run_pattern_detector.py
│   │       └── cleanup_expired_data.py
│   ├── intelligence/
│   │   ├── agents/
│   │   │   ├── survey_designer.py
│   │   │   ├── tension_analyst.py
│   │   │   ├── live_agent.py
│   │   │   ├── post_mortem_generator.py
│   │   │   └── pattern_detector.py
│   │   └── prompts.py            # all prompts centralized + versioning
│   └── core/
│       ├── config.py             # Settings from environment
│       ├── database.py           # Async SQLAlchemy + RLS helper
│       ├── security.py           # JWT, HMAC anonymization
│       ├── exceptions.py         # Custom exception hierarchy
│       └── logging.py            # structlog structured logging
├── alembic/
│   └── versions/                 # database migrations
├── tests/
│   ├── unit/
│   │   ├── test_anonymization.py       # adversarial tests (CRITICAL)
│   │   ├── test_detection_algorithms.py
│   │   ├── test_survey_validation.py
│   │   └── test_pattern_statistics.py
│   ├── integration/
│   │   ├── test_api_surveys.py
│   │   ├── test_api_meetings.py
│   │   ├── test_api_decisions.py
│   │   └── test_websocket_session.py
│   ├── ai_evals/
│   │   ├── eval_survey_designer.py
│   │   ├── eval_tension_analyst.py
│   │   └── eval_live_agent.py
│   └── conftest.py
├── web/                          # Next.js 14 frontend
│   └── app/
│       ├── (auth)/               # login, callback
│       ├── (app)/
│       │   ├── dashboard/
│       │   ├── meetings/
│       │   │   └── [id]/
│       │   │       ├── survey/   # participant survey (no auth)
│       │   │       ├── brief/    # facilitator brief (tension map)
│       │   │       ├── live/     # live meeting sidebar
│       │   │       └── decisions/
│       │   ├── decisions/        # decision library
│       │   └── intelligence/     # group intelligence profile
│       └── components/
│           ├── ui/               # shadcn/ui
│           ├── survey/
│           ├── tension-map/
│           ├── live/
│           ├── decisions/
│           └── intelligence/
├── terraform/
│   ├── main.tf
│   ├── staging.tfvars
│   └── production.tfvars
├── .github/
│   └── workflows/
│       ├── ci.yml                # lint, test, security, docker
│       └── deploy.yml            # staging (auto) + production (manual)
├── Dockerfile                    # multi-stage: base → builder → dev → production
├── docker-compose.yml
├── pyproject.toml                # ALL versions pinned exactly
├── alembic.ini
├── nginx.conf
└── Makefile
```

---

## SECTION 16: BUILD ORDER (STRICT SEQUENCE)

### Phase 1A — Foundation (Weeks 1–2)
```
1. PostgreSQL schema + all Alembic migrations + RLS policies
2. FastAPI scaffold + Auth0 JWT integration
3. Organization + User CRUD
4. Basic Next.js app with auth flow
5. CI pipeline (ruff + mypy + pytest + bandit)
```

### Phase 1B — Survey Engine (Weeks 3–5) ← DEPLOY AND CHARGE FOR THIS ALONE
```
1. Meeting CRUD endpoints + participant management
2. Survey question generator (Survey Designer agent + Instructor)
3. Anonymous survey token system + submission endpoint
4. Tension Map Generator (Tension Analyst agent + response rate gating)
5. Facilitator brief generator
6. Survey participant UI (no-auth, mobile-first)
7. Facilitator brief UI (tension map visualization)
8. Email notifications via SendGrid (invite, reminder at 50%, reminder at 90%, brief ready)
```
**MILESTONE**: Deploy, get design partners, charge. Phase 1 alone is a valuable product.

### Phase 2A — Meeting Integration (Weeks 6–9)
```
1. Deepgram Nova-2 WebSocket STT pipeline
2. Speaker diarization + anonymization (anonymize_speaker())
3. InfluxDB speaking time series
4. Redis rolling transcript buffer
5. WebSocket server for real-time events
6. Zoom Apps SDK sidebar integration
7. MeetingStreamProcessor class (the core real-time engine)
```

### Phase 2B — Live Intelligence (Weeks 10–12) ← FULL CORE PRODUCT
```
1. HiPPO detector (rule-based, Tier 1)
2. Groupthink precheck (rule-based, Tier 2)
3. Missing perspective detector (Pinecone semantic, Tier 3)
4. Live Intelligence Agent (LLM evaluation)
5. Alert delivery to facilitator WebSocket
6. Alert acknowledgment system (handle_it, aware, dismissed)
7. Teams Bot Framework integration
8. Google Meet Chrome Extension
9. Live meeting facilitator sidebar UI
```

### Phase 3 — Decisions & Outcomes (Weeks 13–15)
```
1. Decision creation + tagging (from meeting + standalone)
2. Post-mortem generator
3. Outcome check-in Celery Beat scheduler
4. Outcome recording UI (30d, 90d, 180d forms)
5. Decision library with text search + Pinecone semantic search
```

### Phase 4 — Group Intelligence (Weeks 16–18) ← THE MOAT
```
1. Pattern detector weekly LangGraph job
2. Group Intelligence Profile computation + storage
3. Intelligence dashboard (domain accuracy, radar charts, patterns)
4. Pre-meeting pattern alerts ("Your team has the Senior Leader Anchor pattern")
5. Pinecone "similar past decisions" feature
```

### Phase 5 — Production Hardening (Weeks 19–22)
```
1. Terraform AWS infrastructure
2. GitHub Actions CI/CD (staging auto, production manual approval)
3. Datadog dashboards + PagerDuty on-call
4. Sentry error tracking
5. SOC 2 Type II controls implementation
6. Auth0 SAML/SSO for enterprise
7. Stripe billing + seat management + webhooks
8. GDPR export + deletion endpoints + DPA template
```

---

## SECTION 17: NON-NEGOTIABLE PRODUCTION CONSTRAINTS

1. **Never call Claude without Instructor** — raw JSON parsing is a production disaster at scale

2. **RLS must be enabled before any production data enters the system** — there is no second chance to add this safely

3. **Anonymization secrets NEVER in the database** — AWS Secrets Manager only; if these leak, anonymization is broken

4. **80% test coverage enforced in CI** — not optional, not aspirational. `--cov-fail-under=80`

5. **All AI prompts have eval suites** — prompts are code; they need tests and minimum quality thresholds

6. **No `# type: ignore` without justification comment** — mypy strict mode always

7. **CELERY_TASK_ALWAYS_EAGER=true in tests** — async tasks run synchronously in test environment

8. **Facilitator brief is NEVER visible to participants** — separate endpoint, role-checked, not in meeting detail response

9. **The respondent endpoint returns 404** — `GET /meetings/{id}/survey/responses` must not exist

10. **Circuit breaker on all LLM calls** — failure_threshold=3, recovery_timeout=60; app degrades gracefully, meeting never interrupted

11. **All migration changes must be backward-compatible** — old code must run against new schema; two-phase for column renames

12. **Version pinning policy** — all dependencies pinned exactly; security patches within 48hrs of CVE; monthly minor upgrades in dedicated PR

13. **No raw SQL** — SQLAlchemy ORM always; `text()` only for RLS session variable

14. **Secrets in pre-commit** — TruffleHog + detect-secrets on every commit

15. **No stack traces in production error responses** — `APP_ENV == "production"` returns generic message only

---

## SECTION 18: PRICING & BUSINESS MODEL

```
Starter:    $49/seat/month  (5–15 seats)   Phase 1 features
Growth:     $99/seat/month  (16–100 seats)  + Live intelligence, outcomes, GIP
Enterprise: $149/seat/month (100+ seats)    + SAML/SSO, dedicated instance, SLA, CSM
Annual:     20% discount (2 months free)

UNIT ECONOMICS (Growth, 25 seats):
  MRR:              $2,475
  LLM costs:         ~$15
  Infrastructure:     ~$8
  Deepgram:          ~$12
  Total COGS:        ~$35
  Gross margin:      98.6%

SERIES A TARGET (Month 12): 50 orgs, $180K ARR, 3 enterprise pilots, 500+ tracked decisions
```

---

*QUORUM Master System Prompt v2.0 — Production Build Specification*
*Every architectural decision, constraint, and feature described here is internally consistent.*
*Build in the exact sequence specified in Section 16. Do not simplify the quality gates.*

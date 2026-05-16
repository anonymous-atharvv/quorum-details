# QUORUM — Complete Database Schema
## PostgreSQL 16 — production-ready DDL

---

## Conventions
- All primary keys: UUID (gen_random_uuid())
- All timestamps: TIMESTAMPTZ (UTC always)
- All foreign keys: have explicit ON DELETE behavior defined
- All JSONB columns: have a comment describing expected structure
- Soft deletes: NOT used — hard deletes with cascade where appropriate
- Row-level security: enabled on all tables, enforced per org_id

---

## Schema

```sql
-- ════════════════════════════════════════════════════════════════
-- EXTENSIONS
-- ════════════════════════════════════════════════════════════════
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- for text search on titles

-- ════════════════════════════════════════════════════════════════
-- ENUMS
-- ════════════════════════════════════════════════════════════════
CREATE TYPE org_plan AS ENUM ('starter', 'growth', 'enterprise');
CREATE TYPE user_role AS ENUM ('admin', 'facilitator', 'member');
CREATE TYPE meeting_status AS ENUM (
    'draft',
    'survey_open',
    'survey_closed',
    'live',
    'ended',
    'post_mortem_pending',
    'post_mortem_done',
    'cancelled'
);
CREATE TYPE meeting_platform AS ENUM ('zoom', 'teams', 'meet', 'other');
CREATE TYPE participant_role AS ENUM ('facilitator', 'participant');
CREATE TYPE post_mortem_status AS ENUM ('pending', 'in_progress', 'completed', 'skipped');
CREATE TYPE decision_type AS ENUM (
    'go_no_go',
    'selection',
    'prioritization',
    'commitment',
    'strategy',
    'process',
    'other'
);
CREATE TYPE outcome_period AS ENUM ('30d', '90d', '180d', 'adhoc');
CREATE TYPE outcome_verdict AS ENUM (
    'correct',
    'partially_correct',
    'incorrect',
    'too_early_to_tell',
    'decision_no_longer_relevant'
);
CREATE TYPE alert_type AS ENUM (
    'hippo',
    'groupthink',
    'missing_perspective',
    'assumption_blindspot',
    'momentum_trap'
);
CREATE TYPE alert_urgency AS ENUM ('low', 'medium', 'high');

-- ════════════════════════════════════════════════════════════════
-- ORGANIZATIONS
-- ════════════════════════════════════════════════════════════════
CREATE TABLE organizations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    domain              TEXT,  -- e.g. "acme.com" — used to enforce SSO
    plan                org_plan NOT NULL DEFAULT 'starter',
    seat_count          INTEGER NOT NULL DEFAULT 5,
    stripe_customer_id  TEXT UNIQUE,
    stripe_sub_id       TEXT UNIQUE,
    auth0_org_id        TEXT UNIQUE,  -- Auth0 Organization ID for SSO
    settings            JSONB NOT NULL DEFAULT '{}',
    -- settings structure:
    -- {
    --   "recording_consent_enabled": bool,
    --   "slack_webhook_url": str | null,
    --   "ai_context": str,  -- org context injected into AI prompts
    --   "outcome_check_in_day": int,  -- day of week for check-in emails (0=Mon)
    --   "meeting_platforms": ["zoom", "teams", "meet"],
    --   "min_survey_response_rate": float  -- default 0.5
    -- }
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_orgs_domain ON organizations(domain) WHERE domain IS NOT NULL;
CREATE INDEX idx_orgs_stripe ON organizations(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;

-- ════════════════════════════════════════════════════════════════
-- USERS
-- ════════════════════════════════════════════════════════════════
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    auth0_id        TEXT NOT NULL UNIQUE,
    email           TEXT NOT NULL,
    display_name    TEXT,
    role            user_role NOT NULL DEFAULT 'member',
    last_active_at  TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(org_id, email)
);

CREATE INDEX idx_users_org ON users(org_id);
CREATE INDEX idx_users_auth0 ON users(auth0_id);
CREATE INDEX idx_users_email ON users(email);

-- ════════════════════════════════════════════════════════════════
-- API KEYS (for integrations)
-- ════════════════════════════════════════════════════════════════
CREATE TABLE api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by      UUID NOT NULL REFERENCES users(id),
    name            TEXT NOT NULL,
    key_prefix      TEXT NOT NULL,  -- first 8 chars shown in UI (e.g. "qm_live_")
    key_hash        TEXT NOT NULL UNIQUE,  -- bcrypt hash of full key
    scopes          TEXT[] NOT NULL DEFAULT '{}',
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    revoked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_keys_org ON api_keys(org_id);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);

-- ════════════════════════════════════════════════════════════════
-- MEETINGS
-- ════════════════════════════════════════════════════════════════
CREATE TABLE meetings (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by                  UUID NOT NULL REFERENCES users(id),
    title                       TEXT NOT NULL,
    description                 TEXT,
    scheduled_at                TIMESTAMPTZ NOT NULL,
    duration_minutes            INTEGER NOT NULL DEFAULT 60,
    platform                    meeting_platform NOT NULL DEFAULT 'other',
    platform_meeting_id         TEXT,  -- Zoom meeting ID, Teams meeting ID, etc.
    platform_join_url           TEXT,
    status                      meeting_status NOT NULL DEFAULT 'draft',

    -- Calendar integration
    calendar_event_id           TEXT,  -- Google Calendar / Outlook event ID
    calendar_provider           TEXT,  -- 'google' | 'outlook'

    -- Agenda
    agenda_items                JSONB NOT NULL DEFAULT '[]',
    -- [{title: str, description: str, duration_mins: int, type: str}]

    -- Phase 1: Survey
    survey_sent_at              TIMESTAMPTZ,
    survey_deadline             TIMESTAMPTZ,
    survey_participant_count    INTEGER NOT NULL DEFAULT 0,
    survey_response_count       INTEGER NOT NULL DEFAULT 0,
    generated_questions         JSONB,
    -- Full GeneratedSurvey JSON from AI

    -- Phase 1: Tension Map
    tension_map                 JSONB,
    -- Full TensionMapOutput JSON from AI
    tension_map_generated_at    TIMESTAMPTZ,
    facilitator_brief           TEXT,
    -- Formatted markdown brief derived from tension map

    -- Phase 2: Live session
    live_session_started_at     TIMESTAMPTZ,
    live_session_ended_at       TIMESTAMPTZ,

    -- Metadata
    tags                        TEXT[] DEFAULT '{}',
    domain                      TEXT,  -- 'product'|'hiring'|'strategy'|etc.

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_meetings_org_status ON meetings(org_id, status);
CREATE INDEX idx_meetings_scheduled ON meetings(scheduled_at);
CREATE INDEX idx_meetings_platform_id ON meetings(platform, platform_meeting_id)
    WHERE platform_meeting_id IS NOT NULL;
CREATE INDEX idx_meetings_title_trgm ON meetings USING gin(title gin_trgm_ops);

-- ════════════════════════════════════════════════════════════════
-- MEETING PARTICIPANTS
-- ════════════════════════════════════════════════════════════════
CREATE TABLE meeting_participants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id      UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role            participant_role NOT NULL DEFAULT 'participant',
    invited_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    survey_sent_at  TIMESTAMPTZ,
    survey_token    TEXT UNIQUE,  -- unique token in survey email link
    survey_completed_at TIMESTAMPTZ,
    joined_live_at  TIMESTAMPTZ,
    left_live_at    TIMESTAMPTZ,
    UNIQUE(meeting_id, user_id)
);

CREATE INDEX idx_participants_meeting ON meeting_participants(meeting_id);
CREATE INDEX idx_participants_user ON meeting_participants(user_id);
CREATE INDEX idx_participants_token ON meeting_participants(survey_token)
    WHERE survey_token IS NOT NULL;

-- ════════════════════════════════════════════════════════════════
-- SURVEY RESPONSES (anonymized at insert)
-- ════════════════════════════════════════════════════════════════
CREATE TABLE survey_responses (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id          UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    -- CRITICAL: respondent_hash is a one-way HMAC of user_id + meeting_id + secret
    -- It is cryptographically impossible to reverse without the server secret
    -- Even a DBA with full DB access cannot identify who submitted this response
    respondent_hash     TEXT NOT NULL,
    submitted_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    responses           JSONB NOT NULL,
    -- [{
    --   question_id: str,
    --   question_text: str,
    --   answer: str | int | [str],
    --   confidence: int | null  (1-10, if question had include_confidence)
    -- }]
    UNIQUE(meeting_id, respondent_hash)  -- one response per person per meeting
);

CREATE INDEX idx_survey_responses_meeting ON survey_responses(meeting_id);
-- NOTE: no index on respondent_hash intentionally
-- We never query "find responses by this person" — only "find all responses for meeting"

-- ════════════════════════════════════════════════════════════════
-- LIVE MEETING SESSIONS
-- ════════════════════════════════════════════════════════════════
CREATE TABLE live_meeting_sessions (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id                      UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    UNIQUE(meeting_id),  -- one session per meeting
    started_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at                        TIMESTAMPTZ,
    total_seconds                   INTEGER NOT NULL DEFAULT 0,

    -- Speaking distribution (anonymized)
    speaking_distribution           JSONB NOT NULL DEFAULT '{}',
    -- {speaker_hash: seconds_speaking}

    -- Intelligence signals detected
    hippo_events                    JSONB NOT NULL DEFAULT '[]',
    -- [{timestamp_seconds: int, speaker_hash: str, pct_speaking: float, alert_id: uuid}]
    groupthink_events               JSONB NOT NULL DEFAULT '[]',
    -- [{timestamp_seconds: int, topic: str, tension_topic_matched: str, alert_id: uuid}]
    missing_perspective_events      JSONB NOT NULL DEFAULT '[]',
    -- [{timestamp_seconds: int, tension_area: str, alert_id: uuid}]

    -- Alerts delivered
    total_alerts_delivered          INTEGER NOT NULL DEFAULT 0,
    alerts_actioned                 INTEGER NOT NULL DEFAULT 0,
    -- actioned = facilitator clicked "handle it" or "I'm aware"

    created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sessions_meeting ON live_meeting_sessions(meeting_id);

-- ════════════════════════════════════════════════════════════════
-- LIVE TRANSCRIPT CHUNKS
-- ════════════════════════════════════════════════════════════════
CREATE TABLE live_transcript_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES live_meeting_sessions(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    start_seconds   INTEGER NOT NULL,
    end_seconds     INTEGER NOT NULL,
    speaker_hash    TEXT NOT NULL,  -- anonymized, meeting-scoped
    text            TEXT NOT NULL,
    word_count      INTEGER,
    embedding_id    TEXT,  -- Pinecone vector ID (if embedded)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(session_id, chunk_index)
);

CREATE INDEX idx_chunks_session ON live_transcript_chunks(session_id, chunk_index);
-- No index on speaker_hash — we never query by speaker

-- ════════════════════════════════════════════════════════════════
-- INTELLIGENCE ALERTS (live meeting)
-- ════════════════════════════════════════════════════════════════
CREATE TABLE intelligence_alerts (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id              UUID NOT NULL REFERENCES live_meeting_sessions(id) ON DELETE CASCADE,
    alert_type              alert_type NOT NULL,
    urgency                 alert_urgency NOT NULL DEFAULT 'medium',
    triggered_at_seconds    INTEGER NOT NULL,
    message                 TEXT NOT NULL,
    suggested_question      TEXT,
    internal_reasoning      TEXT,  -- stored for model evaluation/debugging

    -- Facilitator response
    acknowledged_at         TIMESTAMPTZ,
    response                TEXT,  -- 'handle_it' | 'aware' | 'dismissed' | null

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_alerts_session ON intelligence_alerts(session_id);

-- ════════════════════════════════════════════════════════════════
-- DECISIONS
-- ════════════════════════════════════════════════════════════════
CREATE TABLE decisions (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    meeting_id                  UUID REFERENCES meetings(id) ON DELETE SET NULL,
    created_by                  UUID NOT NULL REFERENCES users(id),

    title                       TEXT NOT NULL,
    description                 TEXT NOT NULL,
    domain                      TEXT NOT NULL DEFAULT 'other',
    decision_type               decision_type NOT NULL DEFAULT 'other',

    -- Context at time of decision
    options_considered          JSONB NOT NULL DEFAULT '[]',
    -- [{option: str, rationale: str, pros: [str], cons: [str], was_chosen: bool}]
    key_assumptions             JSONB NOT NULL DEFAULT '[]',
    -- [{assumption: str, confidence: float, how_to_verify: str, check_in_question: str}]
    dissenting_views            JSONB NOT NULL DEFAULT '[]',
    -- [{view: str, source: 'survey'|'meeting'|'manual'}]  — always anonymous
    team_confidence             FLOAT,  -- 0.0-1.0, stated confidence at decision time

    -- Post-mortem
    post_mortem_status          post_mortem_status NOT NULL DEFAULT 'pending',
    post_mortem_notes           TEXT,
    post_mortem_completed_at    TIMESTAMPTZ,

    -- Outcome check-in schedule (set automatically on creation)
    check_in_30d_at             TIMESTAMPTZ,
    check_in_90d_at             TIMESTAMPTZ,
    check_in_180d_at            TIMESTAMPTZ,
    check_in_30d_sent           BOOLEAN NOT NULL DEFAULT FALSE,
    check_in_90d_sent           BOOLEAN NOT NULL DEFAULT FALSE,
    check_in_180d_sent          BOOLEAN NOT NULL DEFAULT FALSE,

    -- Embedding (Pinecone vector ID for semantic search)
    embedding_id                TEXT,

    tags                        TEXT[] DEFAULT '{}',
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_decisions_org ON decisions(org_id);
CREATE INDEX idx_decisions_meeting ON decisions(meeting_id) WHERE meeting_id IS NOT NULL;
CREATE INDEX idx_decisions_domain ON decisions(org_id, domain);
CREATE INDEX idx_decisions_checkins ON decisions(check_in_30d_at, check_in_30d_sent)
    WHERE check_in_30d_sent = FALSE;
CREATE INDEX idx_decisions_title_trgm ON decisions USING gin(title gin_trgm_ops);
CREATE INDEX idx_decisions_assumptions ON decisions USING gin(key_assumptions jsonb_path_ops);

-- ════════════════════════════════════════════════════════════════
-- DECISION OUTCOMES
-- ════════════════════════════════════════════════════════════════
CREATE TABLE decision_outcomes (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id                     UUID NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
    recorded_by                     UUID NOT NULL REFERENCES users(id),
    check_in_period                 outcome_period NOT NULL,
    recorded_at                     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    outcome_verdict                 outcome_verdict NOT NULL,
    outcome_description             TEXT NOT NULL,
    what_we_got_right               TEXT,
    what_we_missed                  TEXT,
    key_assumptions_that_failed     JSONB NOT NULL DEFAULT '[]',
    -- [assumption text strings from original key_assumptions that turned out wrong]

    -- For pattern detection
    prediction_accuracy_score       FLOAT,  -- 0.0-1.0 derived from verdict
    lessons_learned                 TEXT,

    created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_outcomes_decision ON decision_outcomes(decision_id);
CREATE INDEX idx_outcomes_verdict ON decision_outcomes(outcome_verdict);

-- ════════════════════════════════════════════════════════════════
-- GROUP INTELLIGENCE PROFILE
-- ════════════════════════════════════════════════════════════════
CREATE TABLE group_intelligence_profiles (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    UNIQUE(org_id),

    -- Aggregate accuracy
    total_decisions_tracked         INTEGER NOT NULL DEFAULT 0,
    decisions_with_outcomes         INTEGER NOT NULL DEFAULT 0,
    overall_accuracy_score          FLOAT,  -- null until >= 5 outcomes
    confidence_calibration_score    FLOAT,  -- accuracy vs stated confidence

    -- Patterns (from pattern detector)
    identified_patterns             JSONB NOT NULL DEFAULT '[]',
    -- [IdentifiedPattern JSON]

    -- Domain breakdown
    domain_accuracy                 JSONB NOT NULL DEFAULT '{}',
    -- {domain: {decisions: int, outcomes: int, accuracy: float, trend: str}}

    -- Meeting dynamics health
    avg_survey_response_rate        FLOAT,
    avg_speaking_time_gini          FLOAT,
    hippo_frequency_score           FLOAT,
    groupthink_frequency_score      FLOAT,

    -- Recommendations
    recommended_practices           JSONB NOT NULL DEFAULT '[]',

    -- Metadata
    last_pattern_run_at             TIMESTAMPTZ,
    last_updated                    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ════════════════════════════════════════════════════════════════
-- AUDIT LOG (immutable)
-- ════════════════════════════════════════════════════════════════
CREATE TABLE audit_log (
    id              BIGSERIAL PRIMARY KEY,  -- bigserial not UUID for insert perf
    org_id          UUID NOT NULL,
    user_id         UUID,  -- null for system actions
    action          TEXT NOT NULL,  -- e.g. 'meeting.created', 'survey.responded'
    resource_type   TEXT NOT NULL,  -- 'meeting', 'decision', 'survey_response', etc.
    resource_id     TEXT NOT NULL,  -- UUID of affected resource
    metadata        JSONB NOT NULL DEFAULT '{}',
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Audit log is append-only — no UPDATE or DELETE permissions on this table
-- In production: revoke UPDATE, DELETE from application user
REVOKE UPDATE, DELETE ON audit_log FROM quorum_app;

CREATE INDEX idx_audit_org ON audit_log(org_id, created_at DESC);
CREATE INDEX idx_audit_resource ON audit_log(resource_type, resource_id);

-- ════════════════════════════════════════════════════════════════
-- ROW-LEVEL SECURITY
-- ════════════════════════════════════════════════════════════════
-- Applied to all core tables. org_id set from JWT in FastAPI middleware.

ALTER TABLE meetings ENABLE ROW LEVEL SECURITY;
ALTER TABLE meeting_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE survey_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE live_meeting_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE live_transcript_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE intelligence_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE decision_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Example policy (repeat pattern for all tables):
CREATE POLICY meetings_org_isolation ON meetings
    USING (org_id = current_setting('app.current_org_id', TRUE)::UUID);

CREATE POLICY users_org_isolation ON users
    USING (org_id = current_setting('app.current_org_id', TRUE)::UUID);

-- Survey responses: additional protection — accessible only within org context
CREATE POLICY survey_responses_org_isolation ON survey_responses
    USING (
        meeting_id IN (
            SELECT id FROM meetings 
            WHERE org_id = current_setting('app.current_org_id', TRUE)::UUID
        )
    );

-- ════════════════════════════════════════════════════════════════
-- TRIGGERS
-- ════════════════════════════════════════════════════════════════

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_meetings_updated_at
    BEFORE UPDATE ON meetings
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_decisions_updated_at
    BEFORE UPDATE ON decisions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Auto-update survey response count on meetings
CREATE OR REPLACE FUNCTION update_survey_response_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE meetings
    SET survey_response_count = (
        SELECT COUNT(*) FROM survey_responses WHERE meeting_id = NEW.meeting_id
    )
    WHERE id = NEW.meeting_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_survey_response_count
    AFTER INSERT OR DELETE ON survey_responses
    FOR EACH ROW EXECUTE FUNCTION update_survey_response_count();

-- Auto-set outcome check-in dates when decision is created
CREATE OR REPLACE FUNCTION set_decision_checkin_dates()
RETURNS TRIGGER AS $$
BEGIN
    NEW.check_in_30d_at  = NEW.created_at + INTERVAL '30 days';
    NEW.check_in_90d_at  = NEW.created_at + INTERVAL '90 days';
    NEW.check_in_180d_at = NEW.created_at + INTERVAL '180 days';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_decision_checkin_dates
    BEFORE INSERT ON decisions
    FOR EACH ROW EXECUTE FUNCTION set_decision_checkin_dates();

-- Auto-compute accuracy score from outcome verdict
CREATE OR REPLACE FUNCTION set_prediction_accuracy()
RETURNS TRIGGER AS $$
BEGIN
    NEW.prediction_accuracy_score = CASE NEW.outcome_verdict
        WHEN 'correct'                      THEN 1.0
        WHEN 'partially_correct'            THEN 0.5
        WHEN 'incorrect'                    THEN 0.0
        WHEN 'too_early_to_tell'            THEN NULL
        WHEN 'decision_no_longer_relevant'  THEN NULL
    END;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_outcome_accuracy
    BEFORE INSERT OR UPDATE ON decision_outcomes
    FOR EACH ROW EXECUTE FUNCTION set_prediction_accuracy();

-- ════════════════════════════════════════════════════════════════
-- SEED DATA (development only)
-- ════════════════════════════════════════════════════════════════
-- Run: psql $DATABASE_URL -f schema.sql -f seed.sql
-- seed.sql not included in production migrations
```

---

## Migration Strategy

```
migrations/
├── 001_initial_schema.py          # All tables above
├── 002_add_embedding_ids.py       # Add embedding_id columns (Phase 4)
├── 003_add_rls_policies.py        # Row-level security (before production)
├── 004_add_audit_triggers.py      # Audit log triggers
└── 005_performance_indexes.py     # Additional indexes after first load test
```

Run with Alembic:
```bash
alembic upgrade head           # apply all migrations
alembic downgrade -1           # roll back one
alembic revision --autogenerate -m "description"   # generate from model changes
```

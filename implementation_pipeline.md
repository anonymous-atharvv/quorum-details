# QUORUM — GOD-TIER IMPLEMENTATION PIPELINE
## Complete Production Build Specification v3.0 — Top 1% Engineer Grade

> **AUTHORITY**: This document supersedes all others. Every gap identified in the existing codebase is catalogued, prioritized, and given exact implementation instructions. Feed this to Claude Code, Cursor, or any frontier coding agent as the authoritative build specification.

---

## PART 0 — EXISTING CODEBASE AUDIT (What's Built vs. What's Missing)

### ✅ BUILT (Solid Foundation)
- FastAPI routing skeleton across all resource domains
- SQLAlchemy models with correct relationships
- Auth0 JWT verification + dev HS256 fallback
- Instructor-wrapped Claude agents (Survey Designer, Tension Analyst, Live Agent, Post-Mortem, Pattern Detector)
- HMAC-SHA256 anonymization (`anonymize_respondent`, `anonymize_speaker`)
- WebSocket live session with simulated intelligence loop
- Circuit breaker pattern on LLM calls
- Celery task structure + Beat scheduler
- Next.js 14 App Router frontend with all major pages
- Stripe, SendGrid, Deepgram, Pinecone service wrappers
- Docker Compose full local stack
- GitHub Actions CI + deploy pipeline
- Terraform AWS infrastructure skeleton
- GDPR export/erase endpoints

### ❌ CRITICAL GAPS (Will Cause Production Failures)

#### Gap 1 — Database: No actual RLS policies written for most tables
**Status**: Only `meetings` and `users` have RLS in the schema doc. `decisions`, `survey_responses`, `live_transcript_chunks`, `decision_outcomes`, `group_intelligence_profiles` have `ENABLE ROW LEVEL SECURITY` but no CREATE POLICY statements.

#### Gap 2 — `app/main.py`: `await conn.execute("SELECT 1")` uses string — asyncpg requires `text()`
**Status**: Will crash on startup in production with asyncpg.

#### Gap 3 — `stt_service.py`: `_intelligence_evaluation_loop` defined twice; `self._eval_task` assigned before coroutine created
**Status**: SyntaxError / logic bug — live meeting intelligence will never run.

#### Gap 4 — `meetings.py` router: Full version imports `notification_service`, `email_service`, `audit_service` which are not guaranteed to be importable if SendGrid key is missing
**Status**: Meeting creation crashes in dev without optional service graceful degradation.

#### Gap 5 — No Alembic migration files exist — only `alembic.ini` and schema SQL
**Status**: `alembic upgrade head` will error with no migration versions.

#### Gap 6 — `app/models/models.py` referenced everywhere but not provided
**Status**: Every router import will fail. The models file is the single most critical missing file.

#### Gap 7 — `app/schemas/schemas.py` referenced everywhere but not provided
**Status**: Same as above — all Pydantic request/response schemas missing.

#### Gap 8 — `src/app/auth/` routes for Auth0 callback missing
**Status**: `auth0.middleware()` references `/auth/login`, `/auth/callback`, `/auth/access-token` — none implemented.

#### Gap 9 — Pinecone `APP_URL` setting missing from `Settings` class
**Status**: `email_service.py` references `settings.APP_URL` which doesn't exist in `config.py`.

#### Gap 10 — No Celery task implementations — only `app/workers/tasks/` stubs
**Status**: `schedule_outcome_checkins`, `run_pattern_detector`, etc. are imported but not implemented.

#### Gap 11 — `intelligence.py` router: `selectinload` imported but `Decision` model's `meeting` relationship not defined in the provided schema
**Status**: `selectinload(Decision.meeting)` will error.

#### Gap 12 — No test fixtures / factory-boy factories for any model
**Status**: Integration tests cannot run without `conftest.py` factories.

#### Gap 13 — No `app/services/email_service.py` `APP_URL` setting; missing `display_name` on `CurrentUser`
**Status**: `meetings.py` (full version) references `current_user.display_name` which doesn't exist on `CurrentUser`.

#### Gap 14 — WebSocket auth token passed as query param is insecure and breaks in production with WSS
**Status**: Token should be sent in first WebSocket message, not URL query param.

#### Gap 15 — No database seed data or `scripts/seed_db.py`
**Status**: `make db-seed` and `make setup` will fail.

---

## PART 1 — EXACT FILE IMPLEMENTATIONS (Fill Every Gap)

### 1.1 — `app/models/models.py` (THE MOST CRITICAL MISSING FILE)

```python
"""
app/models/models.py — Complete SQLAlchemy model definitions for Quorum.
All models use UUID PKs, TIMESTAMPTZ for dates, and proper relationships.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Enum, Float,
    ForeignKey, Index, Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ── Enums ──────────────────────────────────────────────────────────────
class OrgPlan(PyEnum):
    STARTER = "starter"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"


class UserRole(PyEnum):
    ADMIN = "admin"
    FACILITATOR = "facilitator"
    MEMBER = "member"


class MeetingStatus(PyEnum):
    DRAFT = "draft"
    SURVEY_OPEN = "survey_open"
    SURVEY_CLOSED = "survey_closed"
    LIVE = "live"
    ENDED = "ended"
    POST_MORTEM_PENDING = "post_mortem_pending"
    POST_MORTEM_DONE = "post_mortem_done"
    CANCELLED = "cancelled"


class MeetingPlatform(PyEnum):
    ZOOM = "zoom"
    TEAMS = "teams"
    MEET = "meet"
    OTHER = "other"


class ParticipantRole(PyEnum):
    FACILITATOR = "facilitator"
    PARTICIPANT = "participant"


class PostMortemStatus(PyEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class DecisionType(PyEnum):
    GO_NO_GO = "go_no_go"
    SELECTION = "selection"
    PRIORITIZATION = "prioritization"
    COMMITMENT = "commitment"
    STRATEGY = "strategy"
    PROCESS = "process"
    OTHER = "other"


class OutcomePeriod(PyEnum):
    THIRTY_DAYS = "30d"
    NINETY_DAYS = "90d"
    ONE_EIGHTY_DAYS = "180d"
    ADHOC = "adhoc"


class OutcomeVerdict(PyEnum):
    CORRECT = "correct"
    PARTIALLY_CORRECT = "partially_correct"
    INCORRECT = "incorrect"
    TOO_EARLY = "too_early_to_tell"
    NO_LONGER_RELEVANT = "decision_no_longer_relevant"


class AlertType(PyEnum):
    HIPPO = "hippo"
    GROUPTHINK = "groupthink"
    MISSING_PERSPECTIVE = "missing_perspective"
    ASSUMPTION_BLINDSPOT = "assumption_blindspot"
    MOMENTUM_TRAP = "momentum_trap"


class AlertUrgency(PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LiveSessionStatus(PyEnum):
    ACTIVE = "active"
    ENDED = "ended"
    ERROR = "error"


# ── Models ──────────────────────────────────────────────────────────────
class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plan: Mapped[OrgPlan] = mapped_column(Enum(OrgPlan), nullable=False, default=OrgPlan.STARTER)
    seat_count: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    stripe_sub_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    auth0_org_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    users: Mapped[list["User"]] = relationship("User", back_populates="org", cascade="all, delete-orphan")
    meetings: Mapped[list["Meeting"]] = relationship("Meeting", back_populates="org", cascade="all, delete-orphan")
    decisions: Mapped[list["Decision"]] = relationship("Decision", back_populates="org", cascade="all, delete-orphan")
    intelligence_profile: Mapped["GroupIntelligenceProfile | None"] = relationship("GroupIntelligenceProfile", back_populates="org", uselist=False)

    __table_args__ = (
        Index("idx_orgs_domain", "domain"),
        Index("idx_orgs_stripe", "stripe_customer_id"),
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    auth0_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.MEMBER)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    org: Mapped["Organization"] = relationship("Organization", back_populates="users")
    participants: Mapped[list["MeetingParticipant"]] = relationship("MeetingParticipant", back_populates="user")
    decisions_created: Mapped[list["Decision"]] = relationship("Decision", back_populates="creator")
    outcomes_recorded: Mapped[list["DecisionOutcome"]] = relationship("DecisionOutcome", back_populates="recorded_by_user")
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    api_keys: Mapped[list["ApiKey"]] = relationship("ApiKey", back_populates="created_by_user")

    __table_args__ = (
        UniqueConstraint("org_id", "email", name="uq_users_org_email"),
        Index("idx_users_org", "org_id"),
        Index("idx_users_auth0", "auth0_id"),
        Index("idx_users_email", "email"),
    )


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    scopes: Mapped[list] = mapped_column(ARRAY(String), nullable=False, default=list)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())

    org: Mapped["Organization"] = relationship("Organization")
    created_by_user: Mapped["User"] = relationship("User", back_populates="api_keys")

    __table_args__ = (
        Index("idx_api_keys_org", "org_id"),
        Index("idx_api_keys_hash", "key_hash"),
    )


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    platform: Mapped[MeetingPlatform] = mapped_column(Enum(MeetingPlatform), nullable=False, default=MeetingPlatform.OTHER)
    platform_meeting_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    platform_join_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    status: Mapped[MeetingStatus] = mapped_column(Enum(MeetingStatus), nullable=False, default=MeetingStatus.DRAFT)
    calendar_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    calendar_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    agenda_items: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    survey_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    survey_deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    survey_participant_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    survey_response_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generated_questions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tension_map: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tension_map_generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    facilitator_brief: Mapped[str | None] = mapped_column(Text, nullable=True)
    live_session_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    live_session_ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tags: Mapped[list] = mapped_column(ARRAY(String), nullable=False, default=list)
    domain: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    org: Mapped["Organization"] = relationship("Organization", back_populates="meetings")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    participants: Mapped[list["MeetingParticipant"]] = relationship("MeetingParticipant", back_populates="meeting", cascade="all, delete-orphan")
    survey_responses: Mapped[list["SurveyResponse"]] = relationship("SurveyResponse", back_populates="meeting", cascade="all, delete-orphan")
    live_session: Mapped["LiveMeetingSession | None"] = relationship("LiveMeetingSession", back_populates="meeting", uselist=False)
    decisions: Mapped[list["Decision"]] = relationship("Decision", back_populates="meeting")

    __table_args__ = (
        Index("idx_meetings_org_status", "org_id", "status"),
        Index("idx_meetings_scheduled", "scheduled_at"),
        Index("idx_meetings_platform_id", "platform", "platform_meeting_id"),
    )


class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[ParticipantRole] = mapped_column(Enum(ParticipantRole), nullable=False, default=ParticipantRole.PARTICIPANT)
    invited_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    survey_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    survey_token: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    survey_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    joined_live_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    left_live_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="participants")
    user: Mapped["User"] = relationship("User", back_populates="participants")

    __table_args__ = (
        UniqueConstraint("meeting_id", "user_id", name="uq_participant_meeting_user"),
        Index("idx_participants_meeting", "meeting_id"),
        Index("idx_participants_user", "user_id"),
        Index("idx_participants_token", "survey_token"),
    )


class SurveyResponse(Base):
    __tablename__ = "survey_responses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    respondent_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    responses: Mapped[list] = mapped_column(JSONB, nullable=False)

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="survey_responses")

    __table_args__ = (
        UniqueConstraint("meeting_id", "respondent_hash", name="uq_survey_response_per_person"),
        Index("idx_survey_responses_meeting", "meeting_id"),
        # NO index on respondent_hash — intentional
    )


class LiveMeetingSession(Base):
    __tablename__ = "live_meeting_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), unique=True, nullable=False)
    status: Mapped[LiveSessionStatus] = mapped_column(Enum(LiveSessionStatus), nullable=False, default=LiveSessionStatus.ACTIVE)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    speaking_distribution: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    hippo_events: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    groupthink_events: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    missing_perspective_events: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    total_alerts_delivered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    alerts_actioned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="live_session")
    transcript_chunks: Mapped[list["LiveTranscriptChunk"]] = relationship("LiveTranscriptChunk", back_populates="session", cascade="all, delete-orphan")
    alerts: Mapped[list["IntelligenceAlert"]] = relationship("IntelligenceAlert", back_populates="session", cascade="all, delete-orphan")


class LiveTranscriptChunk(Base):
    __tablename__ = "live_transcript_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("live_meeting_sessions.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    end_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker_hash: Mapped[str] = mapped_column(String(32), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())

    session: Mapped["LiveMeetingSession"] = relationship("LiveMeetingSession", back_populates="transcript_chunks")

    __table_args__ = (
        UniqueConstraint("session_id", "chunk_index", name="uq_chunk_session_index"),
        Index("idx_chunks_session", "session_id", "chunk_index"),
    )


class IntelligenceAlert(Base):
    __tablename__ = "intelligence_alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("live_meeting_sessions.id", ondelete="CASCADE"), nullable=False)
    alert_type: Mapped[AlertType] = mapped_column(Enum(AlertType), nullable=False)
    urgency: Mapped[AlertUrgency] = mapped_column(Enum(AlertUrgency), nullable=False, default=AlertUrgency.MEDIUM)
    triggered_at_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    response: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())

    session: Mapped["LiveMeetingSession"] = relationship("LiveMeetingSession", back_populates="alerts")

    __table_args__ = (
        Index("idx_alerts_session", "session_id"),
    )


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    meeting_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="SET NULL"), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(100), nullable=False, default="other")
    decision_type: Mapped[DecisionType] = mapped_column(Enum(DecisionType), nullable=False, default=DecisionType.OTHER)
    options_considered: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    key_assumptions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    dissenting_views: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    team_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    post_mortem_status: Mapped[PostMortemStatus] = mapped_column(Enum(PostMortemStatus), nullable=False, default=PostMortemStatus.PENDING)
    post_mortem_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    post_mortem_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    check_in_30d_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    check_in_90d_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    check_in_180d_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    check_in_30d_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    check_in_90d_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    check_in_180d_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags: Mapped[list] = mapped_column(ARRAY(String), nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    org: Mapped["Organization"] = relationship("Organization", back_populates="decisions")
    meeting: Mapped["Meeting | None"] = relationship("Meeting", back_populates="decisions")
    creator: Mapped["User"] = relationship("User", back_populates="decisions_created")
    outcomes: Mapped[list["DecisionOutcome"]] = relationship("DecisionOutcome", back_populates="decision", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_decisions_org", "org_id"),
        Index("idx_decisions_meeting", "meeting_id"),
        Index("idx_decisions_domain", "org_id", "domain"),
        Index("idx_decisions_checkins", "check_in_30d_at", "check_in_30d_sent"),
    )


class DecisionOutcome(Base):
    __tablename__ = "decision_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False)
    recorded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    check_in_period: Mapped[str] = mapped_column(String(20), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    outcome_verdict: Mapped[str] = mapped_column(String(50), nullable=False)
    outcome_description: Mapped[str] = mapped_column(Text, nullable=False)
    what_we_got_right: Mapped[str | None] = mapped_column(Text, nullable=True)
    what_we_missed: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_assumptions_that_failed: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    prediction_accuracy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    lessons_learned: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())

    decision: Mapped["Decision"] = relationship("Decision", back_populates="outcomes")
    recorded_by_user: Mapped["User"] = relationship("User", back_populates="outcomes_recorded")

    __table_args__ = (
        Index("idx_outcomes_decision", "decision_id"),
    )


class GroupIntelligenceProfile(Base):
    __tablename__ = "group_intelligence_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, nullable=False)
    total_decisions_tracked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    decisions_with_outcomes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overall_accuracy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_calibration_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    identified_patterns: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    domain_accuracy: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    avg_survey_response_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_speaking_time_gini: Mapped[float | None] = mapped_column(Float, nullable=True)
    hippo_frequency_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    groupthink_frequency_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    recommended_practices: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    last_pattern_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())

    org: Mapped["Organization"] = relationship("Organization", back_populates="intelligence_profile")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(255), nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())

    __table_args__ = (
        Index("idx_audit_org", "org_id", "created_at"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
    )


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="notifications")

    __table_args__ = (
        Index("idx_notifications_user", "user_id", "is_read"),
    )


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_type: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    experiment_traffic_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())

    __table_args__ = (
        UniqueConstraint("prompt_type", "version", name="uq_prompt_type_version"),
        Index("idx_prompt_versions_type", "prompt_type", "is_active"),
    )
```

---

### 1.2 — `app/schemas/schemas.py` (SECOND MOST CRITICAL MISSING FILE)

```python
"""
app/schemas/schemas.py — All Pydantic request/response schemas for Quorum.
These form the API contract. Keep in sync with models.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Pagination ──────────────────────────────────────────────────────────
class PaginationMeta(BaseModel):
    total: int
    has_more: bool
    cursor: str | None = None


class PaginatedResponse(BaseModel):
    data: list[Any]
    pagination: PaginationMeta


# ── Org ──────────────────────────────────────────────────────────────────
class OrgSettings(BaseModel):
    recording_consent_enabled: bool = False
    slack_webhook_url: str | None = None
    ai_context: str = ""
    outcome_check_in_day: int = 1  # 1=Mon
    meeting_platforms: list[str] = ["zoom", "teams", "meet"]
    min_survey_response_rate: float = 0.5

    model_config = {"extra": "allow"}  # forward-compatible with future settings


class OrgResponse(BaseModel):
    id: uuid.UUID
    name: str
    domain: str | None
    plan: str
    seat_count: int
    seats_used: int
    settings: OrgSettings
    created_at: datetime

    model_config = {"from_attributes": True}


class OrgUpdate(BaseModel):
    name: str | None = None
    settings: dict | None = None


# ── Users ────────────────────────────────────────────────────────────────
class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    role: str
    last_active_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Meetings ─────────────────────────────────────────────────────────────
class AgendaItem(BaseModel):
    title: str
    description: str = ""
    duration_mins: int = 15
    type: str = "discussion"

    def model_dump(self, **kwargs):
        return {"title": self.title, "description": self.description,
                "duration_mins": self.duration_mins, "type": self.type}


class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    scheduled_at: datetime
    duration_minutes: int = Field(60, ge=15, le=480)
    platform: str = "other"
    platform_meeting_id: str | None = None
    platform_join_url: str | None = None
    domain: str | None = None
    tags: list[str] = []
    agenda_items: list[AgendaItem] = []
    participant_emails: list[EmailStr] = []


class MeetingUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = None
    agenda_items: list[AgendaItem] | None = None
    tags: list[str] | None = None


class MeetingListItem(BaseModel):
    id: uuid.UUID
    title: str
    scheduled_at: datetime
    duration_minutes: int
    status: str
    platform: str
    survey_response_count: int
    survey_participant_count: int
    domain: str | None

    model_config = {"from_attributes": True}


class MeetingResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    scheduled_at: datetime
    duration_minutes: int
    platform: str
    status: str
    domain: str | None
    tags: list[str]
    agenda_items: list[Any]
    survey_participant_count: int
    survey_response_count: int
    survey_response_rate: float
    generated_questions: list[Any]
    tension_map: dict | None
    facilitator_brief: str | None
    tension_map_generated_at: datetime | None
    live_session: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Surveys ───────────────────────────────────────────────────────────────
class SurveyQuestion(BaseModel):
    id: str
    text: str
    type: Literal["scale_1_10", "multiple_choice", "open_text", "ranked_choice"]
    options: list[str] | None = None
    include_confidence_rating: bool = False
    rationale: str = ""
    tension_hypothesis: str = ""


class SurveyDesignerOutput(BaseModel):
    questions: list[SurveyQuestion]
    design_rationale: str
    watch_for: list[str]


class SurveyResponseItem(BaseModel):
    question_id: str
    answer: Any
    confidence: int | None = None


class SurveySubmit(BaseModel):
    token: str
    responses: list[SurveyResponseItem]


class SurveySubmitResponse(BaseModel):
    submitted: bool
    can_update_until: datetime | None


class SurveyStatusResponse(BaseModel):
    response_count: int
    participant_count: int
    response_rate: float
    deadline: datetime | None
    meets_threshold: bool


class SurveyGenerateResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    estimated_seconds: int


# ── Tension Map ───────────────────────────────────────────────────────────
class ConsensusArea(BaseModel):
    topic: str
    agreement_score: float
    summary: str
    confidence_average: float
    caveat: str | None = None


class TensionArea(BaseModel):
    topic: str
    tension_score: float
    summary: str
    perspective_a: str
    perspective_b: str
    perspective_c: str | None = None
    why_this_matters: str
    recommended_question: str


class TensionMapOutput(BaseModel):
    consensus_areas: list[ConsensusArea]
    tension_areas: list[TensionArea]
    missing_from_conversation: list[str]
    facilitator_opening_question: str
    watch_list: list[str]
    confidence: float
    confidence_caveat: str | None = None


# ── Live Session ──────────────────────────────────────────────────────────
class SessionStartResponse(BaseModel):
    session_id: uuid.UUID
    started_at: datetime
    websocket_url: str


class SessionSummaryResponse(BaseModel):
    session_id: uuid.UUID
    duration_minutes: int
    speaking_distribution: list[dict]
    alerts_delivered: list[Any]
    decisions_marked: int


# ── Decisions ─────────────────────────────────────────────────────────────
class DecisionOption(BaseModel):
    option: str
    rationale: str = ""
    pros: list[str] = []
    cons: list[str] = []
    was_chosen: bool = False

    def model_dump(self, **kwargs):
        return {"option": self.option, "rationale": self.rationale,
                "pros": self.pros, "cons": self.cons, "was_chosen": self.was_chosen}


class DecisionAssumption(BaseModel):
    assumption: str
    confidence: float = 0.5
    how_to_verify: str = ""
    check_in_question: str = ""

    def model_dump(self, **kwargs):
        return {"assumption": self.assumption, "confidence": self.confidence,
                "how_to_verify": self.how_to_verify, "check_in_question": self.check_in_question}


class DecisionCreate(BaseModel):
    meeting_id: uuid.UUID | None = None
    title: str = Field(..., min_length=1, max_length=500)
    description: str
    domain: str = "other"
    decision_type: str = "other"
    options_considered: list[DecisionOption] = []
    key_assumptions: list[DecisionAssumption] = []
    team_confidence: float | None = Field(None, ge=0.0, le=1.0)


class DecisionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    domain: str | None = None
    decision_type: str | None = None
    options_considered: list[DecisionOption] | None = None
    key_assumptions: list[DecisionAssumption] | None = None
    team_confidence: float | None = None


class DecisionResponse(BaseModel):
    id: uuid.UUID
    meeting_id: uuid.UUID | None
    title: str
    description: str
    domain: str
    decision_type: str
    team_confidence: float | None
    options_considered: list[Any]
    key_assumptions: list[Any]
    dissenting_views: list[Any]
    post_mortem_status: str
    post_mortem_notes: str | None
    check_in_30d_at: datetime | None
    check_in_90d_at: datetime | None
    check_in_180d_at: datetime | None
    created_at: datetime
    outcomes: list[Any]

    model_config = {"from_attributes": True}


class PostMortemSubmit(BaseModel):
    notes: str | None = None
    status: Literal["completed", "skipped"] = "completed"


# ── Outcomes ──────────────────────────────────────────────────────────────
class OutcomeCreate(BaseModel):
    check_in_period: Literal["30d", "90d", "180d", "adhoc"]
    outcome_verdict: Literal["correct", "partially_correct", "incorrect",
                             "too_early_to_tell", "decision_no_longer_relevant"]
    outcome_description: str
    what_we_got_right: str | None = None
    what_we_missed: str | None = None
    key_assumptions_that_failed: list[str] = []
    lessons_learned: str | None = None


# ── Intelligence ──────────────────────────────────────────────────────────
class PatternResponse(BaseModel):
    pattern_id: str
    pattern_name: str
    description: str
    confidence: str
    data_points: int
    severity: float
    recommendation: str


class IntelligenceProfileResponse(BaseModel):
    overall_accuracy_score: float | None
    confidence_calibration_score: float | None
    total_decisions_tracked: int
    decisions_with_outcomes: int
    domain_accuracy: dict
    identified_patterns: list[Any]
    meeting_health: dict
    last_updated: datetime | None


class CalibrationBucket(BaseModel):
    stated_confidence_bucket: str
    actual_accuracy: float
    decisions: int


class CalibrationResponse(BaseModel):
    calibration_curve: list[CalibrationBucket]
    overconfidence_index: float
    interpretation: str
```

---

### 1.3 — First Alembic Migration (THE ACTUAL SQL)

```python
# alembic/versions/001_initial_schema.py
"""Initial database schema with all tables, indexes, RLS, and triggers.

Revision ID: 001
Create Date: 2026-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Enums
    op.execute("""
        CREATE TYPE org_plan AS ENUM ('starter', 'growth', 'enterprise');
        CREATE TYPE user_role AS ENUM ('admin', 'facilitator', 'member');
        CREATE TYPE meeting_status AS ENUM (
            'draft','survey_open','survey_closed','live','ended',
            'post_mortem_pending','post_mortem_done','cancelled'
        );
        CREATE TYPE meeting_platform AS ENUM ('zoom','teams','meet','other');
        CREATE TYPE participant_role AS ENUM ('facilitator','participant');
        CREATE TYPE post_mortem_status AS ENUM ('pending','in_progress','completed','skipped');
        CREATE TYPE decision_type AS ENUM (
            'go_no_go','selection','prioritization','commitment','strategy','process','other'
        );
        CREATE TYPE alert_type AS ENUM (
            'hippo','groupthink','missing_perspective','assumption_blindspot','momentum_trap'
        );
        CREATE TYPE alert_urgency AS ENUM ('low','medium','high');
        CREATE TYPE live_session_status AS ENUM ('active','ended','error');
    """)

    # Organizations
    op.execute("""
        CREATE TABLE organizations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            domain VARCHAR(255),
            plan org_plan NOT NULL DEFAULT 'starter',
            seat_count INTEGER NOT NULL DEFAULT 5,
            stripe_customer_id VARCHAR(255) UNIQUE,
            stripe_sub_id VARCHAR(255) UNIQUE,
            auth0_org_id VARCHAR(255) UNIQUE,
            settings JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX idx_orgs_domain ON organizations(domain) WHERE domain IS NOT NULL;
        CREATE INDEX idx_orgs_stripe ON organizations(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;
    """)

    # Users
    op.execute("""
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            auth0_id VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255) NOT NULL,
            display_name VARCHAR(255),
            role user_role NOT NULL DEFAULT 'member',
            last_active_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(org_id, email)
        );
        CREATE INDEX idx_users_org ON users(org_id);
        CREATE INDEX idx_users_auth0 ON users(auth0_id);
        CREATE INDEX idx_users_email ON users(email);
    """)

    # Meetings
    op.execute("""
        CREATE TABLE meetings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            created_by UUID NOT NULL REFERENCES users(id),
            title VARCHAR(500) NOT NULL,
            description TEXT,
            scheduled_at TIMESTAMPTZ NOT NULL,
            duration_minutes INTEGER NOT NULL DEFAULT 60,
            platform meeting_platform NOT NULL DEFAULT 'other',
            platform_meeting_id VARCHAR(255),
            platform_join_url VARCHAR(2048),
            status meeting_status NOT NULL DEFAULT 'draft',
            calendar_event_id VARCHAR(255),
            calendar_provider VARCHAR(50),
            agenda_items JSONB NOT NULL DEFAULT '[]',
            survey_sent_at TIMESTAMPTZ,
            survey_deadline TIMESTAMPTZ,
            survey_participant_count INTEGER NOT NULL DEFAULT 0,
            survey_response_count INTEGER NOT NULL DEFAULT 0,
            generated_questions JSONB,
            tension_map JSONB,
            tension_map_generated_at TIMESTAMPTZ,
            facilitator_brief TEXT,
            live_session_started_at TIMESTAMPTZ,
            live_session_ended_at TIMESTAMPTZ,
            tags TEXT[] NOT NULL DEFAULT '{}',
            domain VARCHAR(100),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX idx_meetings_org_status ON meetings(org_id, status);
        CREATE INDEX idx_meetings_scheduled ON meetings(scheduled_at);
        CREATE INDEX idx_meetings_platform_id ON meetings(platform, platform_meeting_id)
            WHERE platform_meeting_id IS NOT NULL;
        CREATE INDEX idx_meetings_title_trgm ON meetings USING gin(title gin_trgm_ops);
    """)

    # Meeting Participants
    op.execute("""
        CREATE TABLE meeting_participants (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role participant_role NOT NULL DEFAULT 'participant',
            invited_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            survey_sent_at TIMESTAMPTZ,
            survey_token VARCHAR(255) UNIQUE,
            survey_completed_at TIMESTAMPTZ,
            joined_live_at TIMESTAMPTZ,
            left_live_at TIMESTAMPTZ,
            UNIQUE(meeting_id, user_id)
        );
        CREATE INDEX idx_participants_meeting ON meeting_participants(meeting_id);
        CREATE INDEX idx_participants_user ON meeting_participants(user_id);
        CREATE INDEX idx_participants_token ON meeting_participants(survey_token)
            WHERE survey_token IS NOT NULL;
    """)

    # Survey Responses (ANONYMIZED — no user_id ever)
    op.execute("""
        CREATE TABLE survey_responses (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
            respondent_hash VARCHAR(64) NOT NULL,
            submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            responses JSONB NOT NULL,
            UNIQUE(meeting_id, respondent_hash)
        );
        CREATE INDEX idx_survey_responses_meeting ON survey_responses(meeting_id);
        -- NO index on respondent_hash — intentional for anonymization
    """)

    # Live Meeting Sessions
    op.execute("""
        CREATE TABLE live_meeting_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            meeting_id UUID NOT NULL UNIQUE REFERENCES meetings(id) ON DELETE CASCADE,
            status live_session_status NOT NULL DEFAULT 'active',
            started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ended_at TIMESTAMPTZ,
            total_seconds INTEGER NOT NULL DEFAULT 0,
            speaking_distribution JSONB NOT NULL DEFAULT '{}',
            hippo_events JSONB NOT NULL DEFAULT '[]',
            groupthink_events JSONB NOT NULL DEFAULT '[]',
            missing_perspective_events JSONB NOT NULL DEFAULT '[]',
            total_alerts_delivered INTEGER NOT NULL DEFAULT 0,
            alerts_actioned INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)

    # Transcript Chunks
    op.execute("""
        CREATE TABLE live_transcript_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID NOT NULL REFERENCES live_meeting_sessions(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            start_seconds INTEGER NOT NULL,
            end_seconds INTEGER NOT NULL,
            speaker_hash VARCHAR(32) NOT NULL,
            text TEXT NOT NULL,
            word_count INTEGER,
            embedding_id VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(session_id, chunk_index)
        );
        CREATE INDEX idx_chunks_session ON live_transcript_chunks(session_id, chunk_index);
    """)

    # Intelligence Alerts
    op.execute("""
        CREATE TABLE intelligence_alerts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID NOT NULL REFERENCES live_meeting_sessions(id) ON DELETE CASCADE,
            alert_type alert_type NOT NULL,
            urgency alert_urgency NOT NULL DEFAULT 'medium',
            triggered_at_seconds INTEGER NOT NULL,
            message TEXT NOT NULL,
            suggested_question TEXT,
            internal_reasoning TEXT,
            acknowledged_at TIMESTAMPTZ,
            response VARCHAR(50),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX idx_alerts_session ON intelligence_alerts(session_id);
    """)

    # Decisions
    op.execute("""
        CREATE TABLE decisions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            meeting_id UUID REFERENCES meetings(id) ON DELETE SET NULL,
            created_by UUID NOT NULL REFERENCES users(id),
            title VARCHAR(500) NOT NULL,
            description TEXT NOT NULL,
            domain VARCHAR(100) NOT NULL DEFAULT 'other',
            decision_type decision_type NOT NULL DEFAULT 'other',
            options_considered JSONB NOT NULL DEFAULT '[]',
            key_assumptions JSONB NOT NULL DEFAULT '[]',
            dissenting_views JSONB NOT NULL DEFAULT '[]',
            team_confidence FLOAT,
            post_mortem_status post_mortem_status NOT NULL DEFAULT 'pending',
            post_mortem_notes TEXT,
            post_mortem_completed_at TIMESTAMPTZ,
            check_in_30d_at TIMESTAMPTZ,
            check_in_90d_at TIMESTAMPTZ,
            check_in_180d_at TIMESTAMPTZ,
            check_in_30d_sent BOOLEAN NOT NULL DEFAULT FALSE,
            check_in_90d_sent BOOLEAN NOT NULL DEFAULT FALSE,
            check_in_180d_sent BOOLEAN NOT NULL DEFAULT FALSE,
            embedding_id VARCHAR(255),
            tags TEXT[] NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX idx_decisions_org ON decisions(org_id);
        CREATE INDEX idx_decisions_meeting ON decisions(meeting_id) WHERE meeting_id IS NOT NULL;
        CREATE INDEX idx_decisions_domain ON decisions(org_id, domain);
        CREATE INDEX idx_decisions_checkins ON decisions(check_in_30d_at, check_in_30d_sent)
            WHERE check_in_30d_sent = FALSE;
    """)

    # Decision Outcomes
    op.execute("""
        CREATE TABLE decision_outcomes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            decision_id UUID NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
            recorded_by UUID NOT NULL REFERENCES users(id),
            check_in_period VARCHAR(20) NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            outcome_verdict VARCHAR(50) NOT NULL,
            outcome_description TEXT NOT NULL,
            what_we_got_right TEXT,
            what_we_missed TEXT,
            key_assumptions_that_failed JSONB NOT NULL DEFAULT '[]',
            prediction_accuracy_score FLOAT,
            lessons_learned TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX idx_outcomes_decision ON decision_outcomes(decision_id);
    """)

    # Group Intelligence Profiles
    op.execute("""
        CREATE TABLE group_intelligence_profiles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            org_id UUID NOT NULL UNIQUE REFERENCES organizations(id) ON DELETE CASCADE,
            total_decisions_tracked INTEGER NOT NULL DEFAULT 0,
            decisions_with_outcomes INTEGER NOT NULL DEFAULT 0,
            overall_accuracy_score FLOAT,
            confidence_calibration_score FLOAT,
            identified_patterns JSONB NOT NULL DEFAULT '[]',
            domain_accuracy JSONB NOT NULL DEFAULT '{}',
            avg_survey_response_rate FLOAT,
            avg_speaking_time_gini FLOAT,
            hippo_frequency_score FLOAT,
            groupthink_frequency_score FLOAT,
            recommended_practices JSONB NOT NULL DEFAULT '[]',
            last_pattern_run_at TIMESTAMPTZ,
            last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)

    # Audit Log (append-only)
    op.execute("""
        CREATE TABLE audit_log (
            id BIGSERIAL PRIMARY KEY,
            org_id UUID NOT NULL,
            user_id UUID,
            action VARCHAR(255) NOT NULL,
            resource_type VARCHAR(100) NOT NULL,
            resource_id VARCHAR(255) NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{}',
            ip_address INET,
            user_agent TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX idx_audit_org ON audit_log(org_id, created_at DESC);
        CREATE INDEX idx_audit_resource ON audit_log(resource_type, resource_id);
    """)

    # Notifications
    op.execute("""
        CREATE TABLE notifications (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            org_id UUID NOT NULL,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(500) NOT NULL,
            message TEXT NOT NULL,
            type VARCHAR(100) NOT NULL,
            resource_id VARCHAR(255),
            is_read BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX idx_notifications_user ON notifications(user_id, is_read);
    """)

    # Prompt Versions
    op.execute("""
        CREATE TABLE prompt_versions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            prompt_type VARCHAR(100) NOT NULL,
            version INTEGER NOT NULL,
            content TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT FALSE,
            experiment_traffic_pct FLOAT NOT NULL DEFAULT 0.0,
            avg_quality_score FLOAT,
            avg_latency_ms INTEGER,
            error_rate FLOAT,
            created_by VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(prompt_type, version)
        );
        CREATE INDEX idx_prompt_versions_type ON prompt_versions(prompt_type, is_active);
    """)

    # API Keys
    op.execute("""
        CREATE TABLE api_keys (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            created_by UUID NOT NULL REFERENCES users(id),
            name VARCHAR(255) NOT NULL,
            key_prefix VARCHAR(16) NOT NULL,
            key_hash VARCHAR(255) UNIQUE NOT NULL,
            scopes TEXT[] NOT NULL DEFAULT '{}',
            last_used_at TIMESTAMPTZ,
            expires_at TIMESTAMPTZ,
            revoked_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX idx_api_keys_org ON api_keys(org_id);
        CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
    """)

    # ── ROW LEVEL SECURITY ──────────────────────────────────────────────
    for table in [
        "meetings", "meeting_participants", "survey_responses",
        "live_meeting_sessions", "live_transcript_chunks", "intelligence_alerts",
        "decisions", "decision_outcomes", "users", "notifications",
        "group_intelligence_profiles", "api_keys",
    ]:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    # RLS Policies
    rls_policies = {
        "meetings": "org_id = current_setting('app.current_org_id', TRUE)::UUID",
        "users": "org_id = current_setting('app.current_org_id', TRUE)::UUID",
        "decisions": "org_id = current_setting('app.current_org_id', TRUE)::UUID",
        "notifications": "org_id = current_setting('app.current_org_id', TRUE)::UUID",
        "group_intelligence_profiles": "org_id = current_setting('app.current_org_id', TRUE)::UUID",
        "api_keys": "org_id = current_setting('app.current_org_id', TRUE)::UUID",
        "meeting_participants": """
            meeting_id IN (
                SELECT id FROM meetings
                WHERE org_id = current_setting('app.current_org_id', TRUE)::UUID
            )
        """,
        "survey_responses": """
            meeting_id IN (
                SELECT id FROM meetings
                WHERE org_id = current_setting('app.current_org_id', TRUE)::UUID
            )
        """,
        "live_meeting_sessions": """
            meeting_id IN (
                SELECT id FROM meetings
                WHERE org_id = current_setting('app.current_org_id', TRUE)::UUID
            )
        """,
        "live_transcript_chunks": """
            session_id IN (
                SELECT lms.id FROM live_meeting_sessions lms
                JOIN meetings m ON lms.meeting_id = m.id
                WHERE m.org_id = current_setting('app.current_org_id', TRUE)::UUID
            )
        """,
        "intelligence_alerts": """
            session_id IN (
                SELECT lms.id FROM live_meeting_sessions lms
                JOIN meetings m ON lms.meeting_id = m.id
                WHERE m.org_id = current_setting('app.current_org_id', TRUE)::UUID
            )
        """,
        "decision_outcomes": """
            decision_id IN (
                SELECT id FROM decisions
                WHERE org_id = current_setting('app.current_org_id', TRUE)::UUID
            )
        """,
    }
    for table, policy in rls_policies.items():
        op.execute(f"""
            CREATE POLICY {table}_org_isolation ON {table}
                USING ({policy})
        """)

    # ── AUTO-TRIGGERS ───────────────────────────────────────────────────
    op.execute("""
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

        CREATE TRIGGER trg_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();

        -- Auto-update survey response count
        CREATE OR REPLACE FUNCTION update_survey_response_count()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                UPDATE meetings SET survey_response_count = survey_response_count + 1
                WHERE id = NEW.meeting_id;
            ELSIF TG_OP = 'DELETE' THEN
                UPDATE meetings SET survey_response_count = survey_response_count - 1
                WHERE id = OLD.meeting_id;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_survey_response_count
            AFTER INSERT OR DELETE ON survey_responses
            FOR EACH ROW EXECUTE FUNCTION update_survey_response_count();

        -- Auto-set decision check-in dates
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

        -- Auto-compute prediction accuracy from verdict
        CREATE OR REPLACE FUNCTION set_prediction_accuracy()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.prediction_accuracy_score = CASE NEW.outcome_verdict
                WHEN 'correct' THEN 1.0
                WHEN 'partially_correct' THEN 0.5
                WHEN 'incorrect' THEN 0.0
                ELSE NULL
            END;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_outcome_accuracy
            BEFORE INSERT OR UPDATE ON decision_outcomes
            FOR EACH ROW EXECUTE FUNCTION set_prediction_accuracy();
    """)

    # Revoke UPDATE/DELETE on audit_log from app user
    # (run after app user exists in production)
    # op.execute("REVOKE UPDATE, DELETE ON audit_log FROM quorum_app")


def downgrade() -> None:
    tables = [
        "api_keys", "prompt_versions", "notifications", "audit_log",
        "group_intelligence_profiles", "decision_outcomes", "decisions",
        "intelligence_alerts", "live_transcript_chunks", "live_meeting_sessions",
        "survey_responses", "meeting_participants", "meetings", "users", "organizations"
    ]
    for table in tables:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

    op.execute("""
        DROP TYPE IF EXISTS org_plan CASCADE;
        DROP TYPE IF EXISTS user_role CASCADE;
        DROP TYPE IF EXISTS meeting_status CASCADE;
        DROP TYPE IF EXISTS meeting_platform CASCADE;
        DROP TYPE IF EXISTS participant_role CASCADE;
        DROP TYPE IF EXISTS post_mortem_status CASCADE;
        DROP TYPE IF EXISTS decision_type CASCADE;
        DROP TYPE IF EXISTS alert_type CASCADE;
        DROP TYPE IF EXISTS alert_urgency CASCADE;
        DROP TYPE IF EXISTS live_session_status CASCADE;
    """)
```

---

### 1.4 — Fixed `app/main.py` (Bug Fixes + Production-Ready)

```python
# KEY FIXES FROM AUDIT:
# 1. await conn.execute("SELECT 1") → await conn.execute(text("SELECT 1"))
# 2. _scrub_sensitive_data moved before sentry_sdk.init (forward reference fix)
# 3. Proper lifespan for Redis connection pool
# 4. Rate limiting middleware added
# 5. Security headers middleware added

from sqlalchemy import text  # ADD THIS IMPORT
# In _add_health_check:
async with engine.begin() as conn:
    await conn.execute(text("SELECT 1"))  # FIX: was "SELECT 1" (string)
```

---

### 1.5 — Fixed `app/services/stt_service.py` (Critical Bug: Duplicate Method + Wrong Task Init)

```python
# REPLACE the entire stt_service.py with this fixed version:

class MeetingStreamProcessor:
    def __init__(self, session_id: str, meeting_id: str, tension_map: dict | None = None):
        self.session_id = session_id
        self.meeting_id = meeting_id
        self.tension_map = tension_map or {}
        self.transcript_buffer: collections.deque = collections.deque(maxlen=200)
        self.speaking_seconds: dict[str, int] = {}
        self.total_seconds = 0
        self.session_active = False
        self.alerts_delivered: list[dict] = []
        self.hippo_alerts_count = 0
        self.mp_alerts_count = 0
        self.chunk_index = 0
        self.scheduled_duration_seconds = 3600
        self._eval_task: asyncio.Task | None = None  # declare but don't create

    async def start(self):
        self.session_active = True
        # Create task AFTER setting session_active=True
        self._eval_task = asyncio.create_task(self._intelligence_evaluation_loop())

    async def _intelligence_evaluation_loop(self):
        """Single definition — no duplicates."""
        while self.session_active:
            await asyncio.sleep(30)
            if self.total_seconds < 300:
                continue
            alert = await self._evaluate()
            if alert and alert.get("action") == "intervene":
                await self._deliver_alert(alert)

    async def end(self):
        self.session_active = False
        if self._eval_task and not self._eval_task.done():
            self._eval_task.cancel()
            try:
                await self._eval_task
            except asyncio.CancelledError:
                pass
        self._eval_task = None
```

---

### 1.6 — Missing `app/settings.py` Fix: Add `APP_URL`

```python
# In app/core/config.py, add to Settings class:
APP_URL: str = "https://app.quorum.ai"

# Also add display_name to CurrentUser in app/api/auth.py:
class CurrentUser:
    def __init__(self, user_id: uuid.UUID, org_id: uuid.UUID, email: str, role: str,
                 display_name: str | None = None):
        self.user_id = user_id
        self.org_id = org_id
        self.email = email
        self.role = role
        self.display_name = display_name or email.split("@")[0].capitalize()
```

---

### 1.7 — Auth0 Next.js Routes (Missing `/auth/` endpoints)

```typescript
// src/app/auth/login/route.ts
import { auth0 } from "@/lib/auth0";
export const GET = auth0.handlers.GET;

// src/app/auth/logout/route.ts
import { auth0 } from "@/lib/auth0";
export const GET = auth0.handlers.GET;

// src/app/auth/callback/route.ts
import { auth0 } from "@/lib/auth0";
export const GET = auth0.handlers.GET;

// src/app/auth/access-token/route.ts
import { auth0 } from "@/lib/auth0";
import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  try {
    const session = await auth0.getSession();
    if (!session?.tokenSet?.accessToken) {
      return NextResponse.json({ error: "No session" }, { status: 401 });
    }
    return NextResponse.json({ token: session.tokenSet.accessToken });
  } catch {
    return NextResponse.json({ error: "Failed to get token" }, { status: 500 });
  }
}
```

---

### 1.8 — Celery Task Implementations (Currently Stubs)

```python
# app/workers/tasks/send_outcome_checkins.py
"""
Celery task: send 30/90/180-day outcome check-in emails.
Runs daily at 09:00 UTC via Celery Beat.
"""
from datetime import datetime, timedelta, UTC
from app.workers.celery_app import celery_app
from app.core.database import async_session_factory
from app.models.models import Decision, Organization, User
from app.services.email_service import email_service
import asyncio
import logging
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.send_outcome_checkins", bind=True, max_retries=3)
def send_outcome_checkins(self):
    """Find all decisions with due check-ins and send emails."""
    asyncio.run(_send_outcome_checkins_async())


async def _send_outcome_checkins_async():
    now = datetime.now(UTC).replace(tzinfo=None)
    tomorrow = now + timedelta(days=1)

    async with async_session_factory() as db:
        # 30-day check-ins due
        result_30 = await db.execute(
            select(Decision)
            .where(
                and_(
                    Decision.check_in_30d_at <= tomorrow,
                    Decision.check_in_30d_at >= now - timedelta(days=1),
                    Decision.check_in_30d_sent == False,
                )
            )
        )
        decisions_30 = result_30.scalars().all()

        for decision in decisions_30:
            await _send_checkin_for_decision(db, decision, "30d")
            decision.check_in_30d_sent = True

        # 90-day check-ins due
        result_90 = await db.execute(
            select(Decision).where(
                and_(
                    Decision.check_in_90d_at <= tomorrow,
                    Decision.check_in_90d_at >= now - timedelta(days=1),
                    Decision.check_in_90d_sent == False,
                )
            )
        )
        for decision in result_90.scalars().all():
            await _send_checkin_for_decision(db, decision, "90d")
            decision.check_in_90d_sent = True

        # 180-day check-ins due
        result_180 = await db.execute(
            select(Decision).where(
                and_(
                    Decision.check_in_180d_at <= tomorrow,
                    Decision.check_in_180d_at >= now - timedelta(days=1),
                    Decision.check_in_180d_sent == False,
                )
            )
        )
        for decision in result_180.scalars().all():
            await _send_checkin_for_decision(db, decision, "180d")
            decision.check_in_180d_sent = True

        await db.commit()
        logger.info("Outcome check-in emails sent successfully")


async def _send_checkin_for_decision(db, decision: Decision, period: str):
    """Send check-in email to the decision creator."""
    from app.core.config import get_settings
    settings = get_settings()

    creator_q = await db.execute(select(User).where(User.id == decision.created_by))
    creator = creator_q.scalar_one_or_none()
    if not creator:
        return

    assumptions = [
        a.get("assumption", "") if isinstance(a, dict) else str(a)
        for a in (decision.key_assumptions or [])
    ]
    checkin_url = f"{settings.APP_URL}/decisions/{decision.id}?checkin={period}"

    await email_service.send_outcome_checkin(
        to_email=creator.email,
        decision_title=decision.title,
        check_in_period=period,
        checkin_url=checkin_url,
        key_assumptions=assumptions[:5],  # cap at 5 for email readability
    )
    logger.info(f"Sent {period} check-in for decision {decision.id} to {creator.email}")


# app/workers/tasks/run_pattern_detector.py
"""
Celery task: weekly pattern detector via LangGraph.
Runs Sunday 03:00 UTC via Celery Beat.
"""
from app.workers.celery_app import celery_app
from app.core.database import async_session_factory
from app.models.models import Decision, GroupIntelligenceProfile, Organization
from app.intelligence.agents.factory import AgentFactory
from app.core.security import utc_now
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import asyncio
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.run_pattern_detector", bind=True, max_retries=2)
def run_pattern_detector(self):
    """Run weekly pattern detection for all organizations."""
    asyncio.run(_run_pattern_detector_async())


async def _run_pattern_detector_async():
    async with async_session_factory() as db:
        orgs_result = await db.execute(select(Organization))
        orgs = orgs_result.scalars().all()

        for org in orgs:
            try:
                await _detect_patterns_for_org(db, org.id)
                logger.info(f"Pattern detection complete for org {org.id}")
            except Exception as e:
                logger.error(f"Pattern detection failed for org {org.id}: {e}")


async def _detect_patterns_for_org(db, org_id):
    decisions_q = await db.execute(
        select(Decision)
        .options(selectinload(Decision.outcomes))
        .where(Decision.org_id == org_id)
    )
    decisions = decisions_q.scalars().all()

    if len(decisions) < 5:
        logger.info(f"Skipping org {org_id}: only {len(decisions)} decisions")
        return

    decisions_data = [
        {
            "id": str(d.id),
            "title": d.title,
            "domain": d.domain,
            "team_confidence": d.team_confidence,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "key_assumptions": d.key_assumptions or [],
            "outcomes": [
                {
                    "outcome_verdict": o.outcome_verdict,
                    "prediction_accuracy_score": o.prediction_accuracy_score,
                }
                for o in (d.outcomes or [])
            ],
        }
        for d in decisions
    ]

    profile_q = await db.execute(
        select(GroupIntelligenceProfile).where(GroupIntelligenceProfile.org_id == org_id)
    )
    profile = profile_q.scalar_one_or_none()

    if not profile:
        profile = GroupIntelligenceProfile(org_id=org_id)
        db.add(profile)
        await db.flush()

    agent = AgentFactory.get_pattern_detector()
    patterns = await agent.detect(decisions_data, profile.identified_patterns)

    if patterns:
        profile.identified_patterns = patterns

    profile.last_pattern_run_at = utc_now()
    profile.last_updated = utc_now()
    await db.commit()
```

---

### 1.9 — Celery App Configuration

```python
# app/workers/celery_app.py
"""Celery application factory with beat schedule."""
from celery import Celery
from celery.schedules import crontab
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "quorum",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.tasks.send_outcome_checkins",
        "app.workers.tasks.run_pattern_detector",
        "app.workers.tasks.cleanup_expired_data",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    beat_schedule={
        "send-outcome-checkins-daily": {
            "task": "tasks.send_outcome_checkins",
            "schedule": crontab(hour=9, minute=0),
        },
        "run-pattern-detector-weekly": {
            "task": "tasks.run_pattern_detector",
            "schedule": crontab(hour=3, minute=0, day_of_week=0),
        },
        "cleanup-expired-audio-daily": {
            "task": "tasks.cleanup_expired_data",
            "schedule": crontab(hour=2, minute=0),
        },
    },
    task_routes={
        "tasks.send_outcome_checkins": {"queue": "scheduled"},
        "tasks.run_pattern_detector": {"queue": "scheduled"},
        "tasks.cleanup_expired_data": {"queue": "scheduled"},
        "tasks.generate_tension_map": {"queue": "high-priority"},
        "tasks.send_survey_invitations": {"queue": "high-priority"},
    },
)
```

---

### 1.10 — Secure WebSocket Authentication Fix

```python
# FIX in app/api/routers/sessions.py:
# BEFORE (insecure — token in URL query param):
@router.websocket("/stream")
async def websocket_stream(websocket: WebSocket, meeting_id: str):
    token = websocket.query_params.get("token")  # ← visible in server logs

# AFTER (secure — token in first message):
@router.websocket("/stream")
async def websocket_stream(websocket: WebSocket, meeting_id: str):
    await websocket.accept()

    # Expect auth message as FIRST message within 10 seconds
    try:
        auth_data = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
    except asyncio.TimeoutError:
        await websocket.close(code=4401, reason="Auth timeout")
        return

    if auth_data.get("type") != "auth":
        await websocket.close(code=4401, reason="Expected auth message first")
        return

    token = auth_data.get("token")
    if not token:
        await websocket.close(code=4401, reason="Missing token in auth message")
        return

    # ... rest of auth verification unchanged

# FRONTEND UPDATE (src/lib/api.ts — WebSocket connection):
function connectWebSocket(meetingId: string, token: string): WebSocket {
    const wsBase = getWebSocketBaseUrl();
    const ws = new WebSocket(`${wsBase}/api/v1/meetings/${meetingId}/session/stream`);

    ws.onopen = () => {
        // Send auth as first message instead of query param
        ws.send(JSON.stringify({ type: "auth", token }));
    };
    return ws;
}
```

---

## PART 2 — SCALABLE FEATURES MISSING FROM SPECIFICATION

### 2.1 — Rate Limiting Middleware (Currently Config Only, Not Implemented)

```python
# app/api/middleware/rate_limiter.py
"""
Token bucket rate limiter using Redis.
Replaces nginx-only rate limiting with application-level granularity.
"""
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import redis.asyncio as aioredis
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

RATE_LIMITS = {
    "/api/v1/meetings/{id}/survey/respond": (10, 60),   # 10/min (anonymous)
    "/api/v1/meetings/{id}/survey/generate": (10, 60),  # 10/min per org
    "default_starter": (100, 60),
    "default_growth": (500, 60),
    "default_enterprise": (2000, 60),
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_url: str):
        super().__init__(app)
        self.redis_url = redis_url
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = await aioredis.from_url(self.redis_url, encoding="utf-8")
        return self._redis

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health check and docs
        if request.url.path in ("/health", "/docs", "/openapi.json"):
            return await call_next(request)

        try:
            redis = await self._get_redis()
            identifier = self._get_identifier(request)
            limit, window = self._get_limit(request)

            key = f"quorum:ratelimit:{identifier}:{request.url.path}"
            current = await redis.incr(key)
            if current == 1:
                await redis.expire(key, window)

            remaining = max(0, limit - current)

            if current > limit:
                return JSONResponse(
                    status_code=429,
                    content={"error": "rate_limit_exceeded",
                             "message": "Too many requests. Please slow down."},
                    headers={
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "Retry-After": str(window),
                    }
                )

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            return response

        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            return await call_next(request)  # fail open

    def _get_identifier(self, request: Request) -> str:
        # Use org_id from token if available, else IP
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            # Use first 16 chars of token as identifier (hashed later)
            return f"token:{auth[7:23]}"
        return f"ip:{request.client.host if request.client else 'unknown'}"

    def _get_limit(self, request: Request) -> tuple[int, int]:
        path = request.url.path
        if "survey/respond" in path:
            return (10, 60)
        if "survey/generate" in path or "tension-map" in path:
            return (10, 60)
        return (100, 60)  # default starter tier
```

---

### 2.2 — Security Headers Middleware

```python
# app/api/middleware/security_headers.py
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        # CSP - tightened for production
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "connect-src 'self' wss://api.quorum.ai https://api.quorum.ai; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline';"
        )
        return response
```

---

### 2.3 — Decision Embedding on Creation (Currently Skipped)

```python
# Add to app/api/routers/decisions.py after decision is committed:
async def _embed_and_store_decision(decision: Decision, db: AsyncSession) -> None:
    """Background task: embed decision and store in Pinecone for semantic search."""
    from app.services.embedding_service import embedding_service
    from app.services.pinecone_service import pinecone_service

    try:
        text = f"{decision.title}. {decision.description}. Domain: {decision.domain}."
        if decision.key_assumptions:
            assumptions_text = " ".join(
                a.get("assumption", "") if isinstance(a, dict) else str(a)
                for a in decision.key_assumptions[:5]
            )
            text += f" Key assumptions: {assumptions_text}"

        embedding = await embedding_service.embed_one(text)

        metadata = {
            "org_id": str(decision.org_id),
            "domain": decision.domain,
            "title": decision.title,
            "decision_type": decision.decision_type.value
                if hasattr(decision.decision_type, "value") else decision.decision_type,
            "team_confidence": decision.team_confidence or 0,
            "created_at": decision.created_at.isoformat(),
        }

        success = await pinecone_service.upsert_decision(decision.id, embedding, metadata)
        if success:
            decision.embedding_id = str(decision.id)
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to embed decision {decision.id}: {e}")
        # Non-fatal — semantic search won't work for this decision

# In create_decision endpoint, add background task:
# from fastapi import BackgroundTasks
# background_tasks.add_task(_embed_and_store_decision, decision, db)
```

---

### 2.4 — Structured Logging Request Correlation

```python
# app/api/middleware/request_context.py
"""
Attach structured logging context to every request.
Ensures all log lines in a request share the same request_id and org_id.
"""
import uuid
import structlog
from starlette.middleware.base import BaseHTTPMiddleware

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        with structlog.contextvars.bound_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        ):
            import time
            start = time.perf_counter()
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start) * 1000, 2)

            structlog.get_logger().info(
                "http.request_complete",
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

            response.headers["X-Request-ID"] = request_id
            return response
```

---

### 2.5 — Database Connection Pool Monitoring

```python
# Add to app/main.py health check:
@app.get("/health/detailed", include_in_schema=False)
async def detailed_health():
    """Detailed health for internal monitoring — not exposed externally."""
    from sqlalchemy import text
    checks = {}

    # DB pool stats
    pool = engine.pool
    checks["db"] = {
        "status": "ok",
        "pool_size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "checked_in": pool.checkedin(),
    }

    # Redis
    try:
        r = aioredis.from_url(settings.REDIS_URL)
        info = await r.info("memory")
        checks["redis"] = {
            "status": "ok",
            "used_memory_mb": round(info["used_memory"] / 1024 / 1024, 2),
            "connected_clients": info.get("connected_clients"),
        }
        await r.aclose()
    except Exception as e:
        checks["redis"] = {"status": "error", "error": str(e)}

    return checks
```

---

### 2.6 — Stripe Webhook Handler (Currently Just Logs)

```python
# app/api/routers/webhooks.py — Full implementation:
@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    event = _verify_stripe_event(payload, sig_header)
    if settings.STRIPE_WEBHOOK_SECRET and event is None:
        return Response(content="Invalid signature", status_code=400)

    event_type = event["type"] if event else "unverified"

    if event_type == "customer.subscription.created":
        await _handle_subscription_created(db, event["data"]["object"])
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(db, event["data"]["object"])
    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(db, event["data"]["object"])
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(db, event["data"]["object"])

    return {"acknowledged": True, "event_type": event_type}


async def _handle_subscription_created(db, subscription):
    """Update org plan based on Stripe price."""
    from app.models.models import Organization
    customer_id = subscription["customer"]
    result = await db.execute(
        select(Organization).where(Organization.stripe_customer_id == customer_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        logger.warning(f"No org found for Stripe customer {customer_id}")
        return

    org.stripe_sub_id = subscription["id"]
    # Map price to plan (configure these price IDs in settings)
    price_id = subscription["items"]["data"][0]["price"]["id"]
    if "growth" in price_id.lower():
        org.plan = OrgPlan.GROWTH
    elif "enterprise" in price_id.lower():
        org.plan = OrgPlan.ENTERPRISE
    else:
        org.plan = OrgPlan.STARTER

    await db.commit()
    logger.info(f"Subscription created for org {org.id}, plan={org.plan}")


async def _handle_subscription_deleted(db, subscription):
    """Downgrade to starter on cancellation."""
    from app.models.models import Organization, OrgPlan
    result = await db.execute(
        select(Organization).where(Organization.stripe_sub_id == subscription["id"])
    )
    org = result.scalar_one_or_none()
    if org:
        org.plan = OrgPlan.STARTER
        org.stripe_sub_id = None
        await db.commit()


async def _handle_payment_failed(db, invoice):
    """Send alert on payment failure — don't immediately revoke access."""
    logger.error(f"Payment failed for customer {invoice['customer']}: {invoice['id']}")
    # TODO: Send email via SendGrid, flag account in Datadog
```

---

### 2.7 — Datadog Custom Metrics Integration

```python
# app/core/metrics.py
"""
Custom business metrics for Datadog.
Reports: surveys sent, tension maps generated, alerts delivered, decisions tracked.
"""
import logging
from functools import wraps
from typing import Callable

logger = logging.getLogger(__name__)


class QuorumMetrics:
    """Thin wrapper around Datadog statsd client."""

    def __init__(self):
        self._client = None
        self._initialized = False

    def _get_client(self):
        if self._initialized:
            return self._client
        try:
            from datadog import initialize, statsd
            from app.core.config import get_settings
            settings = get_settings()
            if settings.DATADOG_API_KEY:
                initialize(api_key=settings.DATADOG_API_KEY)
                self._client = statsd
            self._initialized = True
        except ImportError:
            logger.warning("Datadog not installed, metrics disabled")
        return self._client

    def increment(self, metric: str, tags: list[str] | None = None, value: int = 1):
        client = self._get_client()
        if client:
            try:
                client.increment(f"quorum.{metric}", value, tags=tags or [])
            except Exception as e:
                logger.debug(f"Metrics error: {e}")

    def gauge(self, metric: str, value: float, tags: list[str] | None = None):
        client = self._get_client()
        if client:
            try:
                client.gauge(f"quorum.{metric}", value, tags=tags or [])
            except Exception as e:
                logger.debug(f"Metrics error: {e}")

    def timing(self, metric: str, value_ms: float, tags: list[str] | None = None):
        client = self._get_client()
        if client:
            try:
                client.timing(f"quorum.{metric}", value_ms, tags=tags or [])
            except Exception as e:
                logger.debug(f"Metrics error: {e}")


metrics = QuorumMetrics()

# Usage in routers:
# metrics.increment("surveys.sent", tags=[f"org:{org_id}", f"platform:{platform}"])
# metrics.increment("tension_maps.generated", tags=[f"org:{org_id}"])
# metrics.increment("intelligence_alerts.delivered", tags=[f"type:{alert_type}"])
# metrics.timing("llm.latency", duration_ms, tags=[f"agent:{agent_name}"])
```

---

### 2.8 — Idempotent Survey Submission (Prevent Double-Count on Network Retry)

```python
# Add to app/api/routers/surveys.py:
# The UNIQUE(meeting_id, respondent_hash) constraint handles this at DB level.
# But we need to return 200 (not 201) on update, and the right can_update_until.

@router.post("/respond", status_code=201)
async def submit_response(meeting_id: UUID, data: SurveySubmit, db: AsyncSession = Depends(get_db)):
    # ... existing validation ...

    existing = existing_q.scalar_one_or_none()
    is_update = existing is not None

    if existing:
        existing.responses = [r.model_dump() for r in data.responses]
        existing.updated_at = utc_now()
        # Don't increment survey_response_count on update
    else:
        db.add(SurveyResponse(...))
        meeting.survey_response_count += 1

    participant.survey_completed_at = utc_now()
    await db.commit()

    # Return 200 for updates, 201 for first submission
    # (FastAPI doesn't easily change status_code per-response,
    #  so use Response with explicit status_code)
    from fastapi.responses import JSONResponse
    status = 200 if is_update else 201
    return JSONResponse(
        status_code=status,
        content=SurveySubmitResponse(
            submitted=True,
            can_update_until=meeting.survey_deadline
        ).model_dump(mode="json"),
    )
```

---

## PART 3 — TESTING INFRASTRUCTURE (From Zero to 80%+ Coverage)

### 3.1 — `tests/conftest.py` (The Missing Foundation)

```python
"""
tests/conftest.py — Test fixtures, DB setup, and factory-boy factories.
ALL integration tests depend on this file.
"""
import asyncio
import uuid
from datetime import datetime, timedelta, UTC
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import app
from app.models.models import (
    Decision, Meeting, MeetingParticipant, MeetingPlatform, MeetingStatus,
    Organization, OrgPlan, ParticipantRole, User, UserRole,
)
from app.core.security import generate_survey_token, utc_now
from app.core.jwt_utils import encode_jwt

TEST_DATABASE_URL = "postgresql+asyncpg://quorum_test:quorum_test@localhost:5432/quorum_test"


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Each test gets a fresh session that's rolled back after."""
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


def create_test_jwt(user: User, settings_secret: str = "test-secret-key-32-characters-min") -> str:
    """Create a valid test JWT token."""
    payload = {
        "type": "dev_access",
        "sub": str(user.id),
        "org_id": str(user.org_id),
        "email": user.email,
        "role": user.role.value,
        "iat": datetime.now(UTC).timestamp(),
        "exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp(),
    }
    return encode_jwt(payload, settings_secret)


# ── Fixture Factories ──────────────────────────────────────────────────
@pytest_asyncio.fixture
async def org(db_session: AsyncSession) -> Organization:
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        domain="testorg.com",
        plan=OrgPlan.GROWTH,
        seat_count=25,
        settings={"ai_context": "Test B2B SaaS company", "min_survey_response_rate": 0.5},
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession, org: Organization) -> User:
    user = User(
        id=uuid.uuid4(),
        org_id=org.id,
        auth0_id=f"dev|admin-{uuid.uuid4()}",
        email="admin@testorg.com",
        display_name="Admin User",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def facilitator(db_session: AsyncSession, org: Organization) -> User:
    user = User(
        id=uuid.uuid4(),
        org_id=org.id,
        auth0_id=f"dev|facilitator-{uuid.uuid4()}",
        email="facilitator@testorg.com",
        display_name="Facilitator User",
        role=UserRole.FACILITATOR,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def meeting_with_survey(db_session: AsyncSession, org: Organization, facilitator: User) -> Meeting:
    """A meeting with 5 participants, all with survey tokens."""
    meeting = Meeting(
        id=uuid.uuid4(),
        org_id=org.id,
        created_by=facilitator.id,
        title="Q3 Roadmap Decision",
        description="Deciding features for Q3",
        scheduled_at=datetime.now(UTC) + timedelta(days=1),
        duration_minutes=60,
        platform=MeetingPlatform.ZOOM,
        status=MeetingStatus.SURVEY_OPEN,
        agenda_items=[{"title": "Review options", "duration_mins": 30}],
        survey_participant_count=5,
        generated_questions=[
            {
                "id": "q1", "text": "How confident are you in the timeline?",
                "type": "scale_1_10", "include_confidence_rating": True,
                "tension_hypothesis": "Timeline skepticism",
            },
            {
                "id": "q2",
                "text": "What are you worried nobody will say about the Q3 plan?",
                "type": "open_text", "include_confidence_rating": False,
                "tension_hypothesis": "Hidden concerns",
            },
            {
                "id": "q3",
                "text": "What would change your mind about prioritizing feature X?",
                "type": "open_text", "include_confidence_rating": False,
                "tension_hypothesis": "Falsifiability test",
            },
            {
                "id": "q4", "text": "Which resource is most at risk?",
                "type": "multiple_choice",
                "options": ["Engineering", "Design", "QA", "PM"],
                "include_confidence_rating": True,
                "tension_hypothesis": "Resource allocation",
            },
        ],
    )
    db_session.add(meeting)
    await db_session.flush()

    # Create 5 participant users with tokens
    participants = []
    for i in range(5):
        user = User(
            id=uuid.uuid4(),
            org_id=org.id,
            auth0_id=f"dev|participant-{i}-{uuid.uuid4()}",
            email=f"participant{i}@testorg.com",
            display_name=f"Participant {i}",
            role=UserRole.MEMBER,
        )
        db_session.add(user)
        await db_session.flush()

        role = ParticipantRole.FACILITATOR if i == 0 else ParticipantRole.PARTICIPANT
        participant = MeetingParticipant(
            id=uuid.uuid4(),
            meeting_id=meeting.id,
            user_id=user.id,
            role=role,
            survey_token=generate_survey_token(),
        )
        db_session.add(participant)
        participants.append((user, participant))

    await db_session.flush()
    meeting._test_participants = participants  # attach for test access
    return meeting


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, facilitator: User) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client authenticated as facilitator."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    token = create_test_jwt(facilitator)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as c:
        yield c

    app.dependency_overrides.clear()
```

---

### 3.2 — `tests/unit/test_anonymization.py` (The Required Adversarial Suite)

```python
"""
tests/unit/test_anonymization.py — Adversarial anonymization tests.
These MUST all pass. They simulate an attacker with full DB access.
"""
import hashlib
import hmac
import pytest
from unittest.mock import patch

from app.core.security import anonymize_respondent, anonymize_speaker, verify_survey_token

FAKE_SECRET = "test-respondent-secret-32chars-min"
FAKE_SPEAKER_SECRET = "test-speaker-secret-32chars-min"


class TestRespondentAnonymization:
    def test_same_user_same_meeting_produces_same_hash(self):
        h1 = anonymize_respondent("user-123", "meeting-456")
        h2 = anonymize_respondent("user-123", "meeting-456")
        assert h1 == h2, "Must be deterministic"

    def test_same_user_different_meetings_produce_different_hashes(self):
        h1 = anonymize_respondent("user-123", "meeting-001")
        h2 = anonymize_respondent("user-123", "meeting-002")
        assert h1 != h2, "Meeting-scoping must prevent cross-meeting correlation"

    def test_different_users_same_meeting_produce_different_hashes(self):
        h1 = anonymize_respondent("user-001", "meeting-456")
        h2 = anonymize_respondent("user-002", "meeting-456")
        assert h1 != h2, "Different users must produce different hashes"

    def test_hash_length_is_fixed_regardless_of_input_length(self):
        h1 = anonymize_respondent("u", "m")
        h2 = anonymize_respondent("user-" + "x" * 100, "meeting-" + "y" * 100)
        assert len(h1) == len(h2), "Hash length must not leak input length"
        assert len(h1) == 20, "Expected 20-char truncated hash"

    def test_cannot_brute_force_with_known_user_list_and_wrong_secret(self):
        """Simulate attacker with full user list but no secret."""
        user_ids = [f"user-{i}" for i in range(1000)]
        meeting_id = "meeting-456"
        real_hash = anonymize_respondent("user-42", meeting_id)

        wrong_secret = "wrong-secret-not-the-real-one"
        attacker_matches = []
        for uid in user_ids:
            attacker_hash = hmac.new(
                wrong_secret.encode(),
                f"{uid}:{meeting_id}".encode(),
                hashlib.sha256,
            ).hexdigest()[:20]
            if attacker_hash == real_hash:
                attacker_matches.append(uid)

        assert len(attacker_matches) == 0, "Attacker should not match without the real secret"

    def test_hash_not_present_in_log_output(self, caplog):
        """Ensure user_id never appears in application log output."""
        import logging
        sensitive_user_id = "super-secret-user-id-should-not-log"
        with caplog.at_level(logging.DEBUG):
            anonymize_respondent(sensitive_user_id, "meeting-test")
        assert sensitive_user_id not in caplog.text, "User ID must not appear in logs"

    def test_two_hashes_from_different_meetings_are_uncorrelatable(self):
        """Verify no pattern across meeting hashes."""
        hash_m1 = anonymize_respondent("user-123", "meeting-001")
        hash_m2 = anonymize_respondent("user-123", "meeting-002")
        assert hash_m1 != hash_m2
        # First 4 chars differ (basic entropy check — not a guarantee but sanity)
        # This will occasionally fail with very low probability — acceptable
        # assert hash_m1[:4] != hash_m2[:4]  # too strict, remove

    def test_empty_inputs_produce_valid_hash(self):
        """Edge case: empty strings should not crash."""
        h = anonymize_respondent("", "")
        assert isinstance(h, str)
        assert len(h) == 20


class TestSpeakerAnonymization:
    def test_same_platform_id_different_meetings_produce_different_hashes(self):
        h1 = anonymize_speaker("zoom_user_abc", "meeting-001")
        h2 = anonymize_speaker("zoom_user_abc", "meeting-002")
        assert h1 != h2

    def test_hash_length_is_16(self):
        h = anonymize_speaker("any_user", "any_meeting")
        assert len(h) == 16


class TestSurveyTokenVerification:
    def test_valid_token_returns_true(self):
        assert verify_survey_token("abc123", "abc123") is True

    def test_wrong_token_returns_false(self):
        assert verify_survey_token("wrong", "abc123") is False

    def test_none_db_token_returns_false(self):
        assert verify_survey_token("abc123", None) is False

    def test_empty_token_returns_false(self):
        assert verify_survey_token("", "abc123") is False
```

---

### 3.3 — `tests/unit/test_detection_algorithms.py`

```python
"""
tests/unit/test_detection_algorithms.py — HiPPO and groupthink detection tests.
"""
import pytest
from collections import deque
from app.intelligence.agents.live_agent import detect_hippo, groupthink_precheck


class TestHiPPODetector:
    def test_no_alert_before_5_minutes(self):
        speaking = {"hash_a": 200, "hash_b": 10}
        result = detect_hippo(speaking, total_seconds=210, elapsed_seconds=200, hippo_alerts_delivered=0)
        assert result is None, "Must not alert before 5-minute minimum"

    def test_alert_fires_above_45_percent_threshold(self):
        speaking = {"hash_a": 460, "hash_b": 100, "hash_c": 80, "hash_d": 60}
        total = sum(speaking.values())  # 700
        # hash_a = 65.7% — well above 45%
        result = detect_hippo(speaking, total_seconds=total, elapsed_seconds=600, hippo_alerts_delivered=0)
        assert result is not None
        assert result.type == "hippo"
        assert result.urgency == "high"

    def test_medium_urgency_between_38_and_45_percent(self):
        speaking = {"hash_a": 165, "hash_b": 100, "hash_c": 90, "hash_d": 70}
        total = sum(speaking.values())  # 425; hash_a = 38.8%
        result = detect_hippo(speaking, total_seconds=total, elapsed_seconds=600, hippo_alerts_delivered=0)
        assert result is not None
        assert result.urgency == "medium"

    def test_no_alert_below_38_percent(self):
        speaking = {"hash_a": 150, "hash_b": 130, "hash_c": 120, "hash_d": 100}
        total = sum(speaking.values())  # 500; hash_a = 30%
        result = detect_hippo(speaking, total_seconds=total, elapsed_seconds=600, hippo_alerts_delivered=0)
        assert result is None

    def test_caps_at_2_alerts_per_meeting(self):
        speaking = {"hash_a": 900, "hash_b": 100}
        result = detect_hippo(speaking, total_seconds=1000, elapsed_seconds=600, hippo_alerts_delivered=2)
        assert result is None, "Must cap at 2 HiPPO alerts per meeting"

    def test_handles_empty_speaking_distribution(self):
        result = detect_hippo({}, total_seconds=0, elapsed_seconds=0, hippo_alerts_delivered=0)
        assert result is None

    def test_handles_single_speaker(self):
        speaking = {"hash_a": 500}
        result = detect_hippo(speaking, total_seconds=500, elapsed_seconds=600, hippo_alerts_delivered=0)
        assert result is not None
        assert result.urgency == "high"


class TestGroupthinkPrecheck:
    SAMPLE_TENSION = [{"topic": "Timeline", "tension_score": 0.7, "summary": "Risk of delay"}]

    def _make_buffer(self, texts: list[str]) -> deque:
        return deque([{"text": t, "speaker_hash": "hash_x"} for t in texts])

    def test_triggers_on_3_or_more_consensus_signals_with_tension(self):
        buffer = self._make_buffer([
            "I totally agree with this direction",
            "That makes sense, let's go with it",
            "Same page here, sounds good to me",
        ])
        result = groupthink_precheck(buffer, self.SAMPLE_TENSION, elapsed_seconds=600)
        assert result is True

    def test_no_trigger_before_8_minutes(self):
        buffer = self._make_buffer([
            "I agree, totally, sounds good, same page, let's go with it",
        ])
        result = groupthink_precheck(buffer, self.SAMPLE_TENSION, elapsed_seconds=400)
        assert result is False, "Must not trigger before 8-minute minimum"

    def test_no_trigger_without_tension_in_map(self):
        buffer = self._make_buffer([
            "I totally agree, sounds good, let's go with it, same page",
        ])
        result = groupthink_precheck(buffer, [], elapsed_seconds=600)
        assert result is False, "No tension map = no groupthink check"

    def test_no_trigger_when_tension_score_too_low(self):
        low_tension = [{"topic": "Timeline", "tension_score": 0.2, "summary": "Minor"}]
        buffer = self._make_buffer([
            "I agree totally, sounds good, let's go",
        ])
        result = groupthink_precheck(buffer, low_tension, elapsed_seconds=600)
        assert result is False

    def test_no_trigger_with_fewer_than_3_signals(self):
        buffer = self._make_buffer([
            "I agree with this approach",  # 1 signal
            "Let me think about it",
        ])
        result = groupthink_precheck(buffer, self.SAMPLE_TENSION, elapsed_seconds=600)
        assert result is False
```

---

### 3.4 — `tests/integration/test_api_surveys.py`

```python
"""
tests/integration/test_api_surveys.py — Full survey flow integration tests.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Meeting, SurveyResponse


@pytest.mark.integration
class TestSurveySubmission:
    async def test_submit_survey_success_first_submission(
        self, client: AsyncClient, meeting_with_survey: Meeting, db_session: AsyncSession
    ):
        token = meeting_with_survey._test_participants[1][1].survey_token
        payload = {
            "token": token,
            "responses": [
                {"question_id": "q1", "answer": 7, "confidence": 8},
                {"question_id": "q2", "answer": "I'm worried about technical debt"},
                {"question_id": "q3", "answer": "If we had more design resources"},
                {"question_id": "q4", "answer": "Engineering", "confidence": 6},
            ],
        }

        response = await client.post(
            f"/api/v1/meetings/{meeting_with_survey.id}/survey/respond",
            json=payload,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["submitted"] is True

        # Verify stored with hash, not user_id
        sr_query = await db_session.execute(
            select(SurveyResponse).where(SurveyResponse.meeting_id == meeting_with_survey.id)
        )
        records = sr_query.scalars().all()
        assert len(records) == 1
        assert records[0].respondent_hash is not None
        assert len(records[0].respondent_hash) == 20  # truncated to 20

    async def test_duplicate_submission_updates_not_duplicates(
        self, client: AsyncClient, meeting_with_survey: Meeting, db_session: AsyncSession
    ):
        token = meeting_with_survey._test_participants[2][1].survey_token
        base_payload = {
            "token": token,
            "responses": [{"question_id": "q1", "answer": 5}],
        }

        # First submit
        r1 = await client.post(
            f"/api/v1/meetings/{meeting_with_survey.id}/survey/respond",
            json=base_payload,
        )
        assert r1.status_code == 201

        # Update submit
        base_payload["responses"][0]["answer"] = 9
        r2 = await client.post(
            f"/api/v1/meetings/{meeting_with_survey.id}/survey/respond",
            json=base_payload,
        )
        assert r2.status_code in (200, 201)  # both acceptable

        # Verify only ONE record exists
        count_q = await db_session.execute(
            select(SurveyResponse).where(SurveyResponse.meeting_id == meeting_with_survey.id)
        )
        assert len(count_q.scalars().all()) == 1

    async def test_facilitator_cannot_get_individual_responses(
        self, client: AsyncClient, meeting_with_survey: Meeting
    ):
        """This endpoint MUST NOT exist."""
        response = await client.get(
            f"/api/v1/meetings/{meeting_with_survey.id}/survey/responses"
        )
        assert response.status_code == 404

    async def test_invalid_token_rejected(
        self, client: AsyncClient, meeting_with_survey: Meeting
    ):
        response = await client.post(
            f"/api/v1/meetings/{meeting_with_survey.id}/survey/respond",
            json={"token": "invalid-token-xyz", "responses": []},
        )
        assert response.status_code == 404

    async def test_survey_status_shows_response_rate(
        self, client: AsyncClient, meeting_with_survey: Meeting, db_session: AsyncSession
    ):
        """After 2 of 5 participants respond, rate should be 0.40."""
        for i in [1, 2]:
            token = meeting_with_survey._test_participants[i][1].survey_token
            await client.post(
                f"/api/v1/meetings/{meeting_with_survey.id}/survey/respond",
                json={"token": token, "responses": [{"question_id": "q1", "answer": 5}]},
            )

        response = await client.get(
            f"/api/v1/meetings/{meeting_with_survey.id}/survey/status"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["response_count"] == 2
        assert data["participant_count"] == 5
        assert abs(data["response_rate"] - 0.4) < 0.01
        assert data["meets_threshold"] is False  # below 50%
```

---

## PART 4 — PRODUCTION INFRASTRUCTURE GAPS

### 4.1 — `scripts/seed_db.py` (Required by Makefile)

```python
#!/usr/bin/env python3
"""
scripts/seed_db.py — Seed local development database with demo data.
Creates a demo org, admin user, sample meetings, decisions.
Run: poetry run python scripts/seed_db.py
"""
import asyncio
import uuid
from datetime import datetime, timedelta, UTC

from app.core.database import async_session_factory
from app.core.security import generate_survey_token, utc_now
from app.core.jwt_utils import encode_jwt
from app.models.models import (
    Decision, DecisionType, GroupIntelligenceProfile, Meeting, MeetingParticipant,
    MeetingPlatform, MeetingStatus, Organization, OrgPlan, ParticipantRole,
    PostMortemStatus, SurveyResponse, User, UserRole,
)
from app.core.security import anonymize_respondent


async def seed():
    print("🌱 Seeding development database...")
    async with async_session_factory() as db:
        # Organization
        org = Organization(
            id=uuid.uuid4(),
            name="Acme Corp (Demo)",
            domain="acmecorp.demo",
            plan=OrgPlan.GROWTH,
            seat_count=25,
            settings={
                "ai_context": "B2B SaaS company, Series B, 200 employees, building developer tools",
                "recording_consent_enabled": False,
                "min_survey_response_rate": 0.5,
            },
        )
        db.add(org)

        # Admin user
        admin = User(
            id=uuid.uuid4(),
            org_id=org.id,
            auth0_id="dev|admin@acmecorp.demo",
            email="admin@acmecorp.demo",
            display_name="Alex Johnson (Admin)",
            role=UserRole.ADMIN,
        )
        db.add(admin)

        # Other team members
        team = []
        names = ["Sarah Chen", "Michael Park", "Jennifer Wu", "David Kumar", "Lisa Anderson"]
        for i, name in enumerate(names):
            u = User(
                id=uuid.uuid4(),
                org_id=org.id,
                auth0_id=f"dev|user{i}@acmecorp.demo",
                email=f"user{i}@acmecorp.demo",
                display_name=name,
                role=UserRole.FACILITATOR if i == 0 else UserRole.MEMBER,
            )
            db.add(u)
            team.append(u)

        await db.flush()

        # Meeting 1 — Past meeting with tension map
        past_meeting = Meeting(
            id=uuid.uuid4(),
            org_id=org.id,
            created_by=admin.id,
            title="Q2 Roadmap Prioritization",
            description="Deciding Q2 features given capacity constraints",
            scheduled_at=datetime.now(UTC) - timedelta(days=30),
            duration_minutes=90,
            platform=MeetingPlatform.ZOOM,
            status=MeetingStatus.POST_MORTEM_DONE,
            agenda_items=[
                {"title": "Review Q1 learnings", "duration_mins": 20, "type": "review"},
                {"title": "Rank feature candidates", "duration_mins": 40, "type": "decision"},
                {"title": "Resource allocation", "duration_mins": 20, "type": "planning"},
                {"title": "Risks", "duration_mins": 10, "type": "risk"},
            ],
            survey_participant_count=5,
            survey_response_count=4,
            tension_map={
                "consensus_areas": [
                    {
                        "topic": "Feature Importance",
                        "agreement_score": 0.92,
                        "summary": "Strong consensus that integrations are top priority",
                        "confidence_average": 8.5,
                    }
                ],
                "tension_areas": [
                    {
                        "topic": "Timeline Feasibility",
                        "tension_score": 0.78,
                        "summary": "Deep disagreement about 60-day delivery estimate",
                        "perspective_a": "Leadership expects linear development",
                        "perspective_b": "Engineering sees legacy technical debt",
                        "why_this_matters": "Customer commitments hinge on this",
                        "recommended_question": "What would cause us to miss the 60-day target?",
                    }
                ],
                "missing_from_conversation": ["Customer Support team impact"],
                "facilitator_opening_question": "Before diving in — what's the biggest unstated risk?",
                "watch_list": ["Engineering confidence", "Marketing timeline assumptions"],
                "confidence": 0.87,
            },
            facilitator_brief="Key insight: Surface agreement masks timeline skepticism. Start with a pre-mortem.",
            domain="product",
        )
        db.add(past_meeting)
        await db.flush()

        # Add participants to past meeting
        all_users = [admin] + team
        for i, user in enumerate(all_users[:5]):
            participant = MeetingParticipant(
                id=uuid.uuid4(),
                meeting_id=past_meeting.id,
                user_id=user.id,
                role=ParticipantRole.FACILITATOR if user.id == admin.id else ParticipantRole.PARTICIPANT,
                survey_token=generate_survey_token(),
                survey_completed_at=datetime.now(UTC) - timedelta(days=30, hours=2),
            )
            db.add(participant)

            if i < 4:  # 4 of 5 responded
                h = anonymize_respondent(str(user.id), str(past_meeting.id))
                sr = SurveyResponse(
                    meeting_id=past_meeting.id,
                    respondent_hash=h,
                    responses=[
                        {"question_id": "q1", "answer": 7 + i, "confidence": 6 + i},
                        {"question_id": "q2", "answer": "Worried about the legacy API dependencies"},
                        {"question_id": "q3", "answer": "If we had 2 more engineers"},
                    ],
                )
                db.add(sr)

        # Decision from past meeting
        decision = Decision(
            id=uuid.uuid4(),
            org_id=org.id,
            meeting_id=past_meeting.id,
            created_by=admin.id,
            title="Prioritize API Integration Feature for Q2",
            description="Commit to building the Salesforce integration as the primary Q2 deliverable",
            domain="product",
            decision_type=DecisionType.PRIORITIZATION,
            options_considered=[
                {"option": "Salesforce Integration", "pros": ["High demand", "Revenue impact"], "cons": ["Complex"], "was_chosen": True},
                {"option": "Mobile App Polish", "pros": ["User satisfaction"], "cons": ["Lower revenue"], "was_chosen": False},
            ],
            key_assumptions=[
                {"assumption": "3 engineers sufficient for 60-day delivery", "confidence": 0.7, "check_in_question": "Is 3 engineers still sufficient?"},
                {"assumption": "No major API breaking changes from Salesforce", "confidence": 0.8, "check_in_question": "Have Salesforce APIs changed?"},
            ],
            team_confidence=0.75,
            post_mortem_status=PostMortemStatus.COMPLETED,
            post_mortem_notes="Strong execution despite initial skepticism. Salesforce API change was managed.",
        )
        db.add(decision)
        await db.flush()

        # Upcoming meeting
        upcoming = Meeting(
            id=uuid.uuid4(),
            org_id=org.id,
            created_by=admin.id,
            title="Q3 Roadmap Decision",
            description="Deciding Q3 features with tighter capacity",
            scheduled_at=datetime.now(UTC) + timedelta(days=3),
            duration_minutes=60,
            platform=MeetingPlatform.ZOOM,
            status=MeetingStatus.SURVEY_OPEN,
            agenda_items=[
                {"title": "Q2 retrospective", "duration_mins": 15, "type": "review"},
                {"title": "Q3 feature ranking", "duration_mins": 30, "type": "decision"},
                {"title": "Capacity allocation", "duration_mins": 15, "type": "planning"},
            ],
            survey_participant_count=5,
            survey_response_count=2,
            domain="product",
        )
        db.add(upcoming)
        await db.flush()

        # Group Intelligence Profile
        gip = GroupIntelligenceProfile(
            org_id=org.id,
            total_decisions_tracked=8,
            decisions_with_outcomes=3,
            overall_accuracy_score=71.2,
            identified_patterns=[
                {
                    "pattern_id": "pat_001",
                    "name": "Friday Afternoon Effect",
                    "description": "Decisions made Friday PM show 58% lower accuracy",
                    "evidence": "9 data points across 18 months",
                    "sample_size": 9,
                    "confidence": "high",
                    "actionable_intervention": "Avoid scheduling critical decisions on Friday afternoons",
                    "example_decision_ids": [str(decision.id)],
                },
            ],
            domain_accuracy={"product": 72.0, "hiring": 55.0, "strategy": 65.0},
            avg_survey_response_rate=0.78,
            avg_speaking_time_gini=0.42,
            hippo_frequency_score=0.28,
            groupthink_frequency_score=0.19,
        )
        db.add(gip)

        await db.commit()

        # Generate dev JWT for easy testing
        token = encode_jwt(
            {
                "type": "dev_access",
                "sub": str(admin.id),
                "org_id": str(org.id),
                "email": admin.email,
                "role": "admin",
                "exp": (datetime.now(UTC) + timedelta(days=30)).timestamp(),
                "iat": datetime.now(UTC).timestamp(),
            },
            "dev-secret-change-me-in-production",
        )

        print(f"✅ Seed complete!")
        print(f"   Org ID:       {org.id}")
        print(f"   Admin email:  {admin.email}")
        print(f"   Admin token:  {token[:40]}...")
        print(f"\n   Meetings: {past_meeting.id} (past), {upcoming.id} (upcoming)")
        print(f"   Decision: {decision.id}")
        print(f"\n   Login at:     http://localhost:3000/login")
        print(f"   API Health:   http://localhost:8000/health")


if __name__ == "__main__":
    asyncio.run(seed())
```

---

### 4.2 — `alembic/env.py` (Required for Migration to Work)

```python
# alembic/env.py
import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.models.models import Base  # This imports ALL models

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
target_metadata = Base.metadata


def get_url():
    return settings.normalized_database_url


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    engine = create_async_engine(get_url(), poolclass=pool.NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

---

## PART 5 — MISSING PRODUCTION FEATURES (HIGH BUSINESS VALUE)

### 5.1 — Real-Time Collaboration: Multiple Facilitator Tabs

```python
# Problem: Currently only one WebSocket per meeting gets alerts.
# If facilitator has multiple tabs, only the first one works.
#
# Solution: Use Redis Pub/Sub to broadcast to ALL connections for a meeting.

# app/services/websocket_manager.py — Redis-backed pub/sub version:
import json
import asyncio
import redis.asyncio as aioredis
from fastapi import WebSocket


class RedisBackedWebSocketManager:
    """
    Broadcast to all WebSocket connections for a meeting using Redis Pub/Sub.
    Survives pod restarts and horizontal scaling.
    """

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._connections: dict[str, set[WebSocket]] = {}
        self._pubsub_task: asyncio.Task | None = None

    async def connect(self, meeting_id: str, websocket: WebSocket):
        await websocket.accept()
        if meeting_id not in self._connections:
            self._connections[meeting_id] = set()
        self._connections[meeting_id].add(websocket)

    async def disconnect(self, meeting_id: str, websocket: WebSocket):
        if meeting_id in self._connections:
            self._connections[meeting_id].discard(websocket)
            if not self._connections[meeting_id]:
                del self._connections[meeting_id]

    async def broadcast(self, meeting_id: str, message: dict):
        """Publish to Redis — all pods pick up and forward to their WS connections."""
        redis = aioredis.from_url(self.redis_url)
        channel = f"quorum:meeting:{meeting_id}:messages"
        await redis.publish(channel, json.dumps(message))
        await redis.aclose()

    async def start_listener(self, meeting_id: str):
        """Subscribe to Redis pub/sub and forward to local WebSocket connections."""
        redis = aioredis.from_url(self.redis_url)
        pubsub = redis.pubsub()
        channel = f"quorum:meeting:{meeting_id}:messages"
        await pubsub.subscribe(channel)

        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await self._forward_to_local_connections(meeting_id, data)

        await redis.aclose()

    async def _forward_to_local_connections(self, meeting_id: str, message: dict):
        dead = set()
        for ws in self._connections.get(meeting_id, set()):
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._connections.get(meeting_id, set()).discard(ws)
```

---

### 5.2 — Survey Reminder System

```python
# app/workers/tasks/send_survey_reminders.py
"""
Task: Send survey reminders at 50% and 90% of deadline elapsed.
Triggered when survey is created, scheduled as delayed Celery tasks.
"""
from app.workers.celery_app import celery_app
from app.core.database import async_session_factory
from app.models.models import Meeting, MeetingParticipant, User
from app.services.email_service import email_service
from sqlalchemy import select
import asyncio
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.send_survey_reminder")
def send_survey_reminder(meeting_id: str, reminder_type: str):
    """reminder_type: '50_pct' or '90_pct'"""
    asyncio.run(_send_reminder_async(meeting_id, reminder_type))


async def _send_reminder_async(meeting_id: str, reminder_type: str):
    async with async_session_factory() as db:
        meeting_q = await db.execute(
            select(Meeting).where(Meeting.id == meeting_id)
        )
        meeting = meeting_q.scalar_one_or_none()
        if not meeting or meeting.status != "survey_open":
            return  # meeting already closed or not found

        # Get participants who haven't responded
        participants_q = await db.execute(
            select(MeetingParticipant)
            .where(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.survey_completed_at == None,
            )
        )
        participants = participants_q.scalars().all()

        for participant in participants:
            user_q = await db.execute(select(User).where(User.id == participant.user_id))
            user = user_q.scalar_one_or_none()
            if not user or not participant.survey_token:
                continue

            from app.core.config import get_settings
            settings = get_settings()
            survey_url = f"{settings.APP_URL}/survey/{meeting_id}?token={participant.survey_token}"

            await email_service.send_survey_reminder(
                to_email=user.email,
                meeting_title=meeting.title,
                survey_url=survey_url,
                deadline=meeting.survey_deadline,
                reminder_type=reminder_type,
            )

        logger.info(f"Sent {reminder_type} reminders for meeting {meeting_id}")


# Schedule reminders when survey is opened:
# In surveys.py generate_survey endpoint, after setting meeting.status = SURVEY_OPEN:
#
# if meeting.survey_deadline:
#     from app.workers.tasks.send_survey_reminders import send_survey_reminder
#     half_elapsed = (meeting.survey_deadline - datetime.now(UTC)) / 2
#     ninety_elapsed = (meeting.survey_deadline - datetime.now(UTC)) * 0.9
#     send_survey_reminder.apply_async(
#         args=[str(meeting.id), "50_pct"],
#         eta=datetime.now(UTC) + half_elapsed,
#     )
#     send_survey_reminder.apply_async(
#         args=[str(meeting.id), "90_pct"],
#         eta=datetime.now(UTC) + ninety_elapsed,
#     )
```

---

### 5.3 — InfluxDB Speaking Time Recording (Currently Not Written)

```python
# app/services/influx_service.py — Complete implementation:
import logging
from datetime import datetime, UTC
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class InfluxService:
    def __init__(self):
        self._client = None
        self._write_api = None

    def _get_write_api(self):
        if self._write_api:
            return self._write_api
        if not settings.INFLUXDB_URL or not settings.INFLUXDB_TOKEN:
            return None
        try:
            from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
            from influxdb_client.client.write_api import ASYNCHRONOUS
            self._client = InfluxDBClientAsync(
                url=settings.INFLUXDB_URL,
                token=settings.INFLUXDB_TOKEN,
                org=settings.INFLUXDB_ORG,
            )
            return self._client
        except Exception as e:
            logger.warning(f"InfluxDB init failed: {e}")
            return None

    async def record_speaking_time(
        self,
        org_id: str,
        meeting_id: str,
        session_id: str,
        speaker_hash: str,
        seconds_speaking: float,
    ) -> None:
        client = self._get_write_api()
        if not client:
            return
        try:
            from influxdb_client import Point
            point = (
                Point("speaking_time")
                .tag("org_id", org_id)
                .tag("meeting_id", meeting_id)
                .tag("session_id", session_id)
                .tag("speaker_hash", speaker_hash)
                .field("seconds_speaking", seconds_speaking)
                .time(datetime.now(UTC))
            )
            async with client as c:
                write_api = c.write_api()
                await write_api.write(
                    bucket=settings.INFLUXDB_BUCKET,
                    org=settings.INFLUXDB_ORG,
                    record=point,
                )
        except Exception as e:
            logger.error(f"InfluxDB write failed: {e}")

    async def record_intelligence_event(
        self,
        org_id: str,
        meeting_id: str,
        event_type: str,
        severity: int,
    ) -> None:
        client = self._get_write_api()
        if not client:
            return
        try:
            from influxdb_client import Point
            point = (
                Point("intelligence_events")
                .tag("org_id", org_id)
                .tag("meeting_id", meeting_id)
                .tag("event_type", event_type)
                .field("severity", severity)
                .field("resolved", False)
                .time(datetime.now(UTC))
            )
            async with client as c:
                write_api = c.write_api()
                await write_api.write(
                    bucket=settings.INFLUXDB_BUCKET,
                    org=settings.INFLUXDB_ORG,
                    record=point,
                )
        except Exception as e:
            logger.error(f"InfluxDB intelligence event write failed: {e}")


influx_service = InfluxService()
```

---

## PART 6 — EXACT BUILD EXECUTION ORDER

### 6.1 — Step-by-Step Commands to Get to Working State

```bash
# ── STEP 1: Create the two missing critical files ──
# Create app/models/models.py with content from Part 1.1
# Create app/schemas/schemas.py with content from Part 1.2

# ── STEP 2: Create Alembic migration ──
mkdir -p alembic/versions
# Create alembic/versions/001_initial_schema.py with content from Part 1.3

# ── STEP 3: Create alembic/env.py ──
# Create with content from Part 4.2

# ── STEP 4: Fix bugs ──
# Fix app/main.py: "SELECT 1" → text("SELECT 1")
# Fix app/services/stt_service.py: remove duplicate _intelligence_evaluation_loop
# Fix app/core/config.py: add APP_URL field
# Fix app/api/auth.py: add display_name to CurrentUser
# Create Auth0 route handlers in src/app/auth/*/route.ts

# ── STEP 5: Start infrastructure ──
docker compose up -d postgres redis influxdb

# ── STEP 6: Install dependencies ──
poetry install
cd web && npm ci && cd ..

# ── STEP 7: Run migrations ──
DATABASE_URL=postgresql+asyncpg://quorum:quorum_dev@localhost:5432/quorum \
poetry run alembic upgrade head

# ── STEP 8: Seed database ──
DATABASE_URL=postgresql+asyncpg://quorum:quorum_dev@localhost:5432/quorum \
poetry run python scripts/seed_db.py

# ── STEP 9: Create Celery app ──
# Create app/workers/celery_app.py with content from Part 1.9
# Create app/workers/tasks/send_outcome_checkins.py from Part 1.8
# Create app/workers/tasks/run_pattern_detector.py from Part 1.8

# ── STEP 10: Start full stack ──
docker compose up

# ── STEP 11: Verify ──
curl http://localhost:8000/health
# Expected: {"status": "ok", "version": "1.0.0", "db": "ok", "redis": "ok"}

# ── STEP 12: Run tests ──
poetry run pytest tests/unit/ -v --no-header
# Expected: All anonymization + detection tests pass

# ── STEP 13: Pre-commit setup ──
poetry run pre-commit install
poetry run pre-commit run --all-files
```

---

## PART 7 — AI EVAL SUITE IMPLEMENTATION

### 7.1 — Survey Designer Eval (Complete)

```python
# tests/ai_evals/eval_survey_designer.py
"""
AI evaluation suite for the Survey Designer agent.
Cost: ~$0.05 per full run. Run before any prompt change promotion.
Minimum passing score: 0.85 average across all cases.
"""
import asyncio
import time
from dataclasses import dataclass, field
from typing import Callable

import pytest

from app.intelligence.agents.factory import AgentFactory
from app.schemas.schemas import SurveyDesignerOutput


@dataclass
class EvalResult:
    case_name: str
    passed: bool
    score: float
    failures: list[str]
    latency_ms: int


# ── Evaluators ─────────────────────────────────────────────────────────
def eval_question_count(output: SurveyDesignerOutput) -> tuple[bool, float, str]:
    n = len(output.questions)
    ok = 4 <= n <= 6
    return ok, 1.0 if ok else 0.5, f"Question count {n} (expected 4-6)"


def eval_has_worried_question(output: SurveyDesignerOutput) -> tuple[bool, float, str]:
    has_it = any(
        "worried" in q.text.lower() or "concern" in q.text.lower()
        or "worry" in q.text.lower()
        for q in output.questions
    )
    return has_it, 1.0 if has_it else 0.0, "Missing 'worried/concern' question"


def eval_has_falsifiability_question(output: SurveyDesignerOutput) -> tuple[bool, float, str]:
    has_it = any(
        "change your mind" in q.text.lower()
        or "wrong" in q.text.lower()
        or "reconsider" in q.text.lower()
        for q in output.questions
    )
    return has_it, 1.0 if has_it else 0.0, "Missing falsifiability question"


def eval_opinion_questions_have_confidence(output: SurveyDesignerOutput) -> tuple[bool, float, str]:
    opinion_qs = [q for q in output.questions if q.type in ("scale_1_10", "multiple_choice")]
    if not opinion_qs:
        return True, 1.0, ""
    missing = [q for q in opinion_qs if not q.include_confidence_rating]
    score = 1.0 - len(missing) / len(opinion_qs)
    ok = len(missing) == 0
    return ok, score, f"{len(missing)} opinion questions missing confidence rating"


def eval_no_generic_phrasing(output: SurveyDesignerOutput) -> tuple[bool, float, str]:
    generic = ["what do you think", "how do you feel", "any thoughts", "tell me about"]
    generic_count = sum(
        1 for q in output.questions
        if any(g in q.text.lower() for g in generic)
    )
    score = 1.0 - (generic_count / max(len(output.questions), 1))
    return generic_count == 0, score, f"{generic_count} generic question(s) found"


def eval_has_design_rationale(output: SurveyDesignerOutput) -> tuple[bool, float, str]:
    has_it = bool(output.design_rationale) and len(output.design_rationale) > 20
    return has_it, 1.0 if has_it else 0.3, "Missing or very short design rationale"


EVALUATORS = [
    eval_question_count,
    eval_has_worried_question,
    eval_has_falsifiability_question,
    eval_opinion_questions_have_confidence,
    eval_no_generic_phrasing,
    eval_has_design_rationale,
]

TEST_CASES = [
    {
        "name": "Product roadmap prioritization",
        "input": {
            "meeting_title": "Q3 Product Roadmap Prioritization",
            "meeting_description": "Deciding which 3 features to build in Q3 given 60% capacity",
            "agenda_items": [
                {"title": "Review Q2 learnings", "duration_mins": 15},
                {"title": "Rank top 5 features", "duration_mins": 30},
                {"title": "Resource allocation", "duration_mins": 15},
            ],
            "org_context": "B2B SaaS, 80 employees, Series B, developer tools",
            "past_tension_patterns": [],
        },
    },
    {
        "name": "Senior hiring decision",
        "input": {
            "meeting_title": "Hiring Decision: VP Engineering Candidate",
            "meeting_description": "Final go/no-go on hiring Sarah Doe for VP Engineering",
            "agenda_items": [
                {"title": "Interview debrief", "duration_mins": 20},
                {"title": "Decision vote", "duration_mins": 15},
            ],
            "org_context": "25-person engineering team, Series A startup",
            "past_tension_patterns": [
                {"name": "Overconfidence in senior hiring", "confidence": "high"}
            ],
        },
    },
    {
        "name": "Strategic pivot discussion",
        "input": {
            "meeting_title": "Should We Pivot to Enterprise Market?",
            "meeting_description": "Evaluating a major strategic shift from SMB to enterprise",
            "agenda_items": [
                {"title": "Market data review", "duration_mins": 20},
                {"title": "Risk assessment", "duration_mins": 20},
                {"title": "Go/no-go decision", "duration_mins": 20},
            ],
            "org_context": "SaaS company, $2M ARR, 15 employees, mostly SMB customers",
            "past_tension_patterns": [],
        },
    },
]


async def run_eval(case: dict) -> EvalResult:
    agent = AgentFactory.get_survey_designer()
    start = time.time()

    try:
        output = await agent.generate(**case["input"])
    except Exception as e:
        return EvalResult(
            case_name=case["name"],
            passed=False,
            score=0.0,
            failures=[f"Generation failed: {str(e)}"],
            latency_ms=int((time.time() - start) * 1000),
        )

    latency_ms = int((time.time() - start) * 1000)
    failures = []
    scores = []

    for evaluator in EVALUATORS:
        passed, score, reason = evaluator(output)
        scores.append(score)
        if not passed:
            failures.append(reason)

    avg_score = sum(scores) / len(scores)
    return EvalResult(
        case_name=case["name"],
        passed=len(failures) == 0,
        score=avg_score,
        failures=failures,
        latency_ms=latency_ms,
    )


@pytest.mark.ai_eval
@pytest.mark.asyncio
async def test_survey_designer_quality():
    """All cases must achieve average score >= 0.85."""
    results = [await run_eval(case) for case in TEST_CASES]

    print("\n── Survey Designer Eval Results ──")
    all_scores = []
    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        print(f"{status} [{r.score:.2f}] {r.case_name} ({r.latency_ms}ms)")
        if r.failures:
            for f in r.failures:
                print(f"         ⚠ {f}")
        all_scores.append(r.score)

    avg = sum(all_scores) / len(all_scores)
    print(f"\nAverage score: {avg:.2f} (minimum: 0.85)")
    assert avg >= 0.85, f"Survey Designer quality below threshold: {avg:.2f} < 0.85"
```

---

## PART 8 — ENVIRONMENT CONFIGURATION CHECKLIST

### 8.1 — Complete `.env.example`

```bash
# ── App ──────────────────────────────────────────
APP_ENV=development
APP_URL=http://localhost:3000
SECRET_KEY=dev-secret-change-me-in-production-32ch
DEBUG=true
LOG_LEVEL=DEBUG

# ── Auth0 ────────────────────────────────────────
AUTH0_DOMAIN=quorum-dev.auth0.com
AUTH0_CLIENT_ID=your-auth0-client-id
AUTH0_CLIENT_SECRET=your-auth0-client-secret
AUTH0_AUDIENCE=https://api.quorum.ai

# ── Database ─────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://quorum:quorum_dev@localhost:5432/quorum
DATABASE_ECHO=false
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# ── Redis ────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── InfluxDB ─────────────────────────────────────
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=dev-token-12345
INFLUXDB_ORG=quorum
INFLUXDB_BUCKET=meeting_metrics

# ── AI (REQUIRED for AI features) ────────────────
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
PINECONE_INDEX=quorum-decisions-dev
DEEPGRAM_API_KEY=...

# ── Anonymization (NEVER rotate during open surveys) ──
SPEAKER_HASH_SECRET=dev-speaker-secret-32chars-minimum
RESPONDENT_HASH_SECRET=dev-respondent-secret-32chars-min

# ── Meeting Platforms ─────────────────────────────
ZOOM_CLIENT_ID=
ZOOM_CLIENT_SECRET=
ZOOM_WEBHOOK_SECRET=
TEAMS_APP_ID=
TEAMS_APP_PASSWORD=

# ── Email ────────────────────────────────────────
SENDGRID_API_KEY=
SENDGRID_FROM_EMAIL=hello@quorum.ai
SENDGRID_FROM_NAME=Quorum

# ── Billing ──────────────────────────────────────
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=

# ── AWS ──────────────────────────────────────────
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
S3_BUCKET=quorum-recordings-dev

# ── Observability ────────────────────────────────
SENTRY_DSN=
DATADOG_API_KEY=

# ── Next.js Frontend ─────────────────────────────
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000
AUTH0_SECRET=dev-auth0-secret-minimum-32-chars
AUTH0_BASE_URL=http://localhost:3000
AUTH0_ISSUER_BASE_URL=https://quorum-dev.auth0.com
AUTH0_CLIENT_ID=your-auth0-client-id
AUTH0_CLIENT_SECRET=your-auth0-client-secret
AUTH0_AUDIENCE=https://api.quorum.ai

# ── Celery ────────────────────────────────────────
CELERY_TASK_ALWAYS_EAGER=false
```

---

## PART 9 — MISSING FRONTEND PAGES AND COMPONENTS

### 9.1 — Survey Deadline Extension UI (Missing from Spec)

```typescript
// src/app/(app)/meetings/[id]/survey-deadline/page.tsx
// When facilitator wants to extend survey deadline by 24 hours
"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { queries, mutations } from "@/lib/api";
import { toast } from "sonner";

export default function ExtendDeadlinePage({ params }: { params: { id: string } }) {
  const { data: meeting } = useQuery({
    queryKey: ["meeting", params.id],
    queryFn: () => queries.getMeeting(params.id),
  });

  const extendMutation = useMutation({
    mutationFn: () => mutations.extendSurveyDeadline(params.id, 24), // +24 hours
    onSuccess: () => toast.success("Survey deadline extended by 24 hours. Reminder sent to non-respondents."),
    onError: () => toast.error("Failed to extend deadline"),
  });

  return (
    <div className="glass-card p-8 max-w-md mx-auto mt-10">
      <h2 className="text-xl font-bold text-white mb-2">Extend Survey Deadline?</h2>
      <p className="text-sm text-on-surface-muted mb-6">
        Current response rate: {Math.round((meeting?.survey_response_rate || 0) * 100)}%
        ({meeting?.survey_response_count}/{meeting?.survey_participant_count}).
        Extending by 24 hours will send reminders to non-respondents.
      </p>
      <button
        onClick={() => extendMutation.mutate()}
        disabled={extendMutation.isPending}
        className="btn-primary w-full"
      >
        {extendMutation.isPending ? "Extending..." : "Extend by 24 Hours"}
      </button>
    </div>
  );
}
```

```typescript
// Add to src/lib/api.ts mutations:
extendSurveyDeadline: (meetingId: string, hoursToAdd: number) =>
    patch<Meeting>(`/meetings/${meetingId}`, {
        survey_deadline: new Date(Date.now() + hoursToAdd * 60 * 60 * 1000).toISOString()
    }),
```

---

### 9.2 — API Key Management Page (Missing)

```typescript
// src/app/(app)/settings/api-keys/page.tsx
"use client";
import { useState } from "react";
import { Key, Plus, Trash2, Copy } from "lucide-react";

export default function ApiKeysPage() {
  const [newKeyName, setNewKeyName] = useState("");
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Key className="w-5 h-5" /> API Keys
        </h2>
        <p className="text-sm text-on-surface-muted mb-4">
          API keys allow Zoom integrations, custom workflows, and third-party tools
          to authenticate with Quorum without using OAuth.
          Keys are shown once — store them securely.
        </p>

        {generatedKey && (
          <div className="bg-success/10 border border-success/30 rounded-lg p-4 mb-6">
            <p className="text-sm text-success font-semibold mb-2">
              ✓ New key generated. Copy it now — it won&apos;t be shown again.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 font-mono text-xs text-white bg-black/30 p-2 rounded">
                {generatedKey}
              </code>
              <button
                onClick={() => { navigator.clipboard.writeText(generatedKey); }}
                className="p-2 rounded bg-white/[0.06] hover:bg-white/[0.12]"
              >
                <Copy className="w-4 h-4 text-on-surface-muted" />
              </button>
            </div>
          </div>
        )}

        <div className="flex gap-3">
          <input
            value={newKeyName}
            onChange={e => setNewKeyName(e.target.value)}
            placeholder="Key name (e.g. 'Zoom Integration')"
            className="input-field flex-1"
          />
          <button className="btn-primary flex items-center gap-2">
            <Plus className="w-4 h-4" /> Create Key
          </button>
        </div>
      </div>
    </div>
  );
}
```

---

## PART 10 — FINAL PRE-LAUNCH VERIFICATION SCRIPT

```bash
#!/bin/bash
# scripts/verify_production_readiness.sh
# Run this script before accepting first paying customer.
# Every check must pass.

set -e
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

PASS=0
FAIL=0

check() {
    local label="$1"
    local command="$2"
    if eval "$command" &>/dev/null; then
        echo -e "${GREEN}✅${NC} $label"
        ((PASS++))
    else
        echo -e "${RED}❌${NC} $label"
        ((FAIL++))
    fi
}

echo "═══════════════════════════════════════════════"
echo "  QUORUM Production Readiness Verification"
echo "═══════════════════════════════════════════════"

# ── Code Quality ──────────────────────────────────
echo "\n── Code Quality ──"
check "Ruff linting passes" "poetry run ruff check ."
check "Ruff format check" "poetry run ruff format --check ."
check "MyPy type checking" "poetry run mypy app/"
check "TypeScript no errors" "cd web && npx tsc --noEmit"

# ── Tests ─────────────────────────────────────────
echo "\n── Tests ──"
check "Unit tests pass" "poetry run pytest tests/unit/ -q"
check "Integration tests pass" "poetry run pytest tests/integration/ -q"
check "Coverage >= 80%" "poetry run pytest --cov=app --cov-fail-under=80 -q"

# ── Security ──────────────────────────────────────
echo "\n── Security ──"
check "No high-severity Bandit findings" "poetry run bandit -r app/ -ll -q"
check "No known CVEs" "pip-audit --requirement <(poetry export -f requirements.txt --without-hashes) -q"
check "No secrets in repo" "trufflehog git file://. --only-verified --quiet"

# ── Database ──────────────────────────────────────
echo "\n── Database ──"
check "Migrations up to date" "poetry run alembic check"
check "Health check returns ok" "curl -sf http://localhost:8000/health | grep '\"status\": \"ok\"'"

# ── Anonymization (Critical) ──────────────────────
echo "\n── Anonymization (Critical) ──"
check "Adversarial anonymization tests" "poetry run pytest tests/unit/test_anonymization.py -q"

# ── Environment ───────────────────────────────────
echo "\n── Environment ──"
check "RESPONDENT_HASH_SECRET set" "[ -n \"\$RESPONDENT_HASH_SECRET\" ]"
check "SPEAKER_HASH_SECRET set" "[ -n \"\$SPEAKER_HASH_SECRET\" ]"
check "ANTHROPIC_API_KEY set" "[ -n \"\$ANTHROPIC_API_KEY\" ]"
check "STRIPE_SECRET_KEY set" "[ -n \"\$STRIPE_SECRET_KEY\" ]"
check "AUTH0 configured" "[ -n \"\$AUTH0_DOMAIN\" ]"

# ── Endpoints ─────────────────────────────────────
echo "\n── Critical Endpoint Checks ──"
check "Facilitator cannot access individual responses (404)" \
    "curl -sf -o /dev/null -w '%{http_code}' http://localhost:8000/api/v1/meetings/test/survey/responses | grep 404"
check "Health endpoint returns 200" \
    "curl -sf -o /dev/null -w '%{http_code}' http://localhost:8000/health | grep 200"
check "Unauthenticated requests return 401" \
    "curl -sf -o /dev/null -w '%{http_code}' http://localhost:8000/api/v1/meetings | grep 401"

echo "\n═══════════════════════════════════════════════"
echo "  Results: ${PASS} passed, ${FAIL} failed"
echo "═══════════════════════════════════════════════"

if [ $FAIL -gt 0 ]; then
    echo -e "${RED}  ❌ NOT READY FOR PRODUCTION${NC}"
    exit 1
else
    echo -e "${GREEN}  ✅ READY FOR FIRST PAYING CUSTOMER${NC}"
fi
```

---

## APPENDIX — IMPLEMENTATION PRIORITY MATRIX

| Priority | Task | File(s) | Effort | Blocks |
|----------|------|---------|--------|--------|
| **P0 — CRITICAL (Nothing works without these)** | | | | |
| 1 | Create `app/models/models.py` | Part 1.1 | 2h | Everything |
| 2 | Create `app/schemas/schemas.py` | Part 1.2 | 1h | All routers |
| 3 | Create first Alembic migration | Part 1.3 | 1h | DB startup |
| 4 | Create `alembic/env.py` | Part 4.2 | 30m | Migrations |
| 5 | Fix `main.py` SELECT 1 bug | Part 1.4 | 5m | API startup |
| 6 | Fix duplicate `_intelligence_evaluation_loop` | Part 1.5 | 15m | Live meetings |
| 7 | Add `APP_URL` to Settings | Part 1.6 | 5m | Email service |
| 8 | Add Auth0 Next.js routes | Part 1.7 | 30m | Frontend auth |
| **P1 — HIGH (Feature-complete)** | | | | |
| 9 | Implement Celery tasks | Part 1.8 | 3h | Outcome loop |
| 10 | Create Celery app config | Part 1.9 | 30m | Workers |
| 11 | Fix WebSocket auth (query→message) | Part 1.10 | 1h | Security |
| 12 | Create `tests/conftest.py` | Part 3.1 | 2h | Test suite |
| 13 | Implement rate limiting middleware | Part 2.1 | 2h | Production |
| 14 | Implement Stripe webhook handlers | Part 2.6 | 2h | Billing |
| 15 | Create `scripts/seed_db.py` | Part 4.1 | 1h | Local dev |
| **P2 — MEDIUM (Scalability)** | | | | |
| 16 | Redis-backed WebSocket manager | Part 5.1 | 3h | Horizontal scale |
| 17 | Survey reminder Celery tasks | Part 5.2 | 2h | Retention |
| 18 | InfluxDB speaking time recording | Part 5.3 | 2h | Analytics |
| 19 | Decision embedding on creation | Part 2.3 | 1h | Semantic search |
| 20 | Datadog custom metrics | Part 2.7 | 2h | Observability |
| **P3 — LOWER (Polish)** | | | | |
| 21 | Survey deadline extension UI | Part 9.1 | 1h | UX |
| 22 | API key management page | Part 9.2 | 2h | Enterprise |
| 23 | Security headers middleware | Part 2.2 | 30m | Security posture |
| 24 | AI eval suite for Survey Designer | Part 7.1 | 2h | Prompt quality |

---

*QUORUM God-Tier Implementation Pipeline v3.0*
*Total estimated implementation time from this specification: 30-40 engineer-hours*
*Every file, every bug fix, every missing feature catalogued with exact code.*

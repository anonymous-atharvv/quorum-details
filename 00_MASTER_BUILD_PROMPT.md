# QUORUM — MASTER AI BUILD PROMPT
## The single source of truth for any AI coding agent building this product

---

> Feed this entire document as system context to any frontier AI coding agent (Claude Code, Cursor, GPT-4o). Every architectural decision, data model, AI behavior, integration, and build order is defined here. Do not deviate. Build in the exact sequence specified in Section 8.

---

## SECTION 1: WHAT YOU ARE BUILDING

### Product Name
QUORUM — Collective Intelligence Platform

### One-Sentence Definition
QUORUM is a B2B AI platform that makes organizational group decisions measurably better by combining pre-meeting anonymous elicitation, real-time meeting intelligence, and longitudinal outcome tracking.

### What Exists vs. What Quorum Does

| Existing tools | What they solve |
|---|---|
| Otter.ai, Fireflies | Transcription, summaries (efficiency) |
| Asana, Linear, Notion | Task tracking after decisions |
| Slido, Mentimeter | Live audience polling (engagement) |
| **QUORUM** | **Makes the actual decision quality better** |

### Three Core Behaviors

1. BEFORE: Quorum sends AI-generated anonymous surveys to all meeting participants. It synthesizes what people ACTUALLY think (vs. what they'll say in the room) and gives the facilitator a "tension map" and recommended discussion structure.

2. DURING: Quorum joins the meeting (Zoom/Teams/Meet plugin), listens in real-time, and surfaces intelligence: who is dominating the conversation, when groupthink is setting in, what the anonymous survey data said that hasn't been raised, and what question nobody is asking but should be.

3. AFTER: Quorum generates a structured post-mortem template, schedules outcome check-ins at 30/90/180 days, and tracks whether the decision turned out to be correct. Over time, it builds the team's "Group Intelligence Profile" — their blind spots, their overconfidence patterns, their prediction accuracy.

### What Quorum Is NOT
- Not a transcription tool
- Not a task manager
- Not a personal assistant
- Not a performance evaluation tool (never used to assess individual employees)
- Not surveillance — all individual input is anonymous within the group

---

## SECTION 2: SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                               │
│  Web App (Next.js)  │  Zoom Plugin  │  Teams Plugin  │  Meet Plugin │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTPS / WebSocket
┌──────────────────────────────▼──────────────────────────────────────┐
│                    API GATEWAY  (FastAPI)                           │
│          Auth · Rate limiting · Webhook routing                     │
└────┬──────────┬──────────────┬───────────────┬───────────────┬──────┘
     │          │              │               │               │
┌────▼──┐  ┌───▼────┐   ┌─────▼──────┐  ┌────▼────┐   ┌──────▼─────┐
│Survey │  │Meeting │   │Intelligence│  │Decision │   │ Outcome    │
│Engine │  │Stream  │   │Engine      │  │Library  │   │ Tracker    │
│       │  │Ingester│   │(AI agents) │  │         │   │            │
└────┬──┘  └───┬────┘   └─────┬──────┘  └────┬────┘   └──────┬─────┘
     │          │              │               │               │
┌────▼──────────▼──────────────▼───────────────▼───────────────▼─────┐
│                         DATA LAYER                                  │
│   PostgreSQL (primary)  ·  Redis (cache/queue)  ·  S3 (recordings) │
│   Pinecone (decision embeddings)  ·  InfluxDB (time-series metrics) │
└─────────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                     INTEGRATION LAYER                               │
│   Zoom SDK  ·  Teams Bot Framework  ·  Google Meet API             │
│   Slack (notifications)  ·  Cal.com / Google Calendar (scheduling) │
│   Stripe (billing)  ·  SendGrid (email)                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## SECTION 3: EXACT TECH STACK

### Backend
- Runtime: Python 3.12
- API: FastAPI 0.111+
- Task queue: Celery 5 + Redis 7
- Real-time: WebSockets (FastAPI native)
- ORM: SQLAlchemy 2.0 async + Alembic migrations
- Background scheduler: APScheduler 4

### AI
- Primary LLM: Anthropic Claude claude-sonnet-4-20250514 (all reasoning)
- Embeddings: OpenAI text-embedding-3-large
- STT (speech-to-text): Deepgram Nova-2 (real-time streaming, best accuracy/latency)
- Orchestration: LangGraph (multi-agent workflows)
- Structured output: Instructor library (Pydantic-validated LLM responses)

### Databases
- PostgreSQL 16 — primary: orgs, users, meetings, surveys, decisions, outcomes
- Redis 7 — session cache, real-time meeting state, celery broker
- Pinecone — decision embeddings for semantic similarity search
- InfluxDB — participation time-series, speaking time metrics
- S3 — encrypted meeting audio (optional, user consent required)

### Frontend
- Framework: Next.js 14 App Router
- Styling: Tailwind CSS + shadcn/ui
- State: Zustand + TanStack Query
- Real-time: native WebSocket client
- Charts: Recharts

### Meeting Plugins
- Zoom: Zoom Apps SDK (runs in Zoom sidebar)
- Microsoft Teams: Teams App SDK + Bot Framework
- Google Meet: Chrome Extension (Meet doesn't have a native SDK)

### Infrastructure
- AWS: ECS Fargate + RDS PostgreSQL + ElastiCache Redis + S3
- IaC: Terraform
- CI/CD: GitHub Actions
- Monitoring: Datadog + Sentry
- Auth: Auth0 (SAML/SSO for enterprise)

---

## SECTION 4: COMPLETE DATA MODELS

### 4.1 Organization & Users

```python
class Organization(Base):
    __tablename__ = "organizations"
    id: UUID (PK)
    name: str
    domain: str                        # e.g. "acme.com" for SSO enforcement
    plan: Enum["starter","growth","enterprise"]
    seat_count: int
    stripe_customer_id: str
    created_at: datetime
    settings: JSONB                    # {meeting_platforms, recording_consent, ...}

class User(Base):
    __tablename__ = "users"
    id: UUID (PK)
    org_id: UUID (FK → organizations)
    auth0_id: str (unique)
    email: str
    role: Enum["admin","facilitator","member"]
    created_at: datetime
    # NOTE: No individual performance data ever stored here
    # Quorum is an org-level product, not individual surveillance
```

### 4.2 Meetings

```python
class Meeting(Base):
    __tablename__ = "meetings"
    id: UUID (PK)
    org_id: UUID (FK)
    created_by: UUID (FK → users)      # the facilitator
    title: str
    description: str
    scheduled_at: datetime
    platform: Enum["zoom","teams","meet","other"]
    platform_meeting_id: str           # external ID for SDK integration
    status: Enum["scheduled","survey_open","live","ended","post_mortem"]

    # Survey phase
    survey_sent_at: datetime (nullable)
    survey_deadline: datetime (nullable)
    survey_response_count: int
    survey_participant_count: int

    # Agenda
    agenda_items: JSONB                # [{title, duration_mins, type}]
    ai_generated_questions: JSONB      # generated from agenda before survey

    # Intelligence outputs
    tension_map: JSONB (nullable)      # generated after survey closes
    facilitator_brief: text (nullable) # generated after tension map
    live_transcript_id: str (nullable) # pointer to S3 or streaming store

    ended_at: datetime (nullable)
    created_at: datetime

class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"
    id: UUID (PK)
    meeting_id: UUID (FK)
    user_id: UUID (FK → users)
    role: Enum["facilitator","participant"]
    invited_at: datetime
    joined_at: datetime (nullable)
    left_at: datetime (nullable)
```

### 4.3 Survey System (Core of Phase 1)

```python
class SurveyResponse(Base):
    __tablename__ = "survey_responses"
    id: UUID (PK)
    meeting_id: UUID (FK)
    # CRITICAL: respondent_id is a one-way hash of user_id + meeting_id + secret
    # This means Quorum cannot link responses back to individuals
    # Even internal DB access cannot de-anonymize
    respondent_hash: str               # SHA256(user_id + meeting_id + ORG_SECRET)
    submitted_at: datetime

    responses: JSONB                   # [{question_id, question_text, answer, confidence}]
    # confidence: how strongly they hold this view (0.0-1.0)
    # This allows tension mapping even when surface answers agree

class TensionMap(Base):
    __tablename__ = "tension_maps"
    id: UUID (PK)
    meeting_id: UUID (FK, unique)
    generated_at: datetime

    consensus_areas: JSONB             # [{topic, agreement_score, summary}]
    tension_areas: JSONB               # [{topic, tension_score, perspectives}]
    missing_perspectives: JSONB        # what the AI thinks nobody is saying
    recommended_questions: JSONB       # [{question, why_important, ask_when}]
    response_rate: float
    confidence: float                  # how much the AI trusts this map (based on response rate)
```

### 4.4 Live Meeting Intelligence

```python
class LiveMeetingSession(Base):
    __tablename__ = "live_meeting_sessions"
    id: UUID (PK)
    meeting_id: UUID (FK, unique)
    started_at: datetime
    ended_at: datetime (nullable)

    # Speaking time (anonymized)
    speaking_time_distribution: JSONB  # [{participant_hash, seconds, percentage}]
    total_meeting_seconds: int

    # Intelligence signals detected
    hippo_events: JSONB               # [{timestamp, description, severity}]
    groupthink_events: JSONB          # [{timestamp, trigger, suggested_question}]
    tension_surfaced_events: JSONB    # [{timestamp, tension_topic, how_surfaced}]

    # Quorum interventions delivered
    interventions_delivered: JSONB    # [{timestamp, type, content, delivered_by}]

class LiveTranscriptChunk(Base):
    __tablename__ = "live_transcript_chunks"
    id: UUID (PK)
    session_id: UUID (FK → live_meeting_sessions)
    chunk_index: int
    start_seconds: int
    end_seconds: int
    # IMPORTANT: speaker is anonymized — never stored as user_id
    speaker_hash: str
    text: str
    embedding_id: str (nullable)       # Pinecone vector ID for semantic search
    created_at: datetime
```

### 4.5 Decision Library & Outcome Tracking

```python
class Decision(Base):
    __tablename__ = "decisions"
    id: UUID (PK)
    org_id: UUID (FK)
    meeting_id: UUID (FK, nullable)    # can create decisions outside meetings
    created_at: datetime

    title: str
    description: text
    domain: str                        # "product", "hiring", "strategy", "financial", etc.
    decision_type: str                 # "go/no-go", "selection", "prioritization", "commitment"

    # Context
    options_considered: JSONB          # [{option, rationale, pros, cons}]
    key_assumptions: JSONB             # what the team believed when deciding
    dissenting_views: JSONB            # what the anonymous data said (if any)
    confidence_at_decision: float      # team's stated confidence (0.0-1.0)

    # Post-mortem
    post_mortem_status: Enum["pending","completed","skipped"]
    post_mortem_completed_at: datetime (nullable)
    post_mortem_notes: text (nullable)

    # Scheduled outcome check-ins
    outcome_check_30d: datetime        # scheduled automatically
    outcome_check_90d: datetime
    outcome_check_180d: datetime

class DecisionOutcome(Base):
    __tablename__ = "decision_outcomes"
    id: UUID (PK)
    decision_id: UUID (FK)
    check_in_period: Enum["30d","90d","180d","adhoc"]
    recorded_at: datetime
    recorded_by: UUID (FK → users)

    outcome_verdict: Enum["correct","partially_correct","incorrect","too_early"]
    outcome_description: text
    what_we_got_right: text
    what_we_missed: text
    key_assumptions_that_failed: JSONB  # which of the original assumptions were wrong

    # For model training
    prediction_accuracy_score: float    # 0.0-1.0
    lessons_learned: text
```

### 4.6 Group Intelligence Profile

```python
class GroupIntelligenceProfile(Base):
    __tablename__ = "group_intelligence_profiles"
    id: UUID (PK)
    org_id: UUID (FK, unique)           # one per organization
    last_updated: datetime

    # Aggregate accuracy
    total_decisions_tracked: int
    decisions_with_outcomes: int
    overall_accuracy_score: float       # weighted average across all decisions

    # Pattern library — what this team does wrong
    identified_patterns: JSONB          # [{pattern_name, frequency, confidence, description, example_decision_ids}]
    # Examples:
    # "Overestimates timelines by avg 40%"
    # "Friday afternoon decisions have 60% lower accuracy"
    # "Hiring decisions for senior roles are consistently overconfident"
    # "Strategy decisions made under time pressure underperform by 35%"

    # Calibration scores by domain
    domain_accuracy: JSONB              # {"product": 0.72, "hiring": 0.55, "financial": 0.81}

    # Participation health
    avg_survey_response_rate: float
    avg_speaking_time_gini: float       # 0 = perfectly equal, 1 = one person talks only
    hippo_frequency_score: float        # how often HiPPO effect is detected
    groupthink_frequency_score: float

    # Suggested interventions
    recommended_practices: JSONB        # [{practice, why, based_on_pattern_id}]
```

---

## SECTION 5: THE AI INTELLIGENCE ENGINE

### 5.1 Survey Question Generator

Called 48 hours before each meeting. Takes the meeting agenda and generates anonymous survey questions.

```python
SURVEY_QUESTION_GENERATOR_PROMPT = """
You are Quorum's Survey Designer. Your job is to generate anonymous pre-meeting 
survey questions that surface what participants ACTUALLY think before social 
dynamics in the room shape their views.

Meeting context:
- Title: {meeting_title}
- Purpose: {meeting_description}
- Agenda items: {agenda_items}
- Team context: {org_context}

Generate 4-6 survey questions that:
1. Surface the key points of disagreement that will arise in this meeting
2. Are framed neutrally (no leading questions)
3. Include a confidence rating for each answer (0-10: how strongly do you hold this view?)
4. Include at least one "what are you worried nobody will say?" question
5. Include at least one "what would need to be true for you to change your mind?" question

Return JSON:
{
  "questions": [
    {
      "id": "q1",
      "text": "...",
      "type": "scale|multiple_choice|open_text",
      "options": [...] | null,
      "include_confidence": true|false,
      "why_this_question": "internal reasoning"
    }
  ]
}
"""
```

### 5.2 Tension Map Generator

Called after survey closes (minimum 50% response rate required).

```python
TENSION_MAP_GENERATOR_PROMPT = """
You are Quorum's Intelligence Analyst. You have received anonymous survey responses 
from meeting participants. Your job is to identify:

1. Where there is genuine consensus
2. Where there is hidden tension (including cases where surface answers agree 
   but confidence scores reveal uncertainty)
3. What critical perspectives appear to be missing from the conversation
4. What specific questions the facilitator should ask to surface the real issues

CRITICAL RULES:
- Never identify or hint at who said what
- Even if responses are distinctive, treat them as a collective
- Focus on ideas and tensions, not personalities
- Be direct about disagreements — do not soften them

Survey responses: {survey_responses_json}
Meeting context: {meeting_context}

Return JSON matching TensionMap schema.
"""
```

### 5.3 Live Meeting Intelligence Agent

The most technically complex component. Runs continuously during meetings.

```python
LIVE_INTELLIGENCE_SYSTEM_PROMPT = """
You are Quorum's Live Intelligence Agent. You are analyzing a meeting in real-time.

Your job is to detect the following signals and surface interventions at the right moment:

HIPPO EFFECT: One participant is speaking >40% of total time AND others have 
stopped contributing. Intervention: suggest a round-robin or direct question 
to quiet participants.

GROUPTHINK: Consensus forming in <8 minutes on a decision with >3 viable 
alternatives, OR universal agreement on something the pre-survey showed 
significant disagreement about. Intervention: surface the pre-survey tension.

MISSING PERSPECTIVE: A key concern from the pre-survey has not been mentioned 
after 60% of meeting time. Intervention: prompt facilitator with the question.

ASSUMPTION BLINDSPOT: A decision is about to be made with unstated assumptions. 
Intervention: surface the assumptions for explicit acknowledgment.

Pre-survey tension map: {tension_map}
Transcript so far: {transcript_context}
Speaking time distribution: {speaking_distribution}
Time elapsed / total scheduled: {time_context}

Respond only when a genuine intervention is warranted. False positives destroy trust.
If no intervention is needed: return {{"action": "monitor"}}
If intervention needed: return {{"action": "intervene", "type": "...", "message": "...", "urgency": "low|medium|high"}}
"""
```

### 5.4 Post-Mortem Generator

Called within 24 hours after meeting ends.

```python
POST_MORTEM_GENERATOR_PROMPT = """
You are Quorum's Post-Decision Analyst. A meeting has ended with the following 
decisions and context. Generate a structured post-mortem document that will:
1. Capture what was decided and why
2. Document the key assumptions made
3. Record dissenting views (anonymously)
4. Set up clear outcome measurement criteria
5. Schedule the right check-in questions for 30/90/180 days

Meeting summary: {meeting_summary}
Decisions made: {decisions_json}
Tension map (what the anonymous survey showed): {tension_map}
Live meeting intelligence events: {live_events}

The post-mortem should be honest about where the team showed warning signs 
(groupthink detected, HiPPO effect, low participation). This data is for 
the team's improvement, not for performance evaluation.
"""
```

### 5.5 Pattern Detector (Weekly Background Job)

```python
PATTERN_DETECTOR_PROMPT = """
You are Quorum's Pattern Analyst. Review this organization's decision history 
and outcome data. Identify statistically significant patterns in how this 
team makes decisions — specifically patterns that correlate with poor outcomes.

Decision and outcome history: {decision_history_json}
Group intelligence profile (current): {current_profile_json}

Look for:
1. Domain-specific overconfidence (where does this team think they're right but aren't?)
2. Temporal patterns (time of day, day of week, meeting length effects)
3. Participation patterns (does lower survey response rate predict worse outcomes?)
4. Decision type patterns (go/no-go vs. selection vs. strategy — where does this team struggle?)
5. Systematic blind spots (what topics consistently go unquestioned?)

Only surface patterns with at least 5 data points and p < 0.05 statistical significance.
Return updated GroupIntelligenceProfile patterns section as JSON.
"""
```

---

## SECTION 6: API SPECIFICATION

### Base URL: `https://api.quorum.ai/v1`

### Auth: Auth0 JWT. All requests: `Authorization: Bearer {token}`. Enterprise: SAML SSO.

```
# Organization management
GET    /org                          # get org profile
PATCH  /org                          # update settings
GET    /org/intelligence-profile     # group intelligence profile
GET    /org/decisions                # all decisions, paginated
GET    /org/patterns                 # detected patterns

# User management
GET    /users                        # list users (admin only)
POST   /users/invite                 # invite by email
DELETE /users/{id}                   # remove user

# Meeting lifecycle
POST   /meetings                     # create meeting
GET    /meetings                     # list meetings (upcoming + past)
GET    /meetings/{id}                # meeting detail
PATCH  /meetings/{id}                # update meeting
DELETE /meetings/{id}                # cancel

# Phase 1: Survey
POST   /meetings/{id}/survey/generate    # AI generates questions from agenda
GET    /meetings/{id}/survey             # get questions (for participants)
POST   /meetings/{id}/survey/respond     # submit anonymous response
GET    /meetings/{id}/survey/status      # response rate (admin)
POST   /meetings/{id}/tension-map/generate  # trigger after survey closes
GET    /meetings/{id}/tension-map        # get tension map (facilitator only)
GET    /meetings/{id}/facilitator-brief  # formatted brief for facilitator

# Phase 2: Live meeting
POST   /meetings/{id}/session/start      # begin live session
WS     /meetings/{id}/session/stream     # real-time transcript + intelligence feed
POST   /meetings/{id}/session/end        # end live session
GET    /meetings/{id}/session/summary    # live session summary

# Phase 3: Decision & outcomes
POST   /meetings/{id}/decisions          # create decision from meeting
GET    /decisions/{id}                   # decision detail
PATCH  /decisions/{id}                   # update decision
POST   /decisions/{id}/post-mortem       # submit post-mortem
POST   /decisions/{id}/outcomes          # record outcome check-in
GET    /decisions/{id}/outcomes          # get all outcome check-ins

# Intelligence
GET    /intelligence/patterns            # org patterns
GET    /intelligence/domain/{domain}     # domain-specific intelligence
GET    /intelligence/calibration         # prediction accuracy breakdown
```

### WebSocket Events (`/meetings/{id}/session/stream`)

```javascript
// Server → Client
{type: "transcript_chunk", data: {speaker_hash, text, timestamp}}
{type: "intelligence_alert", data: {type, message, urgency, action_suggestion}}
{type: "speaking_distribution_update", data: {distribution: [{hash, seconds, pct}]}}
{type: "session_ended", data: {summary}}

// Client → Server
{type: "acknowledge_alert", data: {alert_id}}
{type: "mark_decision", data: {title, description, timestamp}}
{type: "request_suggested_question", data: {context}}
```

---

## SECTION 7: REAL-TIME PIPELINE (MEETING PHASE)

```
Meeting audio (Zoom/Teams/Meet)
    │
    ▼
Deepgram WebSocket (STT, ~300ms latency)
    │
    ▼ transcript chunks (every ~3 seconds)
Speaker Diarization (who is speaking, anonymized hash)
    │
    ├──▶ InfluxDB: speaking_time_series (per speaker_hash, per chunk)
    │
    ├──▶ Redis: rolling_transcript_buffer (last 10 minutes, sliding window)
    │
    └──▶ Intelligence Evaluation (every 30 seconds):
            1. Check speaking distribution → HiPPO alert?
            2. Diff against tension_map → Missing perspective?
            3. Check consensus velocity → Groupthink alert?
            4. LLM call to LIVE_INTELLIGENCE_AGENT with context
            5. If intervention warranted → push to WebSocket → client UI
```

### Speaker Anonymization
```python
def anonymize_speaker(zoom_participant_id: str, meeting_id: str) -> str:
    """
    One-way hash. Cannot be reversed.
    Same participant gets same hash within a meeting (for speaking time tracking).
    Different hash across different meetings (no cross-meeting tracking).
    """
    secret = settings.SPEAKER_HASH_SECRET  # rotated monthly
    return hashlib.sha256(
        f"{zoom_participant_id}:{meeting_id}:{secret}".encode()
    ).hexdigest()[:16]
```

---

## SECTION 8: BUILD ORDER

Build and deploy each phase independently. Phase 1 has standalone value.

### Phase 1A: Foundation (Weeks 1–2)
1. PostgreSQL schema + Alembic migrations (all models from Section 4)
2. FastAPI scaffold + Auth0 integration
3. Organization + User CRUD
4. Basic Next.js app with auth flow

### Phase 1B: Survey Engine (Weeks 3–5)
1. Meeting CRUD endpoints
2. Survey question generator (LLM prompt + Instructor structured output)
3. Anonymous response submission (with anonymization)
4. Tension map generator
5. Facilitator brief generator
6. Survey UI (participant view + facilitator view)
7. Email notifications via SendGrid

**Milestone: Deploy and sell Phase 1 only. This is already a valuable product.**

### Phase 2A: Meeting Integration (Weeks 6–9)
1. Deepgram WebSocket integration (STT pipeline)
2. Speaker diarization + anonymization
3. InfluxDB time-series for speaking metrics
4. Redis rolling transcript buffer
5. Basic WebSocket server for real-time events
6. Zoom Apps SDK integration (sidebar app)

### Phase 2B: Live Intelligence (Weeks 10–12)
1. HiPPO detector (speaking time threshold logic)
2. Groupthink detector (consensus velocity + survey divergence check)
3. Missing perspective detector (tension map vs. transcript semantic comparison)
4. Live Intelligence Agent (LLM evaluation every 30 seconds)
5. Intervention delivery to client UI
6. Teams Bot Framework integration
7. Google Meet Chrome Extension

**Milestone: Full Phase 1 + Phase 2. Core product complete.**

### Phase 3: Decision Library & Outcomes (Weeks 13–15)
1. Decision creation + tagging
2. Post-mortem generator
3. Outcome check-in scheduler (Celery Beat)
4. Outcome recording UI
5. Basic accuracy scoring

### Phase 4: Group Intelligence Profile (Weeks 16–18)
1. Pattern detector (weekly background job)
2. Group intelligence profile computation
3. Intelligence dashboard (Next.js)
4. Domain-specific calibration scores
5. Pinecone integration for decision similarity search

### Phase 5: Production (Weeks 19–22)
1. Terraform AWS infrastructure
2. GitHub Actions CI/CD
3. Datadog monitoring + Sentry error tracking
4. SOC 2 Type II controls implementation
5. SAML/SSO (Auth0 enterprise)
6. Stripe billing + seat management
7. Beta → GA launch

---

## SECTION 9: ENVIRONMENT VARIABLES

```env
APP_ENV=production
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

# AI
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
PINECONE_API_KEY=...
PINECONE_INDEX=quorum-decisions
DEEPGRAM_API_KEY=...

# Meeting platforms
ZOOM_CLIENT_ID=...
ZOOM_CLIENT_SECRET=...
ZOOM_WEBHOOK_SECRET=...
TEAMS_APP_ID=...
TEAMS_APP_PASSWORD=...

# Anonymization (rotate monthly)
SPEAKER_HASH_SECRET=<openssl rand -hex 32>
RESPONDENT_HASH_SECRET=<openssl rand -hex 32>

# Comms
SENDGRID_API_KEY=...
SENDGRID_FROM_EMAIL=hello@quorum.ai
SLACK_BOT_TOKEN=...

# Storage
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
S3_BUCKET=quorum-recordings

# Billing
STRIPE_SECRET_KEY=...
STRIPE_WEBHOOK_SECRET=...
```

---

## SECTION 10: PRIVACY ARCHITECTURE

This is a B2B product. The privacy model is fundamentally different from consumer apps.

### What is NEVER stored
- Individual survey responses linked to a named person
- Individual speaking time linked to a named person
- Any performance data used for individual evaluation
- Audio recordings (unless org explicitly enables with consent flow)

### What IS stored
- Anonymous survey responses (one-way hash, cannot be reversed)
- Speaking time per anonymous speaker hash (resets per meeting)
- Organization-level aggregate patterns
- Decision history and outcomes (org-level, not attributed to individuals)

### Compliance
- SOC 2 Type II: architecture designed for it from day 1
- GDPR: anonymization at collection point satisfies data minimization
- No PHI/HIPAA concerns (no health data)
- Standard enterprise DPA available

### Deletion
- Org can delete all data instantly via API
- Individual users have no deletion rights (no personal data exists to delete)
- Audio recordings (if enabled): deleted after 30 days unless org extends

---

*This is the complete specification. Every file in this package elaborates one section.*

# QUORUM — Technical Architecture
## Complete system design, infrastructure, and engineering decisions

---

## 1. Architecture Philosophy

Three guiding principles:

**1. Privacy by default, not by configuration.** Anonymization happens at the point of data collection. It is not a setting. It cannot be turned off by admins. The system is architecturally incapable of re-identifying anonymous survey responses.

**2. Fail silent in live meetings.** A Quorum outage during a meeting must not disrupt the meeting. The Zoom/Teams/Meet call continues; Quorum simply stops providing intelligence. This is achieved through circuit breakers on all real-time components.

**3. Phase 1 (survey) has no runtime dependencies on Phase 2 (live AI).** A team can use Quorum's survey and tension mapping forever without ever using the live meeting feature. This means the core value proposition is available without the hardest infrastructure to build.

---

## 2. System Components

### 2.1 API Server (FastAPI)

```
app/
├── main.py                    # FastAPI app factory
├── api/
│   ├── auth.py               # Auth0 JWT verification middleware
│   ├── routers/
│   │   ├── orgs.py
│   │   ├── users.py
│   │   ├── meetings.py
│   │   ├── surveys.py
│   │   ├── sessions.py       # live meeting WebSocket
│   │   ├── decisions.py
│   │   ├── outcomes.py
│   │   └── intelligence.py
├── models/                    # SQLAlchemy models (see schema doc)
├── schemas/                   # Pydantic schemas (request/response)
├── services/
│   ├── survey_service.py      # question generation, response storage
│   ├── tension_map_service.py # tension map + facilitator brief
│   ├── stt_service.py         # Deepgram WebSocket management
│   ├── intelligence_service.py # live AI agent orchestration
│   ├── decision_service.py
│   ├── outcome_service.py
│   └── pattern_service.py    # Group Intelligence Profile computation
├── workers/
│   ├── celery_app.py
│   ├── tasks/
│   │   ├── send_survey_invitations.py
│   │   ├── generate_tension_map.py
│   │   ├── schedule_outcome_checkins.py
│   │   ├── run_pattern_detector.py   # weekly
│   │   └── cleanup_expired_data.py
├── intelligence/
│   ├── agents/
│   │   ├── survey_designer.py
│   │   ├── tension_analyst.py
│   │   ├── live_agent.py
│   │   ├── post_mortem_generator.py
│   │   └── pattern_detector.py
│   └── prompts.py             # all LLM prompts centralized
└── core/
    ├── config.py              # settings from env
    ├── database.py            # async SQLAlchemy engine
    ├── security.py            # JWT, hashing, encryption utilities
    └── exceptions.py
```

### 2.2 Background Workers (Celery)

```
Workers:
  survey-worker     (2 instances) — handles email sends, survey generation
  intelligence-worker (4 instances) — handles tension maps, post-mortems, patterns
  
Queues:
  default           — general tasks
  high-priority     — tension map generation (facilitators waiting)
  scheduled         — outcome check-ins, pattern detector (weekly)
  
Beat schedule:
  - pattern_detector: every Sunday 03:00 UTC
  - cleanup_expired_audio: daily 02:00 UTC
  - send_outcome_checkins: daily 09:00 UTC (per org timezone)
```

### 2.3 Real-Time Meeting Pipeline

This is the most complex component. Full detail:

```python
# stt_service.py
class MeetingStreamProcessor:
    """
    Manages the real-time pipeline for a single meeting session.
    Lifecycle: start() → process_chunks() → end()
    """

    def __init__(self, session_id: str, meeting_id: str, tension_map: dict):
        self.session_id = session_id
        self.meeting_id = meeting_id
        self.tension_map = tension_map

        # Deepgram WebSocket connection
        self.dg_connection = None

        # Rolling transcript buffer (last 10 minutes)
        self.transcript_buffer = collections.deque(maxlen=200)  # ~10 min at avg pace

        # Speaking time tracker
        self.speaking_seconds: dict[str, int] = {}  # speaker_hash → seconds
        self.total_seconds = 0

        # Intelligence evaluation state
        self.last_evaluation_at = 0
        self.alerts_delivered: list[dict] = []
        self.hippo_alerts_count = 0
        self.missing_perspective_alerts_count = 0

    async def start(self):
        self.dg_connection = await self._connect_deepgram()
        asyncio.create_task(self._intelligence_evaluation_loop())

    async def _on_transcript_chunk(self, result: dict):
        """Called by Deepgram callback for each chunk."""
        speaker_id = result.get("speaker", "unknown")
        speaker_hash = anonymize_speaker(speaker_id, self.meeting_id)
        text = result["channel"]["alternatives"][0]["transcript"]
        duration = result["duration"]

        # Update speaking time
        self.speaking_seconds[speaker_hash] = \
            self.speaking_seconds.get(speaker_hash, 0) + duration
        self.total_seconds += duration

        # Store chunk
        chunk = TranscriptChunk(
            session_id=self.session_id,
            speaker_hash=speaker_hash,
            text=text,
            start_seconds=int(result["start"]),
            end_seconds=int(result["start"] + duration),
        )
        self.transcript_buffer.append(chunk)
        await db.save(chunk)

        # Push to WebSocket clients
        await ws_manager.broadcast(self.session_id, {
            "type": "transcript_chunk",
            "data": {"speaker_hash": speaker_hash, "text": text}
        })

    async def _intelligence_evaluation_loop(self):
        """Runs every 30 seconds. Evaluates current state for alerts."""
        while self.session_active:
            await asyncio.sleep(30)
            now = time.time()

            # Don't evaluate in first 5 minutes (too little signal)
            if self.total_seconds < 300:
                continue

            alert = await self._evaluate_intelligence()
            if alert and alert["action"] == "intervene":
                await self._deliver_alert(alert)

    async def _evaluate_intelligence(self) -> dict | None:
        """Single LLM call to evaluate current meeting state."""
        # Check HiPPO (rule-based, fast) before hitting LLM
        hippo_alert = self._check_hippo()
        if hippo_alert and self.hippo_alerts_count < 2:
            return hippo_alert

        # LLM evaluation for groupthink + missing perspective
        transcript_context = " ".join(
            [f"{c.speaker_hash[:4]}: {c.text}" for c in list(self.transcript_buffer)[-40:]]
        )

        response = await claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            messages=[{
                "role": "user",
                "content": LIVE_INTELLIGENCE_PROMPT.format(
                    tension_map=self.tension_map,
                    transcript_context=transcript_context,
                    speaking_distribution=self._get_distribution(),
                    time_context=f"{self.total_seconds//60}min elapsed",
                    alerts_so_far=self.alerts_delivered[-3:]
                )
            }]
        )
        return json.loads(response.content[0].text)

    def _check_hippo(self) -> dict | None:
        if self.total_seconds < 300:
            return None
        for speaker, seconds in self.speaking_seconds.items():
            pct = seconds / self.total_seconds
            if pct > 0.40:
                return {
                    "action": "intervene",
                    "type": "hippo",
                    "urgency": "medium",
                    "message": f"One voice has taken {int(pct*100)}% of speaking time. Consider directly inviting others."
                }
        return None
```

### 2.4 Frontend Architecture (Next.js 14)

```
app/
├── (auth)/
│   ├── login/page.tsx
│   └── callback/page.tsx
├── (app)/
│   ├── layout.tsx            # sidebar nav, auth guard
│   ├── dashboard/page.tsx    # upcoming meetings + intelligence summary
│   ├── meetings/
│   │   ├── page.tsx          # meeting list
│   │   ├── new/page.tsx      # create meeting
│   │   └── [id]/
│   │       ├── page.tsx      # meeting overview
│   │       ├── survey/page.tsx     # participant survey view
│   │       ├── brief/page.tsx      # facilitator brief (tension map)
│   │       ├── live/page.tsx       # live meeting intelligence sidebar
│   │       └── decisions/page.tsx  # post-meeting decisions
│   ├── decisions/
│   │   ├── page.tsx          # decision library
│   │   └── [id]/page.tsx     # decision detail + outcomes
│   └── intelligence/page.tsx # group intelligence profile
├── api/                      # Next.js API routes (thin proxies to FastAPI)
└── components/
    ├── ui/                   # shadcn/ui components
    ├── survey/               # SurveyForm, QuestionCard, ConfidenceSlider
    ├── tension-map/          # TensionMap, ConsensusArea, TensionArea
    ├── live/                 # SpeakingDistribution, AlertPanel, TranscriptFeed
    ├── decisions/            # DecisionCard, OutcomeForm, PostMortemView
    └── intelligence/         # GroupProfile, PatternCard, CalibrationChart
```

---

## 3. Database Design

### 3.1 PostgreSQL — Indexing Strategy

```sql
-- High-read indexes
CREATE INDEX idx_meetings_org_status ON meetings(org_id, status);
CREATE INDEX idx_meetings_scheduled ON meetings(scheduled_at) WHERE status = 'scheduled';
CREATE INDEX idx_survey_responses_meeting ON survey_responses(meeting_id);
CREATE INDEX idx_decisions_org_domain ON decisions(org_id, domain);
CREATE INDEX idx_decision_outcomes_decision ON decision_outcomes(decision_id);
CREATE INDEX idx_transcript_chunks_session ON live_transcript_chunks(session_id, chunk_index);

-- GIN index for JSONB search
CREATE INDEX idx_decisions_assumptions ON decisions USING GIN(key_assumptions);
CREATE INDEX idx_gip_patterns ON group_intelligence_profiles USING GIN(identified_patterns);
```

### 3.2 Redis Key Schema

```
# Session state (TTL: 4 hours)
quorum:session:{session_id}:state          → JSON (session metadata)
quorum:session:{session_id}:speaking       → Hash (speaker_hash → seconds)
quorum:session:{session_id}:alerts         → List (delivered alert IDs)

# WebSocket connections (TTL: 4 hours)
quorum:ws:{session_id}:connections         → Set (connection IDs)

# Rate limiting
quorum:ratelimit:{org_id}:{endpoint}       → Counter (TTL: 60s)

# Survey response lock (prevents race condition on response count)
quorum:survey:{meeting_id}:lock            → Lock (TTL: 5s)

# LLM response cache (tension maps — same inputs, same output)
quorum:llm:tension:{meeting_id}            → JSON (TTL: 1 hour)
```

### 3.3 InfluxDB Measurements

```
# Speaking time series
measurement: speaking_time
tags: org_id, meeting_id, session_id, speaker_hash
fields: seconds_speaking (float)
timestamp: unix nanoseconds

# Intelligence events
measurement: intelligence_events
tags: org_id, meeting_id, event_type (hippo|groupthink|missing_perspective)
fields: severity (int), resolved (bool)
timestamp: unix nanoseconds

# Survey metrics
measurement: survey_metrics
tags: org_id, meeting_id
fields: response_count (int), response_rate (float)
timestamp: unix nanoseconds
```

---

## 4. Integration Architecture

### 4.1 Zoom Integration

```python
# Zoom Apps SDK — runs as sidebar app in Zoom client
# Backend: Zoom Webhook events

ZOOM_WEBHOOK_EVENTS = [
    "meeting.started",     # → trigger: create live session, join audio
    "meeting.ended",       # → trigger: end session, start post-mortem generation
    "meeting.participant_joined",   # → update participant list
    "meeting.participant_left",
]

class ZoomIntegrationService:
    async def handle_meeting_started(self, payload: dict):
        meeting_id = await self._find_quorum_meeting(payload["object"]["id"])
        if not meeting_id:
            return  # not a tracked meeting

        session = await self._create_session(meeting_id)
        # Join meeting audio via Zoom RTMP or participant join
        await self._start_audio_stream(session.id, payload["object"]["join_url"])

    async def _start_audio_stream(self, session_id: str, join_url: str):
        """
        Zoom doesn't provide a direct audio API for sidebar apps.
        Approach: bot participant joins the meeting and streams audio.
        Uses Zoom's Meeting SDK + a headless Chrome bot that joins as participant.
        Audio piped to Deepgram via WebSocket.
        """
        processor = MeetingStreamProcessor(session_id, ...)
        await processor.start()
```

### 4.2 Calendar Integration (Google/Outlook)

```python
class CalendarService:
    async def sync_upcoming_meetings(self, org_id: str, user_id: str):
        """
        Pull upcoming meetings from Google Calendar / Outlook.
        For each meeting with >= 3 participants, suggest creating a Quorum survey.
        Never auto-create without explicit user action.
        """
        events = await self._fetch_calendar_events(user_id, days_ahead=7)
        suggestions = []
        for event in events:
            if len(event.attendees) >= 3 and not await self._already_tracked(event.id):
                suggestions.append({
                    "title": event.summary,
                    "scheduled_at": event.start,
                    "participants": len(event.attendees),
                    "calendar_id": event.id
                })
        return suggestions
```

---

## 5. Security Architecture

### 5.1 Authentication Flow

```
1. User visits app.quorum.ai
2. Redirected to Auth0 (PKCE flow for web, device code for CLI)
3. Auth0 returns JWT access token (RS256 signed, 1-hour expiry)
4. Token includes: sub, org_id, role, email
5. API validates JWT on every request
6. Refresh token (7 days) stored in httpOnly cookie
7. Enterprise: SAML2 IdP configured in Auth0, SSO enforced per org domain
```

### 5.2 API Key Authentication (for integrations)

```python
class APIKey(Base):
    __tablename__ = "api_keys"
    id: UUID (PK)
    org_id: UUID (FK)
    key_hash: str           # bcrypt hash of the actual key
    name: str               # "Zoom Integration", "Slack Bot", etc.
    scopes: List[str]       # ["meetings:read", "sessions:write"]
    last_used_at: datetime (nullable)
    expires_at: datetime (nullable)
    created_by: UUID (FK → users)
    created_at: datetime
```

### 5.3 Anonymization Implementation

```python
import hashlib
import hmac

def anonymize_respondent(user_id: str, meeting_id: str) -> str:
    """
    Creates a one-way anonymous identifier for survey respondents.
    
    Properties:
    - Deterministic: same user+meeting always gets same hash
    - Irreversible: cannot get user_id from hash
    - Meeting-scoped: same user gets different hash in different meetings
    - Org-secret protected: even with DB access, cannot reverse without secret
    
    The org_secret is stored in AWS Secrets Manager, not in the database.
    It is rotated annually. Old responses remain anonymized after rotation.
    """
    secret = settings.RESPONDENT_HASH_SECRET.encode()
    message = f"{user_id}:{meeting_id}".encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()[:20]

def anonymize_speaker(speaker_platform_id: str, meeting_id: str) -> str:
    """
    Same pattern for speaker anonymization in live transcripts.
    Meeting-scoped so same person gets different hash in different meetings.
    """
    secret = settings.SPEAKER_HASH_SECRET.encode()
    message = f"{speaker_platform_id}:{meeting_id}".encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()[:16]
```

---

## 6. Scalability Design

### 6.1 Load Profile

- Survey submissions: bursty (all participants submit near deadline) — 100 req/sec peak per large org
- Live meeting intelligence: continuous, latency-sensitive — 1 LLM call per 30 sec per active session
- Tension map generation: compute-heavy, async — 30 sec LLM call, user waits
- Pattern detector: weekly batch job — can take hours, not user-facing

### 6.2 Scaling Strategy

```
API servers:        ECS Fargate, auto-scale on CPU + request queue depth
                    Min: 2 tasks, Max: 20 tasks
                    Scale-out trigger: CPU > 70% for 2 min

Survey workers:     2 instances always on (email sends are time-sensitive)

Intelligence workers: 4 instances, scale on Celery queue depth
                    Each instance handles up to 3 concurrent live meetings
                    Scale-out trigger: queue depth > 10 tasks

PostgreSQL:         RDS r7g.xlarge (primary) + r7g.large read replica
                    Read replica handles all GET requests via pgBouncer

Redis:              ElastiCache r7g.large (cluster mode off for simplicity)
                    Upgrade to cluster mode at 1,000+ concurrent meetings

Deepgram:           API calls scale infinitely (Deepgram handles this)
                    Rate limit: 100 concurrent streaming connections (Deepgram Growth plan)
                    Upgrade to Enterprise plan at 50+ concurrent meetings

LLM (Claude):       Rate limited by Anthropic tier
                    Starter: 40 req/min (sufficient for ~80 concurrent meetings)
                    Scale: request higher tier via Anthropic API console
```

### 6.3 Multi-Tenancy

All data is org-scoped at the PostgreSQL level via `org_id` foreign key on every table. Row-level security (RLS) enforced in PostgreSQL:

```sql
-- RLS policy example
ALTER TABLE meetings ENABLE ROW LEVEL SECURITY;
CREATE POLICY meetings_org_isolation ON meetings
    USING (org_id = current_setting('app.current_org_id')::UUID);
```

The `app.current_org_id` is set from the JWT token in FastAPI middleware before every query, ensuring no cross-org data leakage even if there's a bug in application-level filtering.

---

## 7. Deployment

### 7.1 AWS Architecture

```
Region: us-east-1 (primary), eu-west-1 (GDPR)

VPC:
  Private subnets: API servers, workers, RDS, Redis, InfluxDB
  Public subnets: ALB (Application Load Balancer), NAT Gateway

Services:
  ECS Fargate:    API + workers
  RDS:            PostgreSQL 16 Multi-AZ
  ElastiCache:    Redis 7
  S3:             Audio recordings (optional), static assets
  CloudFront:     CDN for Next.js static
  ALB:            HTTPS termination, WAF rules
  Route53:        DNS (api.quorum.ai, app.quorum.ai)
  Secrets Manager: all secrets (never in env files in production)
  CloudWatch:     Logs + alarms
```

### 7.2 CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - pytest (unit + integration)
      - mypy (type checking)
      - ruff (linting)
      - bandit (security scanning)

  build:
    needs: test
    steps:
      - Docker build API image
      - Docker build worker image
      - Push to ECR

  deploy-staging:
    needs: build
    steps:
      - Terraform plan
      - ECS deploy to staging
      - Smoke tests against staging

  deploy-prod:
    needs: deploy-staging
    environment: production  # requires manual approval
    steps:
      - Terraform apply
      - ECS rolling deploy (blue/green)
      - Datadog deployment marker
```

---

## 8. Observability

### 8.1 Key Metrics (Datadog)

```python
# Business metrics
quorum.surveys.sent                # counter, tags: org_id
quorum.surveys.response_rate       # gauge, tags: org_id, meeting_id
quorum.tension_maps.generated      # counter, tags: org_id
quorum.live_sessions.active        # gauge
quorum.alerts.delivered            # counter, tags: type (hippo|groupthink|missing)
quorum.alerts.actioned             # counter, tags: type, actioned (true|false)
quorum.decisions.tracked           # counter, tags: org_id, domain
quorum.outcomes.recorded           # counter, tags: verdict

# Technical metrics
quorum.api.latency                 # p50/p95/p99, tags: endpoint
quorum.stt.latency                 # Deepgram response time
quorum.llm.latency                 # Claude API response time, tags: prompt_type
quorum.llm.cost                    # estimated USD, tags: prompt_type
quorum.websocket.connections       # gauge
quorum.celery.queue_depth          # gauge, tags: queue_name
```

### 8.2 Alerts

```
CRITICAL (page on-call):
  - API error rate > 1% for 2 minutes
  - RDS connection pool exhausted
  - Any live meeting session crash
  - WebSocket broadcast failure

WARNING (Slack notification):
  - LLM latency p95 > 5 seconds
  - Celery queue depth > 50
  - Survey generation failure
  - Deepgram STT error rate > 5%
```

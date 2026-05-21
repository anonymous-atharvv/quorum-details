# QUORUM — MASTER AI BUILD PROMPT v3.0
## Complete Production Build Specification | Bug Fixes + V2 Features + Working Meeting Workflow

> **HOW TO USE**: Feed this entire document as the system context to any frontier AI coding agent (Claude Code, Cursor, GPT-4o). Every architectural decision, data model, AI behavior, API contract, bug fix, and new V2 feature is defined here. Build in the exact sequence in Section 16. Do not deviate. Do not simplify.

---

## CRITICAL FIXES FROM V1 (Read Before Anything Else)

These bugs exist in the current codebase and MUST be fixed first:

### BUG FIX 1 — Double `_intelligence_evaluation_loop` definition in `stt_service.py`
```python
# BROKEN (current code has this method defined twice):
async def _intelligence_evaluation_loop(self):
    if self._eval_task is None:
        self._eval_task = asyncio.create_task(self._intelligence_evaluation_loop())

async def _intelligence_evaluation_loop(self):  # ← DUPLICATE — Python uses only last def
    while self.session_active: ...

# FIXED:
async def start(self):
    self.session_active = True
    self._eval_task = asyncio.create_task(self._intelligence_evaluation_loop())

async def _intelligence_evaluation_loop(self):
    while self.session_active:
        await asyncio.sleep(30)
        if self.total_seconds < 300:
            continue
        alert = await self._evaluate()
        if alert and alert.get("action") == "intervene":
            await self._deliver_alert(alert)
```

### BUG FIX 2 — `hmac.new()` does not exist; correct call is `hmac.new()`
```python
# BROKEN (current code):
return hmac.new(secret, message, hashlib.sha256).hexdigest()[:20]

# FIXED:
return hmac.new(secret, message, digestmod=hashlib.sha256).hexdigest()[:20]
# NOTE: `hmac.new` is correct — the keyword arg `digestmod=` is required in Python 3.x
# Double-check: the existing code in backend/app/core/security.py already uses digestmod=
# Verify all call sites across the codebase use digestmod= explicitly
```

### BUG FIX 3 — `meetings.py` router imports `random` and `string` for mock IDs but fails in production
```python
# REMOVE from production router — mock join URLs must come from real platform SDK
# The `backend/app/api/routers/meetings.py` (the extended version, not the covered version)
# imports random, string, uuid and generates fake Zoom/Teams/Meet URLs.
# This must be replaced with:
# 1. A proper platform integration service
# 2. Or a configurable mock that is disabled in production via APP_ENV check

# FIXED: Create app/services/platform_service.py
class PlatformService:
    async def get_join_url(self, platform: str, meeting_id: str, org_id: str) -> str:
        if settings.APP_ENV == "development":
            return f"https://meet.example.com/dev-{meeting_id[:8]}"
        # Phase 2A: real SDK integration
        match platform:
            case "zoom":
                return await self._zoom_create_meeting(org_id)
            case "teams":
                return await self._teams_create_meeting(org_id)
            case _:
                return f"https://app.quorum.ai/join/{meeting_id}"
```

### BUG FIX 4 — `TopBar.tsx` uses `localStorage` for auth token — breaks SSR
```typescript
// BROKEN: localStorage access during server render causes hydration mismatch
useEffect(() => {
  const userStr = localStorage.getItem("user");  // ← runs on server = crash

// FIXED: Guard all localStorage access behind typeof window check
const [userName, setUserName] = useState("User");
useEffect(() => {
  if (typeof window === "undefined") return;
  const userStr = localStorage.getItem("user");
  if (userStr) {
    try { const user = JSON.parse(userStr); if (user.name) setUserName(user.name); }
    catch {}
  }
}, []);
```

### BUG FIX 5 — `live/page.tsx` uses hardcoded mock speakers array as fallback, polluting real data
```typescript
// BROKEN: when liveSpeakers is empty, falls back to hardcoded mock
{(liveSpeakers.length > 0 ? liveSpeakers : speakers).map(...)}
// This means the UI always shows fake data until real WS data arrives

// FIXED: Show loading state instead of fake data
{liveSpeakers.length > 0 ? (
  liveSpeakers.map(s => <SpeakerBar key={s.hash} speaker={s} />)
) : (
  <div className="text-xs text-on-surface-muted italic">
    Waiting for participants to speak...
  </div>
)}
```

### BUG FIX 6 — `app_main.py` references `_scrub_sensitive_data` before definition
```python
# BROKEN:
sentry_sdk.init(..., before_send=_scrub_sensitive_data)  # used before defined

def _scrub_sensitive_data(event, hint): ...  # defined after usage

# FIXED: Move _scrub_sensitive_data definition above the sentry_sdk.init() call
```

### BUG FIX 7 — `set_rls_org_id` in `database.py` accepts `str` but `auth.py` passes `UUID`
```python
# BROKEN: Type mismatch causes silent failure in some drivers
async def set_rls_org_id(session: AsyncSession, org_id: str) -> None:
    await session.execute(text("SET LOCAL app.current_org_id = :org_id"), {"org_id": str(org_id)})

# FIXED: Accept Union[str, UUID] and always coerce to str
from uuid import UUID
async def set_rls_org_id(session: AsyncSession, org_id: str | UUID) -> None:
    if "sqlite" in database_url:
        return
    await session.execute(
        text("SET LOCAL app.current_org_id = :org_id"),
        {"org_id": str(org_id)}
    )
```

### BUG FIX 8 — Survey token endpoint missing `APP_URL` setting
```python
# BROKEN: settings.APP_URL referenced in email_service.py but not in config.py
# FIXED: Add to Settings class in config.py
APP_URL: str = "http://localhost:3000"  # override in production
```

### BUG FIX 9 — WebSocket stream endpoint allows no-token connections for participant view
```python
# BROKEN: /live/[id]/page.tsx connects without token, server closes with 4401
# The participant anonymous view (no-auth) should use a separate public WS endpoint

# FIXED: Add public read-only WebSocket endpoint for participant speaking distribution
@router.websocket("/meetings/{meeting_id}/session/public-stream")
async def public_stream(websocket: WebSocket, meeting_id: str):
    """Read-only, no auth — only broadcasts speaking_update events."""
    await websocket.accept()
    # subscribe to Redis pub/sub for this session, forward speaking_update only
    # no transcript_chunk, no intelligence_alert (facilitator-only)
```

### BUG FIX 10 — `intelligence/page.tsx` crashes when `profile.meeting_health` fields are 0
```typescript
// BROKEN:
value: `${profile.meeting_health.avg_survey_response_rate}%`
// If avg_survey_response_rate = 0, shows "0%" not "N/A"
// If avg_survey_response_rate = null, shows "null%"

// FIXED:
value: profile.meeting_health?.avg_survey_response_rate
  ? `${Math.round(profile.meeting_health.avg_survey_response_rate * 100)}%`
  : "N/A"
```

---

## SECTION 1: IDENTITY & MISSION

**QUORUM** — Collective Intelligence Platform. A B2B AI platform that makes organizational group decisions measurably better by combining pre-meeting anonymous elicitation, real-time meeting intelligence, and longitudinal outcome tracking with compounding intelligence that builds over time.

**Core Problem**: Organizations lose $37B annually in the US to social dynamics failures in meetings:
- HiPPO Effect (highest-paid opinion dominates)
- Groupthink (social pressure kills dissent)
- Information Pooling Failure (people know the answer but won't say it)
- Anchoring Bias (first speaker frames everything)

Every existing tool (Otter.ai, Fireflies, Slido) solves **efficiency**. Quorum solves **decision quality**.

**What Quorum Is NOT**: transcription tool, task manager, performance evaluation tool, individual surveillance system.

---

## SECTION 2: V2 NEW FEATURES (Build After Bug Fixes)

### V2 Feature 1: Real-Time Meeting Workflow (COMPLETE END-TO-END)

This is the most critical V2 addition. The meeting workflow must work end-to-end without mocks.

#### Working Meeting Workflow — Full State Machine

```
MEETING STATES:
draft → survey_open → survey_closed → live → ended → post_mortem_pending → post_mortem_done

COMPLETE WORKFLOW:

Step 1: MEETING CREATION
  Facilitator → POST /meetings → {title, agenda_items, participant_emails, platform, scheduled_at}
  System → creates Meeting(status=draft)
  System → creates MeetingParticipant for each email with unique survey_token
  System → sends survey invitation emails via SendGrid (or logs in dev)
  System → creates in-app Notification for each participant
  Response → meeting object with id

Step 2: SURVEY GENERATION (AI)
  Facilitator → POST /meetings/{id}/survey/generate
  System → calls SurveyDesignerAgent with agenda_items + org_context
  System → stores generated_questions in meeting
  System → updates meeting.status = "survey_open"
  System → sends survey emails to all participants
  Response → {job_id, status: "completed", questions: [...]}

Step 3: PARTICIPANT SURVEY SUBMISSION (No Auth Required)
  Participant → GET /meetings/{id}/survey?token={token}  ← verify token, return questions
  Participant → POST /meetings/{id}/survey/respond (X-Survey-Token header)
  System → anonymize_respondent(user_id, meeting_id)
  System → upsert SurveyResponse (allow updates until deadline)
  System → increment meeting.survey_response_count via DB trigger
  System → check: if response_rate >= min_threshold → auto-generate tension map? (configurable)

Step 4: TENSION MAP GENERATION
  Facilitator → POST /meetings/{id}/survey/tension-map
  System → validates response_rate >= 0.30
  System → calls TensionAnalystAgent
  System → stores tension_map + facilitator_brief in meeting
  System → updates meeting.status = "survey_closed"
  System → sends "brief ready" email to facilitator
  System → creates InApp notification for facilitator
  Response → full meeting object with tension_map populated

Step 5: PRE-MEETING INTELLIGENCE (New V2 Feature)
  Facilitator → GET /intelligence/meetings/{id}/alerts
  System → checks GroupIntelligenceProfile patterns
  System → returns pattern warnings relevant to this meeting type
  UI → displays amber warning cards BEFORE facilitator starts live session

Step 6: LIVE SESSION START
  Facilitator → POST /meetings/{id}/session/start
  System → creates LiveMeetingSession
  System → updates meeting.status = "live"
  System → returns {session_id, websocket_url}
  [In Phase 2A: bot joins Zoom/Teams/Meet via platform SDK]
  [In MVP: facilitator manually shares transcript or uses browser-based mic capture]

Step 7: REAL-TIME LIVE INTELLIGENCE (WebSocket)
  Facilitator connects → WS /meetings/{id}/session/stream?token={jwt}
  System → starts simulate_meeting_intelligence() in dev / real Deepgram in prod
  Every 30s → evaluate() → HiPPO check → Groupthink precheck → LLM eval
  Alerts → pushed to facilitator WebSocket only
  Transcript → pushed to facilitator WebSocket
  Speaking distribution → pushed to facilitator WebSocket every 30s

Step 8: DECISION MARKING (During Meeting)
  Facilitator → WS message: {"type": "mark_decision", "title": "...", "description": "..."}
  System → creates Decision(org_id, meeting_id, title, description)
  System → returns confirmation to WebSocket
  OR
  Facilitator → POST /meetings/{id}/decisions (REST, during or after meeting)

Step 9: SESSION END
  Facilitator → POST /meetings/{id}/session/end
  OR: meeting bot detects Zoom/Teams meeting ended → webhook fires
  System → updates LiveMeetingSession.ended_at, total_seconds
  System → updates meeting.status = "ended"
  System → broadcasts session_ended to all WebSocket clients
  System → queues post_mortem_generation Celery task
  System → redirects facilitator to /meetings/{id}/report

Step 10: POST-MORTEM GENERATION
  System (Celery task) → calls PostMortemGeneratorAgent
  System → stores post_mortem_notes on Decision records
  System → updates meeting.status = "post_mortem_pending" → "post_mortem_done"
  System → sends post-mortem ready notification to facilitator

Step 11: OUTCOME CHECK-IN SCHEDULING
  System (on Decision creation) → DB trigger sets check_in_30d/90d/180d_at
  Celery Beat (daily 09:00 UTC) → queries decisions WHERE check_in_Xd_at <= NOW AND check_in_Xd_sent = false
  System → sends outcome check-in emails
  System → marks check_in_Xd_sent = true

Step 12: OUTCOME RECORDING
  Facilitator → POST /decisions/{id}/outcomes
  System → creates DecisionOutcome
  System → DB trigger computes prediction_accuracy_score
  System → queues refresh_intelligence_profile Celery task

Step 13: PATTERN DETECTION (Weekly)
  Celery Beat (Sunday 03:00 UTC) → run_pattern_detector
  System → compute_decision_statistics() pre-computes domain accuracy, temporal patterns
  System → calls PatternDetectorAgent (LangGraph)
  System → updates GroupIntelligenceProfile
  System → next meeting creation will warn based on updated patterns
```

### V2 Feature 2: Browser Microphone Capture (Phase 2A MVP — No Bot Required)

For the MVP live meeting intelligence without requiring the Zoom SDK integration:

```typescript
// web/app/(app)/meetings/[id]/live/MicCapture.tsx
"use client";
import { useEffect, useRef, useState } from "react";

interface Props {
  meetingId: string;
  onTranscript: (text: string, speakerLabel: string) => void;
  onError: (err: string) => void;
}

export function BrowserMicCapture({ meetingId, onTranscript, onError }: Props) {
  const wsRef = useRef<WebSocket | null>(null);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);

  const startCapture = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true }
      });

      // Send to backend STT endpoint via WebSocket
      const token = localStorage.getItem("auth_token");
      const ws = new WebSocket(
        `${getWebSocketBaseUrl()}/api/v1/meetings/${meetingId}/session/audio-stream?token=${token}`
      );
      wsRef.current = ws;

      ws.onopen = () => {
        const recorder = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
        mediaRef.current = recorder;

        recorder.ondataavailable = (e) => {
          if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
            ws.send(e.data);
          }
        };

        recorder.start(1000); // send chunks every 1 second
        setIsCapturing(true);
      };

      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === "transcript_chunk") {
          onTranscript(msg.data.text, msg.data.speaker_label || "You");
        }
      };

      ws.onerror = () => onError("Microphone stream disconnected");
    } catch (err) {
      onError("Microphone access denied. Please allow microphone access and try again.");
    }
  };

  const stopCapture = () => {
    mediaRef.current?.stop();
    wsRef.current?.close();
    setIsCapturing(false);
  };

  return (
    <div className="flex items-center gap-3 p-3 glass-card border border-primary/20">
      <div className={`w-3 h-3 rounded-full ${isCapturing ? "bg-danger animate-pulse" : "bg-white/20"}`} />
      <span className="text-xs text-on-surface-variant">
        {isCapturing ? "Capturing microphone..." : "Browser mic capture (no bot required)"}
      </span>
      {!isCapturing ? (
        <button onClick={startCapture} className="btn-primary text-xs py-1.5 px-3 ml-auto">
          Start Capture
        </button>
      ) : (
        <button onClick={stopCapture} className="btn-ghost text-xs py-1.5 px-3 ml-auto">
          Stop
        </button>
      )}
    </div>
  );
}
```

Backend audio stream endpoint:
```python
# app/api/routers/sessions.py — ADD NEW ENDPOINT

@router.websocket("/audio-stream")
async def audio_stream(websocket: WebSocket, meeting_id: str):
    """
    Receives raw audio bytes from browser, sends to Deepgram, 
    returns transcript chunks. Requires JWT token query param.
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return

    # auth same as /stream endpoint
    async with async_session_factory() as auth_db:
        try:
            current_user = await get_current_user_from_token(token, auth_db)
        except Exception:
            await websocket.close(code=4401)
            return

    await websocket.accept()

    if not settings.DEEPGRAM_API_KEY:
        # DEV MODE: echo back a mock transcript
        await _mock_audio_transcript_loop(websocket, meeting_id)
        return

    # PROD: forward to Deepgram
    from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents
    dg = DeepgramClient(settings.DEEPGRAM_API_KEY)
    dg_conn = dg.listen.live.v("1")
    options = LiveOptions(model="nova-2", punctuate=True, diarize=True,
                          encoding="linear16", sample_rate=16000)

    async def on_message(result, **kwargs):
        transcript = result.channel.alternatives[0].transcript
        if not transcript:
            return
        speaker_idx = 0
        if result.channel.alternatives[0].words:
            speaker_idx = result.channel.alternatives[0].words[0].speaker or 0
        speaker_hash = anonymize_speaker(f"browser_speaker_{speaker_idx}", meeting_id)
        await websocket.send_json({
            "type": "transcript_chunk",
            "data": {"speaker_hash": speaker_hash, "speaker_label": f"Speaker {chr(65 + speaker_idx)}",
                     "text": transcript, "start_seconds": int(result.start)}
        })

    dg_conn.on(LiveTranscriptionEvents.Transcript, on_message)
    await dg_conn.start(options)

    try:
        while True:
            audio_data = await websocket.receive_bytes()
            await dg_conn.send(audio_data)
    except Exception:
        pass
    finally:
        await dg_conn.finish()

async def _mock_audio_transcript_loop(websocket: WebSocket, meeting_id: str):
    """Development mode: returns scripted transcript chunks."""
    import asyncio, random
    mock_lines = [
        ("Speaker A", "I think we should prioritize the API redesign in Q3."),
        ("Speaker B", "I'm a bit worried about the timeline, honestly."),
        ("Speaker A", "Makes sense. Let's go with the original plan then."),
        ("Speaker C", "I agree, sounds good to me."),
        ("Speaker B", "Same page. Let's move forward."),
    ]
    for label, text in mock_lines:
        await asyncio.sleep(random.uniform(3, 6))
        try:
            await websocket.send_json({
                "type": "transcript_chunk",
                "data": {"speaker_label": label,
                         "speaker_hash": anonymize_speaker(label.lower().replace(" ", "_"), meeting_id),
                         "text": text, "start_seconds": 0}
            })
        except Exception:
            break
```

### V2 Feature 3: Meeting Intelligence Dashboard (Real-Time During Meeting)

```typescript
// web/app/(app)/meetings/[id]/live/IntelligenceDashboard.tsx
// Real-time panel showing: speaking balance gauge, active tensions, alert history

interface IntelligenceDashboardProps {
  tensionMap: TensionMap | null;
  speakers: LiveSpeaker[];
  alerts: IntelligenceAlert[];
  elapsedSeconds: number;
  scheduledMinutes: number;
}

export function IntelligenceDashboard({ tensionMap, speakers, alerts, elapsedSeconds, scheduledMinutes }: IntelligenceDashboardProps) {
  const tensionsAddressed = tensionMap?.tension_areas?.filter(t =>
    alerts.some(a => a.type === "missing_perspective" && a.message.includes(t.topic))
  ).length ?? 0;

  const totalTensions = tensionMap?.tension_areas?.length ?? 0;
  const timeProgress = Math.min((elapsedSeconds / (scheduledMinutes * 60)) * 100, 100);
  const dominantSpeaker = speakers.reduce((max, s) => s.pct > (max?.pct ?? 0) ? s : max, speakers[0]);

  return (
    <div className="space-y-4">
      {/* Meeting Progress */}
      <div className="glass-card p-4">
        <div className="flex justify-between text-xs text-on-surface-muted mb-2">
          <span>Meeting Progress</span>
          <span>{Math.floor(elapsedSeconds / 60)}m / {scheduledMinutes}m</span>
        </div>
        <div className="w-full h-2 bg-white/[0.06] rounded-full overflow-hidden">
          <div className="h-full bg-gradient-to-r from-primary to-secondary rounded-full transition-all duration-1000"
               style={{ width: `${timeProgress}%` }} />
        </div>
        {timeProgress > 55 && tensionsAddressed < totalTensions && (
          <p className="text-[10px] text-accent mt-1.5">
            ⚠ {totalTensions - tensionsAddressed} tension area(s) not yet discussed
          </p>
        )}
      </div>

      {/* Tension Coverage */}
      {tensionMap?.tension_areas && tensionMap.tension_areas.length > 0 && (
        <div className="glass-card p-4">
          <h4 className="text-xs font-bold text-on-surface-muted uppercase tracking-widest mb-3">
            Tension Coverage
          </h4>
          {tensionMap.tension_areas.map((tension, i) => {
            const addressed = alerts.some(a => a.message.toLowerCase().includes(tension.topic.toLowerCase()));
            return (
              <div key={i} className="flex items-center gap-2 mb-2">
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${addressed ? "bg-success" : "bg-white/20"}`} />
                <span className={`text-xs ${addressed ? "text-success line-through opacity-60" : "text-on-surface-variant"}`}>
                  {tension.topic}
                </span>
                <span className="ml-auto text-[10px] text-on-surface-muted">
                  {Math.round(tension.tension_score * 100)}% tension
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Dominant Speaker Warning */}
      {dominantSpeaker && dominantSpeaker.pct > 0.38 && (
        <div className="glass-card p-4 border border-accent/30 bg-accent/5">
          <p className="text-xs text-accent font-semibold mb-1">Speaking Imbalance</p>
          <p className="text-[11px] text-on-surface-variant">
            {dominantSpeaker.label} has taken {Math.round(dominantSpeaker.pct * 100)}% of speaking time.
          </p>
        </div>
      )}
    </div>
  );
}
```

### V2 Feature 4: Outcome Check-In Email & Form (Complete Flow)

```python
# app/workers/tasks/schedule_outcome_checkins.py — COMPLETE IMPLEMENTATION

from celery import shared_task
from datetime import datetime, UTC
from sqlalchemy import select, and_
from app.core.database import async_session_factory
from app.models.models import Decision, Organization, User
from app.services.email_service import email_service

@shared_task(name="tasks.send_outcome_checkins")
def send_outcome_checkins():
    """
    Daily task: finds decisions with overdue check-ins and sends emails.
    Runs at 09:00 UTC. Per-org timezone offset applied via org.settings.outcome_check_in_hour.
    """
    import asyncio
    asyncio.run(_send_outcome_checkins_async())

async def _send_outcome_checkins_async():
    now = datetime.now(UTC).replace(tzinfo=None)
    async with async_session_factory() as db:
        # Find 30-day check-ins due
        result_30 = await db.execute(
            select(Decision)
            .where(and_(
                Decision.check_in_30d_at <= now,
                Decision.check_in_30d_sent == False,
                Decision.post_mortem_status == "completed"
            ))
            .limit(500)
        )
        decisions_30 = result_30.scalars().all()

        for d in decisions_30:
            await _send_checkin_for_decision(db, d, "30d")
            d.check_in_30d_sent = True

        # Find 90-day check-ins due
        result_90 = await db.execute(
            select(Decision)
            .where(and_(
                Decision.check_in_90d_at <= now,
                Decision.check_in_90d_sent == False,
                Decision.post_mortem_status == "completed"
            ))
            .limit(500)
        )
        decisions_90 = result_90.scalars().all()

        for d in decisions_90:
            await _send_checkin_for_decision(db, d, "90d")
            d.check_in_90d_sent = True

        # 180-day
        result_180 = await db.execute(
            select(Decision)
            .where(and_(
                Decision.check_in_180d_at <= now,
                Decision.check_in_180d_sent == False,
                Decision.post_mortem_status == "completed"
            ))
            .limit(500)
        )
        for d in result_180.scalars().all():
            await _send_checkin_for_decision(db, d, "180d")
            d.check_in_180d_sent = True

        await db.commit()

async def _send_checkin_for_decision(db, decision: Decision, period: str):
    # Get the facilitator
    creator_q = await db.execute(select(User).where(User.id == decision.created_by))
    creator = creator_q.scalar_one_or_none()
    if not creator:
        return

    assumptions = [a.get("assumption", "") for a in (decision.key_assumptions or [])]
    checkin_url = f"{settings.APP_URL}/decisions/{decision.id}?checkin={period}"

    await email_service.send_outcome_checkin(
        to_email=creator.email,
        decision_title=decision.title,
        check_in_period=period,
        checkin_url=checkin_url,
        key_assumptions=assumptions[:5]  # max 5 in email
    )
```

### V2 Feature 5: Anonymous Survey Token Expiry & Validation

```python
# app/api/routers/surveys.py — ADD TOKEN EXPIRY ENFORCEMENT

@router.get("")
async def get_survey(meeting_id: UUID, token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MeetingParticipant).where(MeetingParticipant.survey_token == token)
    )
    participant = result.scalar_one_or_none()
    if not participant or str(participant.meeting_id) != str(meeting_id):
        raise NotFoundError("survey", token)

    meeting_q = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = meeting_q.scalar_one_or_none()
    if not meeting:
        raise NotFoundError("meeting", str(meeting_id))

    # V2: Check token expiry
    now = utc_now()
    if meeting.survey_deadline and now > meeting.survey_deadline:
        return {
            "meeting_title": meeting.title,
            "meeting_description": meeting.description or "",
            "deadline": meeting.survey_deadline,
            "questions": [],
            "already_submitted": participant.survey_completed_at is not None,
            "expired": True,
            "error": "This survey has closed. The deadline has passed."
        }

    return {
        "meeting_title": meeting.title,
        "meeting_description": meeting.description or "",
        "deadline": meeting.survey_deadline,
        "questions": meeting.generated_questions or [],
        "already_submitted": participant.survey_completed_at is not None,
        "expired": False
    }
```

### V2 Feature 6: Group Intelligence Profile — Auto-Refresh After Each Outcome

```python
# app/workers/tasks/refresh_intelligence.py — NEW FILE

from celery import shared_task
from uuid import UUID

@shared_task(name="tasks.refresh_intelligence_profile", bind=True, max_retries=3)
def refresh_intelligence_profile(self, org_id: str):
    """
    Triggered after each outcome is recorded.
    Recomputes GIP stats + runs pattern detector if enough decisions exist.
    Retries up to 3 times on failure.
    """
    import asyncio
    try:
        asyncio.run(_refresh_async(UUID(org_id)))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

async def _refresh_async(org_id: UUID):
    from app.core.database import async_session_factory
    from app.services.intelligence_service import intelligence_service
    async with async_session_factory() as db:
        await intelligence_service.refresh_profile(org_id, db)
```

```python
# Add to app/api/routers/outcomes.py — trigger after recording outcome
@router.post("", status_code=201)
async def record_outcome(...):
    ...
    await db.commit()

    # V2: Auto-refresh intelligence profile in background
    from app.workers.tasks.refresh_intelligence import refresh_intelligence_profile
    refresh_intelligence_profile.delay(str(current_user.org_id))

    return {"id": str(outcome.id), "recorded_at": outcome.recorded_at, "verdict": outcome.outcome_verdict}
```

### V2 Feature 7: Meeting Survey Reminder System (Automated)

```python
# app/workers/tasks/send_survey_reminders.py — NEW FILE

from celery import shared_task

@shared_task(name="tasks.send_survey_reminders")
def send_survey_reminders():
    """
    Checks meetings with open surveys approaching deadline.
    Sends reminders at 50% of time elapsed and 90% of time elapsed.
    Runs every 30 minutes via Celery Beat.
    """
    import asyncio
    asyncio.run(_send_reminders_async())

async def _send_reminders_async():
    from datetime import datetime, UTC, timedelta
    from app.core.database import async_session_factory
    from app.models.models import Meeting, MeetingParticipant, MeetingStatus, User
    from sqlalchemy import select, and_
    from app.services.email_service import email_service

    now = datetime.now(UTC).replace(tzinfo=None)

    async with async_session_factory() as db:
        # Find open surveys with active deadlines
        result = await db.execute(
            select(Meeting).where(and_(
                Meeting.status == MeetingStatus.SURVEY_OPEN,
                Meeting.survey_deadline > now,
                Meeting.survey_sent_at.isnot(None)
            ))
        )
        meetings = result.scalars().all()

        for meeting in meetings:
            total_window = (meeting.survey_deadline - meeting.survey_sent_at).total_seconds()
            elapsed = (now - meeting.survey_sent_at).total_seconds()
            pct_elapsed = elapsed / total_window if total_window > 0 else 0

            # 50% threshold: send first reminder (check hasn't been sent)
            # 90% threshold: send urgent reminder
            # Use a Redis key to prevent duplicate sends
            reminder_type = None
            if 0.45 <= pct_elapsed < 0.55:
                reminder_type = "50_pct"
            elif 0.85 <= pct_elapsed < 0.95:
                reminder_type = "90_pct"

            if not reminder_type:
                continue

            # Get non-responded participants
            part_q = await db.execute(
                select(MeetingParticipant).where(and_(
                    MeetingParticipant.meeting_id == meeting.id,
                    MeetingParticipant.survey_completed_at.is_(None)
                ))
            )
            pending_participants = part_q.scalars().all()

            for p in pending_participants:
                user_q = await db.execute(select(User).where(User.id == p.user_id))
                user = user_q.scalar_one_or_none()
                if user and p.survey_token:
                    survey_url = f"{settings.APP_URL}/survey/{meeting.id}?token={p.survey_token}"
                    await email_service.send_survey_reminder(
                        to_email=user.email,
                        meeting_title=meeting.title,
                        survey_url=survey_url,
                        deadline=meeting.survey_deadline,
                        reminder_type=reminder_type
                    )
```

```python
# Add to CELERYBEAT_SCHEDULE in app/workers/celery_app.py:
"send_survey_reminders": {
    "task": "tasks.send_survey_reminders",
    "schedule": 1800.0,  # every 30 minutes
},
```

### V2 Feature 8: Decision Confidence Calibration Widget (Frontend)

```typescript
// web/app/(app)/intelligence/CalibrationChart.tsx
"use client";
import { useQuery } from "@tanstack/react-query";
import { queries } from "@/lib/api";
import { TrendingDown, TrendingUp, Minus } from "lucide-react";

export function CalibrationChart() {
  const { data: calibration } = useQuery({
    queryKey: ["calibration"],
    queryFn: () => fetch("/api/v1/intelligence/calibration",
      { headers: { Authorization: `Bearer ${localStorage.getItem("auth_token")}` } }
    ).then(r => r.json()),
  });

  if (!calibration || !calibration.calibration_curve?.length) {
    return (
      <div className="glass-card p-6 text-center text-sm text-on-surface-muted">
        Record at least 3 outcomes to see confidence calibration data.
      </div>
    );
  }

  const overconfidence = calibration.overconfidence_index;
  const Icon = overconfidence > 0.1 ? TrendingDown : overconfidence < -0.1 ? TrendingUp : Minus;
  const color = overconfidence > 0.1 ? "text-danger" : overconfidence < -0.1 ? "text-success" : "text-secondary";

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-sm font-semibold text-white">Confidence Calibration</h3>
        <div className={`flex items-center gap-1.5 ${color}`}>
          <Icon className="w-4 h-4" />
          <span className="text-xs font-bold">
            {overconfidence > 0.1 ? "Overconfident" : overconfidence < -0.1 ? "Underconfident" : "Well Calibrated"}
          </span>
        </div>
      </div>

      <div className="space-y-3">
        {calibration.calibration_curve.map((bucket: any, i: number) => (
          <div key={i} className="flex items-center gap-3">
            <span className="text-xs text-on-surface-muted w-20 shrink-0">
              {bucket.stated_confidence_bucket}
            </span>
            <div className="flex-1 h-6 bg-white/[0.04] rounded relative overflow-hidden">
              {/* Stated confidence bar */}
              <div className="absolute inset-y-0 left-0 bg-primary/30 rounded"
                   style={{ width: `${parseInt(bucket.stated_confidence_bucket) || 80}%` }} />
              {/* Actual accuracy bar */}
              <div className="absolute inset-y-0 left-0 bg-primary rounded"
                   style={{ width: `${bucket.actual_accuracy * 100}%` }} />
            </div>
            <span className="text-xs font-mono text-white w-10 text-right">
              {Math.round(bucket.actual_accuracy * 100)}%
            </span>
            <span className="text-[10px] text-on-surface-muted w-8">
              n={bucket.decisions}
            </span>
          </div>
        ))}
      </div>

      <p className="text-xs text-on-surface-muted mt-4 italic">
        {calibration.interpretation}
      </p>
    </div>
  );
}
```

### V2 Feature 9: Notification System (Complete Implementation)

```python
# app/models/models.py — ADD Notification model if not exists

class Notification(Base):
    __tablename__ = "notifications"
    id: UUID (PK, gen_random_uuid())
    org_id: UUID (FK → organizations, CASCADE DELETE)
    user_id: UUID (FK → users, CASCADE DELETE)
    title: str (NOT NULL)
    message: str (NOT NULL)
    type: str (NOT NULL)  # "meeting_invite"|"brief_ready"|"outcome_due"|"pattern_alert"|"survey_reminder"
    resource_id: str (nullable)  # meeting_id or decision_id
    is_read: bool (DEFAULT false)
    created_at: TIMESTAMPTZ (DEFAULT NOW())

# INDEX: idx_notifications_user ON notifications(user_id, is_read, created_at DESC)
```

```python
# app/services/notification_service.py — ENHANCED VERSION

class NotificationService:
    async def notify(self, db, org_id, user_id, title, message, type, resource_id=None):
        notification = Notification(
            org_id=org_id, user_id=user_id,
            title=title, message=message, type=type, resource_id=resource_id
        )
        db.add(notification)
        # Don't commit — caller decides transaction boundary
        return notification

    async def notify_facilitator_brief_ready(self, db, meeting, facilitator_user_id):
        await self.notify(
            db=db, org_id=meeting.org_id, user_id=facilitator_user_id,
            title="Facilitator Brief Ready",
            message=f"Your tension map for '{meeting.title}' is ready. Review before the meeting.",
            type="brief_ready", resource_id=str(meeting.id)
        )

    async def notify_outcome_due(self, db, decision, user_id, period):
        await self.notify(
            db=db, org_id=decision.org_id, user_id=user_id,
            title=f"{period} Outcome Check-in Due",
            message=f"Record what happened with '{decision.title}'",
            type="outcome_due", resource_id=str(decision.id)
        )

    async def notify_pattern_detected(self, db, org_id, pattern_name, user_ids):
        for uid in user_ids:
            await self.notify(
                db=db, org_id=org_id, user_id=uid,
                title="New Pattern Detected",
                message=f"Quorum identified: {pattern_name}. View your Intelligence Profile.",
                type="pattern_alert"
            )
```

### V2 Feature 10: App Settings — `APP_URL` and Additional Config

```python
# app/core/config.py — ADD MISSING SETTINGS

class Settings(BaseSettings):
    # ... existing fields ...

    # V2 ADDITIONS:
    APP_URL: str = "http://localhost:3000"          # frontend URL, used in emails/links
    API_BASE_URL: str = "http://localhost:8000"     # backend URL, for internal links

    # Survey settings
    SURVEY_DEFAULT_DEADLINE_HOURS: int = 48         # hours before meeting to close survey
    SURVEY_MIN_RESPONSE_RATE: float = 0.30          # global fallback if org setting not set

    # Rate limits per endpoint (req/min)
    RATE_LIMIT_SURVEY_SUBMIT: int = 10              # per IP, unauthenticated
    RATE_LIMIT_AI_GENERATION: int = 10              # per org
    RATE_LIMIT_WEBSOCKET_CONN: int = 5              # concurrent WS per user

    # Worker settings
    INTELLIGENCE_EVAL_INTERVAL_SECONDS: int = 30   # how often live eval runs
    PATTERN_DETECTOR_MIN_DECISIONS: int = 5        # minimum before patterns run

    # Email settings
    EMAIL_FROM_NAME: str = "Quorum"                 # used in email "From" field
    UNSUBSCRIBE_BASE_URL: str = ""                  # for CAN-SPAM compliance

    @property
    def APP_NAME(self) -> str:
        return "Quorum"
```

---

## SECTION 3: SYSTEM ARCHITECTURE

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│  Next.js 14 Web App  │  Zoom Sidebar  │  Teams Bot  │  Meet Ext │
└──────────────────────────────┬───────────────────────────────────┘
                               │ HTTPS / WSS
┌──────────────────────────────▼───────────────────────────────────┐
│          API GATEWAY (FastAPI 0.111.0 + Nginx)                   │
│    Auth0 JWT · RLS inject · Rate limit · CORS · Webhook verify   │
└──┬────────┬────────┬────────┬────────┬────────┬──────────────────┘
   │        │        │        │        │        │
Survey  Meeting  AI Eng  Decision  Intel  GDPR+
Engine  Stream   (5 ag)  Library  Profile Billing
   │        │        │        │        │        │
┌──▼────────▼────────▼────────▼────────▼────────▼──────────────────┐
│                        DATA LAYER                                 │
│  PostgreSQL 16 (RLS+Audit)  ·  Redis 7  ·  Pinecone             │
│  InfluxDB 2.7  ·  S3 (recordings)  ·  AWS Secrets Manager       │
└──────────────────────────────┬───────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────┐
│                       WORKER LAYER                               │
│  Celery 5 + Redis broker  ·  Celery Beat (6 scheduled tasks)    │
│  survey-worker(×2) · intelligence-worker(×4) · outcome-worker   │
└──────────────────────────────────────────────────────────────────┘
```

### Architecture Principles (Non-Negotiable)
1. Privacy by default — anonymization at collection point, not configurable off
2. Fail silent in live meetings — circuit breakers protect meeting flow from API outages
3. Phase 1 (surveys) has no Phase 2 (live AI) runtime dependency
4. RLS enabled before any production data enters the DB
5. All LLM calls through Instructor — never raw JSON parsing
6. No individual performance data ever stored

---

## SECTION 4: COMPLETE TECH STACK (ALL VERSIONS PINNED)

### Backend (Python 3.12)
```toml
[tool.poetry.dependencies]
python = "^3.12"
fastapi = "0.111.0"
uvicorn = { extras = ["standard"], version = "0.30.1" }
pydantic = { extras = ["email"], version = "2.7.4" }
pydantic-settings = "2.3.4"
python-multipart = "0.0.9"
sqlalchemy = { extras = ["asyncio"], version = "2.0.30" }
asyncpg = "0.29.0"
aiosqlite = "0.20.0"       # dev/test SQLite support
alembic = "1.13.1"
redis = { extras = ["hiredis"], version = "5.0.7" }
celery = { extras = ["redis"], version = "5.4.0" }
apscheduler = "4.0.0a4"
flower = "2.0.1"
httpx = "0.27.0"
anthropic = "0.28.0"
openai = "1.35.0"
instructor = "1.4.3"
langgraph = "0.2.0"
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
python-dotenv = "1.0.1"
orjson = "3.10.6"
structlog = "24.4.0"
tenacity = "8.5.0"
sentry-sdk = { extras = ["fastapi"], version = "2.10.0" }
numpy = "1.26.4"           # for Gini coefficient calculation
```

### AI Models
- **Primary reasoning**: `claude-sonnet-4-20250514` — all 5 AI agents
- **Fallback**: `claude-haiku-4-5-20251001` — validation and light tasks
- **Embeddings**: `text-embedding-3-large` (OpenAI, 1536-dim)
- **Speech-to-text**: Deepgram Nova-2 (300-400ms latency)

### Frontend (Next.js 14 App Router)
```json
{
  "next": "14.2.4",
  "react": "18.3.1",
  "typescript": "5.5.3",
  "@tanstack/react-query": "5.50.0",
  "@tanstack/react-query-devtools": "5.50.0",
  "zustand": "4.5.2",
  "tailwindcss": "3.4.4",
  "recharts": "2.12.7",
  "react-hook-form": "7.52.1",
  "zod": "3.23.8",
  "@auth0/nextjs-auth0": "3.5.0",
  "framer-motion": "11.0.0",
  "sonner": "1.5.0",
  "lucide-react": "0.408.0",
  "date-fns": "3.6.0"
}
```

---

## SECTION 5: DATA MODELS (COMPLETE — WITH V2 ADDITIONS)

### All existing models from V1 remain. Add these V2 additions:

```sql
-- V2 ADDITION: Notifications table
CREATE TABLE notifications (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    message     TEXT NOT NULL,
    type        TEXT NOT NULL,  -- meeting_invite|brief_ready|outcome_due|pattern_alert|survey_reminder
    resource_id TEXT,           -- meeting_id or decision_id (string for flexibility)
    is_read     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_unread
    ON notifications(user_id, is_read, created_at DESC);

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
CREATE POLICY notifications_org_isolation ON notifications
    USING (org_id = current_setting('app.current_org_id', TRUE)::UUID);

-- V2 ADDITION: Survey deadline default trigger
CREATE OR REPLACE FUNCTION set_survey_deadline()
RETURNS TRIGGER AS $$
BEGIN
    -- Auto-set deadline to 6 hours before meeting if not specified
    IF NEW.survey_deadline IS NULL AND NEW.survey_sent_at IS NOT NULL THEN
        NEW.survey_deadline = NEW.scheduled_at - INTERVAL '6 hours';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_survey_deadline
    BEFORE UPDATE ON meetings
    FOR EACH ROW
    WHEN (OLD.survey_sent_at IS NULL AND NEW.survey_sent_at IS NOT NULL)
    EXECUTE FUNCTION set_survey_deadline();

-- V2 ADDITION: Add survey_reminder_50_sent, survey_reminder_90_sent columns
ALTER TABLE meetings
    ADD COLUMN IF NOT EXISTS survey_reminder_50_sent BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS survey_reminder_90_sent BOOLEAN NOT NULL DEFAULT FALSE;
```

---

## SECTION 6: ANONYMIZATION SYSTEM

```python
# app/core/security.py — COMPLETE CORRECT IMPLEMENTATION

import hashlib
import hmac
import secrets
from datetime import UTC, datetime
from app.core.config import get_settings

settings = get_settings()

def anonymize_respondent(user_id: str, meeting_id: str) -> str:
    """
    One-way HMAC-SHA256 for survey respondents.
    - Deterministic per user+meeting (needed for duplicate-check)
    - Irreversible without RESPONDENT_HASH_SECRET
    - Meeting-scoped (different hash per meeting)
    """
    secret = settings.RESPONDENT_HASH_SECRET.encode()
    message = f"{user_id}:{meeting_id}".encode()
    return hmac.new(secret, message, digestmod=hashlib.sha256).hexdigest()[:20]

def anonymize_speaker(speaker_platform_id: str, meeting_id: str) -> str:
    """Meeting-scoped speaker anonymization. Resets per meeting."""
    secret = settings.SPEAKER_HASH_SECRET.encode()
    message = f"{speaker_platform_id}:{meeting_id}".encode()
    return hmac.new(secret, message, digestmod=hashlib.sha256).hexdigest()[:16]

def generate_survey_token() -> str:
    """Cryptographically secure 43-char URL-safe token."""
    return secrets.token_urlsafe(32)

def verify_survey_token(token: str, db_token: str | None) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    if not db_token:
        return False
    return hmac.compare_digest(token.encode(), db_token.encode())

def generate_api_key() -> tuple[str, str]:
    """Returns (plain_key, key_hash). Store hash only."""
    plain_key = f"qm_live_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
    return plain_key, key_hash

def utc_now() -> datetime:
    """Timezone-naive UTC datetime (matches PostgreSQL TIMESTAMPTZ WITHOUT timezone)."""
    return datetime.now(UTC).replace(tzinfo=None)
```

---

## SECTION 7: AI ENGINE — 5 AGENTS (COMPLETE WITH WORKING PROMPTS)

### MANDATORY: All agents use Instructor
```python
import instructor
from anthropic import AsyncAnthropic
from app.core.config import get_settings

settings = get_settings()

def get_instructor_client():
    if not settings.ANTHROPIC_API_KEY:
        return None
    raw = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return instructor.from_anthropic(raw, mode=instructor.Mode.ANTHROPIC_JSON)
```

### Agent 1: Survey Designer (PRODUCTION PROMPT)
```python
SURVEY_DESIGNER_PROMPT = """You are Quorum's Survey Designer. Your job is to generate anonymous \
pre-meeting survey questions that reveal what participants actually think before social dynamics \
suppress honest views.

RULES:
1. Never write generic questions ("What do you think about X?"). Write questions with a \
specific hypothesis ("Is X the right priority given constraint Y?").
2. Every substantive opinion question MUST have include_confidence_rating=true \
(how strongly do you hold this view, 1–10).
3. Always include exactly one "what are you worried nobody will say?" question (type=open_text).
4. Always include one "what would need to be true for you to change your mind?" question (type=open_text).
5. Frame all questions neutrally — no leading language.
6. If the org has known tension patterns (provided below), ask harder questions about those \
areas. Don't let them overclaim confidence again.

QUESTION TYPE GUIDE:
- scale_1_10: intensity of opinion or confidence (1=strongly disagree, 10=strongly agree)
- multiple_choice: discrete options, max 5 choices
- open_text: open concerns or explanations
- ranked_choice: priority ordering, max 5 items

Meeting: {meeting_title}
Description: {meeting_description}
Agenda: {agenda_items}
Team context: {org_context}
Known tension patterns from past meetings: {past_tension_patterns}

Return JSON matching this exact schema:
{{
  "questions": [
    {{
      "id": "q1",
      "text": "...",
      "type": "scale_1_10|multiple_choice|open_text|ranked_choice",
      "options": ["option1", "option2"] or null,
      "include_confidence_rating": true or false,
      "rationale": "internal reasoning — why this question",
      "tension_hypothesis": "what conflict this is designed to surface"
    }}
  ],
  "design_rationale": "why these questions together form a good survey",
  "watch_for": ["what the facilitator should watch for during the meeting"]
}}

Generate 4–6 questions. Be specific. Be insightful. Not generic."""
```

### Agent 2: Tension Analyst (PRODUCTION PROMPT)
```python
TENSION_ANALYST_PROMPT = """You are Quorum's Tension Analyst. You have anonymous survey responses \
from meeting participants. Produce a Tension Map giving the facilitator an honest picture of \
what the group really thinks.

ANONYMIZATION RULES — NON-NEGOTIABLE:
1. Never quote any response verbatim, not even partially.
2. Never say "one respondent said" or imply identifiability. Use "some participants" or \
"a perspective that emerged."
3. Groups of fewer than 5 people: aggregate more aggressively — even paraphrasing a unique \
view can de-anonymize.
4. Do NOT soften real disagreements. If views clash sharply, say so. \
Facilitators need the truth, not false harmony.

TENSION DETECTION RULES:
- Surface tension when surface answers agree but confidence scores diverge.
  Example: everyone says "yes" to proceeding but avg confidence is 4/10 — that IS a tension area.
- Consensus requires: >70% agreement AND >6/10 average confidence.
- Surface tension when "what are you worried about?" contradicts structured answers.

MISSING FROM CONVERSATION:
What question was never asked that this group needs to discuss?
What buried assumption in the agenda has nobody questioned?
This section is often the most valuable output — don't leave it empty.

Meeting context: {meeting_context}
Questions asked: {question_set}
Anonymous responses: {responses}
Response rate: {response_rate}
Recent meeting history: {past_tension_maps}

Return JSON matching this schema:
{{
  "consensus_areas": [
    {{
      "topic": "str",
      "agreement_score": 0.0,
      "summary": "str",
      "confidence_average": 0.0,
      "caveat": "str or null"
    }}
  ],
  "tension_areas": [
    {{
      "topic": "str",
      "tension_score": 0.0,
      "summary": "str",
      "perspective_a": "some participants believe...",
      "perspective_b": "others hold that...",
      "perspective_c": "str or null",
      "why_this_matters": "str",
      "recommended_question": "exact question to ask in meeting"
    }}
  ],
  "missing_from_conversation": ["str"],
  "facilitator_opening_question": "the single best question to start the meeting with",
  "watch_list": ["str"],
  "confidence": 0.0,
  "confidence_caveat": "str or null"
}}"""
```

### Agent 3: Live Intelligence (PRODUCTION PROMPT)
```python
LIVE_INTELLIGENCE_PROMPT = """You are Quorum's Live Intelligence Agent. A meeting is in progress.

Detect ONLY the following patterns:
1. GROUPTHINK — group converging on a decision but pre-survey showed significant reservations. \
Consensus forming faster than decision complexity warrants.
2. ASSUMPTION_BLINDSPOT — decision forming around an unstated assumption nobody has questioned \
(discussing HOW without questioning WHETHER).
3. MISSING_CONTEXT — key concern from tension map not raised with time running short.

STRICT RULES:
- Intervene ONLY when >80% confident. False positives destroy facilitator trust permanently.
- When in doubt: return {{"action": "monitor"}}.
- Never alert the same type within 10 minutes.
- Never reference specific individuals, ever.
- Keep suggested questions to ONE sentence — facilitators read them at a glance mid-meeting.
- Alerts already delivered this meeting: {alerts_so_far}

Pre-meeting tension map: {tension_map}
Speaking distribution: {speaking_distribution}
Time elapsed / scheduled: {time_context}
Recent transcript (last 5 min): {transcript_context}

Return ONLY valid JSON — no markdown, no preamble:
{{"action": "monitor"}}
OR:
{{
  "action": "intervene",
  "type": "groupthink|assumption_blindspot|missing_context",
  "urgency": "low|medium|high",
  "message": "Max 2 sentences for the facilitator",
  "suggested_question": "Exact question to ask — 1 sentence only",
  "reasoning": "Internal rationale — not shown to facilitator"
}}"""
```

### Agent 4: Post-Mortem Generator (PRODUCTION PROMPT)
```python
POST_MORTEM_PROMPT = """You are Quorum's Post-Decision Analyst. A meeting has ended. Generate \
a structured post-mortem the facilitator will review and share with the team.

THREE PURPOSES:
1. Capture what was decided and why (accurate record)
2. Document key assumptions explicitly (most teams never do this)
3. Set up concrete outcome measurement (what do we look at in 30/90/180 days?)

RULES:
1. Be honest about warning signs Quorum detected (groupthink, HiPPO, low participation). \
Frame these as learning, not blame.
2. Key assumptions should be the specific beliefs the team held as true.
   BAD: "We assumed the market was ready."
   GOOD: "We assumed enterprise buyers in financial services would approve new vendor \
relationships within 60 days."
3. Success criteria must be measurable. Reject vague criteria.
   BAD: "The product performs well."
   GOOD: "Activation rate exceeds 40% within 30 days of launch."
4. Dissenting views come from the anonymous pre-survey only. Never attributed to a person.
5. Direct, clear prose. No padding or filler.

Meeting: {meeting_title}
Decisions: {decisions_json}
Tension map: {tension_map}
Live session events: {live_events}
Duration: {duration_minutes} minutes | Survey response rate: {survey_response_rate}

Return JSON — no markdown wrapper:
{{
  "executive_summary": "2–3 sentence summary of what was decided and key context",
  "decisions": [
    {{
      "title": "str",
      "description": "str",
      "options_considered": ["str"],
      "rationale": "str",
      "key_assumptions": ["SPECIFIC assumption str"],
      "dissenting_views": "str or null",
      "confidence_at_decision": 0.0,
      "success_criteria": {{
        "30_days": "MEASURABLE criterion",
        "90_days": "MEASURABLE criterion",
        "180_days": "MEASURABLE criterion"
      }}
    }}
  ],
  "process_observations": {{
    "survey_participation": "str",
    "warning_signs_detected": ["str"],
    "what_went_well": "str",
    "suggested_improvement": "str"
  }},
  "open_questions": ["str"]
}}"""
```

### Agent 5: Pattern Detector (PRODUCTION PROMPT)
```python
PATTERN_DETECTOR_PROMPT = """You are Quorum's Pattern Analyst. Review this organization's decision \
history and outcome data. Surface systematic patterns — specifically where this team is miscalibrated.

RULES:
1. Only surface patterns with >= 5 supporting data points. Smaller = noise.
2. Patterns must be ACTIONABLE.
   WEAK: "Your team sometimes makes bad decisions."
   STRONG: "Hiring decisions for senior roles show 38% accuracy vs. 71% for junior roles — \
teams may be overweighting technical signals and underweighting culture fit at senior level."
3. Be honest about confidence. Small samples (5-9) need uncertainty language.
4. Never surface patterns that could identify individuals.

PATTERN TYPES TO INVESTIGATE:
- Domain accuracy gaps (where is this team weakest?)
- Temporal patterns (day of week, time pressure, meeting length)
- Overconfidence: where does stated confidence exceed actual accuracy?
- Assumption failure patterns: what types of assumptions consistently fail?
- Participation patterns: does low survey response predict worse outcomes?

Pre-computed statistics: {computed_stats}
Raw decision history: {decision_history}
Current profile: {current_profile}

Return JSON array — no markdown wrapper:
[
  {{
    "pattern_id": "unique_str",
    "name": "short pattern name",
    "description": "specific, actionable description with data",
    "evidence": "what the data shows",
    "sample_size": 0,
    "confidence": "low|medium|high",
    "actionable_intervention": "what to do differently",
    "example_decision_ids": ["str"]
  }}
]"""
```

---

## SECTION 8: COMPLETE API SPECIFICATION

### Base URLs
- Production: `https://api.quorum.ai/v1`
- Staging: `https://staging.api.quorum.ai/v1`
- Local dev: `http://localhost:8000/api/v1`

### Authentication
- Protected endpoints: `Authorization: Bearer {JWT}` (Auth0 RS256 or dev HS256)
- Survey submission: `X-Survey-Token: {token}` (no JWT required)
- WebSocket: `?token={JWT}` query parameter

### Full Endpoint List
```
# ORGANIZATION
GET    /org                                       org profile + settings
PATCH  /org                                       update settings (admin only)
GET    /org/users                                 list all users
GET    /org/intelligence-profile                  Group Intelligence Profile

# USERS
POST   /users/invite                              invite by email + role
DELETE /users/{id}                                remove from org (admin only)

# MEETINGS
POST   /meetings                                  create meeting
GET    /meetings?status=upcoming|past|all         list meetings
GET    /meetings/{id}                             full detail (tension_map only for facilitator)
PATCH  /meetings/{id}                             update (blocked after status=live)
DELETE /meetings/{id}                             cancel (blocked after survey_open)
POST   /meetings/{id}/end                         end live meeting

# SURVEY PHASE
POST   /meetings/{id}/survey/generate             AI generates questions → {status, questions}
GET    /meetings/{id}/survey?token=               get questions for participant (no auth)
POST   /meetings/{id}/survey/respond              submit/update anonymous response (X-Survey-Token)
GET    /meetings/{id}/survey/status               response rate (facilitator only)
POST   /meetings/{id}/survey/tension-map          generate tension map → meeting object
GET    /meetings/{id}/tension-map                 get tension map (facilitator only)
GET    /meetings/{id}/facilitator-brief           markdown brief (facilitator only)

# LIVE SESSION
POST   /meetings/{id}/session/start               start session → {session_id, websocket_url}
WS     /meetings/{id}/session/stream              real-time intelligence stream (JWT)
WS     /meetings/{id}/session/public-stream       read-only speaking distribution (no auth)
WS     /meetings/{id}/session/audio-stream        receive audio, return transcripts (JWT)
POST   /meetings/{id}/session/end                 end session → summary
GET    /meetings/{id}/session/summary             session report

# DECISIONS
POST   /decisions                                 create decision (standalone or from meeting)
GET    /decisions?domain=&search=&limit=          list decisions
GET    /decisions/{id}                            detail + outcomes + similar decisions
PATCH  /decisions/{id}                            update decision
POST   /decisions/{id}/post-mortem                submit post-mortem {notes, status}
GET    /decisions/{id}/audit-log                  export audit trail as JSON

# OUTCOMES
POST   /decisions/{id}/outcomes                   record check-in {period, verdict, description}
GET    /decisions/{id}/outcomes                   all outcomes for decision

# INTELLIGENCE
GET    /intelligence/profile                      Group Intelligence Profile
GET    /intelligence/patterns                     all detected patterns
GET    /intelligence/domain/{domain}              domain-specific analysis
GET    /intelligence/calibration                  confidence vs. accuracy curve
GET    /intelligence/meetings/{id}/alerts         pre-meeting pattern warnings (V2)
POST   /intelligence/refresh                      force re-run pattern detection

# NOTIFICATIONS (V2)
GET    /notifications?unread_only=false           paginated notifications for user
POST   /notifications/{id}/read                   mark as read
POST   /notifications/read-all                    mark all as read

# AUTH
POST   /auth/login                                dev-only email/password → JWT
GET    /auth/me                                   current user + org

# PROMPTS
GET    /prompts/types                             list prompt types
GET    /prompts/{type}/active                     get active prompt
POST   /prompts                                   create new version (admin)
POST   /prompts/activate                          activate version (admin)
POST   /prompts/experiment                        set A/B traffic % (admin)

# WEBHOOKS
POST   /webhooks/stripe                           billing events (Stripe-Signature verified)
POST   /webhooks/zoom                             meeting lifecycle (HMAC verified)

# GDPR
GET    /gdpr/export                               export all org data (admin)
DELETE /gdpr/erase                                delete all org data (admin, 24hr SLA)
```

### WebSocket Protocol (All Endpoints)

```javascript
// === /session/stream (facilitator, JWT required) ===

// SERVER → CLIENT (facilitator only)
{type: "transcript_chunk", data: {speaker_hash, speaker_label, text, start_seconds}}
{type: "intelligence_alert", data: {alert_id, type, urgency, message, suggested_question, timestamp_seconds}}
{type: "speaking_update", data: {distribution: [{hash, label, seconds, pct}]}}
{type: "decision_suggested", data: {title, confidence}}
{type: "session_ended", data: {total_seconds, duration_minutes, decisions_marked}}
{type: "pong", timestamp: 1234567890}

// CLIENT → SERVER (facilitator)
{type: "ping"}
{type: "acknowledge_alert", alert_id: "uuid", response: "handle_it|aware|dismissed"}
{type: "mark_decision", title: "...", description: "...", timestamp: 1234}
{type: "request_question", context: "We're discussing timeline now"}

// === /session/public-stream (participants, no auth) ===
// SERVER → CLIENT (read-only)
{type: "speaking_update", data: {distribution: [{label, pct}]}}
// NOTE: labels are anonymous ("Speaker A", "Speaker B"), not names
// NOTE: no transcript_chunk, no intelligence_alert

// === /session/audio-stream (browser mic capture, JWT required) ===
// CLIENT → SERVER: raw audio bytes (webm/opus, 1-second chunks)
// SERVER → CLIENT:
{type: "transcript_chunk", data: {speaker_hash, speaker_label, text, start_seconds}}
{type: "error", message: "..."}
```

---

## SECTION 9: COMPLETE MEETING WORKFLOW PROMPT

This section contains the exact prompts, state transitions, and code patterns needed to implement a fully working meeting workflow from creation to outcome tracking.

### 9.1 Meeting Creation → Survey Flow

```python
# STEP 1: Create meeting (POST /meetings)
# Immediately creates participants and sends invitations

@router.post("", response_model=MeetingResponse, status_code=201)
async def create_meeting(data: MeetingCreate, current_user: CurrentUser, db: AsyncSession):
    # 1. Create meeting record
    meeting = Meeting(
        org_id=current_user.org_id,
        created_by=current_user.user_id,
        title=data.title,
        description=data.description,
        scheduled_at=data.scheduled_at,
        duration_minutes=data.duration_minutes,
        platform=data.platform,
        domain=data.domain,
        tags=data.tags,
        agenda_items=[a.model_dump() for a in data.agenda_items],
        survey_participant_count=len(data.participant_emails),
        status=MeetingStatus.DRAFT
    )
    db.add(meeting)
    await db.flush()  # get meeting.id before creating participants

    # 2. Create participant records with survey tokens
    for email in data.participant_emails:
        user = await get_user_by_email_or_none(db, email, current_user.org_id)
        token = generate_survey_token()
        participant = MeetingParticipant(
            meeting_id=meeting.id,
            user_id=user.id if user else current_user.user_id,  # fallback for external
            role=ParticipantRole.FACILITATOR if (user and user.id == current_user.user_id)
                 else ParticipantRole.PARTICIPANT,
            survey_token=token,
        )
        db.add(participant)

        # 3. In-app notification
        if user:
            await notification_service.notify(
                db=db, org_id=current_user.org_id, user_id=user.id,
                title="Meeting Invitation",
                message=f"You've been invited to '{meeting.title}'",
                type="meeting_invite", resource_id=str(meeting.id)
            )

    await db.commit()
    await db.refresh(meeting)
    return _meeting_to_response(meeting)

# STEP 2: Generate AI Survey (POST /meetings/{id}/survey/generate)
@router.post("/generate", response_model=SurveyGenerateResponse, status_code=202)
async def generate_survey(meeting_id: UUID, current_user: CurrentUser, db: AsyncSession):
    meeting = await get_meeting_or_404(db, meeting_id, current_user.org_id)

    # 1. Get org context for better questions
    org = await get_org(db, current_user.org_id)
    org_context = (org.settings or {}).get("ai_context", "")

    # 2. Get past tension patterns for this org
    profile = await get_intelligence_profile(db, current_user.org_id)
    past_patterns = profile.identified_patterns[:3] if profile else []

    # 3. Generate questions
    designer = AgentFactory.get_survey_designer()
    output = await designer.generate(
        meeting_title=meeting.title,
        meeting_description=meeting.description or "",
        agenda_items=meeting.agenda_items,
        org_context=org_context,
        past_tension_patterns=past_patterns,
    )

    # 4. Calculate survey deadline (6 hours before meeting, or 48hr from now, whichever is sooner)
    from datetime import datetime, timedelta, UTC
    now = utc_now()
    deadline_from_meeting = meeting.scheduled_at - timedelta(hours=6)
    deadline_from_now = now + timedelta(hours=48)
    survey_deadline = min(deadline_from_meeting, deadline_from_now)
    if survey_deadline < now:
        survey_deadline = now + timedelta(hours=2)  # last resort: 2hr window

    # 5. Store and send
    meeting.generated_questions = [q.model_dump() for q in output.questions]
    meeting.status = MeetingStatus.SURVEY_OPEN
    meeting.survey_sent_at = now
    meeting.survey_deadline = survey_deadline

    # 6. Send survey emails to all participants
    participants = await get_meeting_participants(db, meeting_id)
    for p in participants:
        user = await get_user(db, p.user_id)
        if user and p.survey_token:
            survey_url = f"{settings.APP_URL}/survey/{meeting.id}?token={p.survey_token}"
            await email_service.send_survey_invitation(
                to_email=user.email,
                meeting_title=meeting.title,
                facilitator_name=current_user.display_name or "your facilitator",
                survey_url=survey_url,
                deadline=meeting.survey_deadline
            )

    await db.commit()
    return SurveyGenerateResponse(
        job_id=uuid4(), status="completed", estimated_seconds=0
    )

# STEP 3: Participant Survey (GET /meetings/{id}/survey?token=)
# No authentication required — anyone with the token can access
@router.get("")
async def get_survey(meeting_id: UUID, token: str, db: AsyncSession = Depends(get_db)):
    participant = await get_participant_by_token_or_404(db, token, meeting_id)
    meeting = await get_meeting_or_404_no_auth(db, meeting_id)

    now = utc_now()
    expired = meeting.survey_deadline and now > meeting.survey_deadline

    return {
        "meeting_title": meeting.title,
        "meeting_description": meeting.description or "",
        "deadline": meeting.survey_deadline,
        "questions": meeting.generated_questions or [],
        "already_submitted": participant.survey_completed_at is not None,
        "expired": expired,
    }

# STEP 4: Submit Survey (POST /meetings/{id}/survey/respond)
@router.post("/respond", response_model=SurveySubmitResponse, status_code=201)
async def submit_response(meeting_id: UUID, data: SurveySubmit, db: AsyncSession = Depends(get_db)):
    participant = await get_participant_by_token_or_404(db, data.token, meeting_id)
    meeting = await get_meeting_or_404_no_auth(db, meeting_id)

    if meeting.survey_deadline and utc_now() > meeting.survey_deadline:
        raise ValidationError("Survey deadline has passed. This response cannot be accepted.")

    respondent_hash = anonymize_respondent(str(participant.user_id), str(meeting_id))

    # Upsert — allow updating responses until deadline
    existing = await get_survey_response(db, meeting_id, respondent_hash)
    if existing:
        existing.responses = [r.model_dump() for r in data.responses]
        existing.updated_at = utc_now()
    else:
        db.add(SurveyResponse(
            meeting_id=meeting_id,
            respondent_hash=respondent_hash,
            responses=[r.model_dump() for r in data.responses],
        ))
        meeting.survey_response_count += 1  # Also incremented by DB trigger

    participant.survey_completed_at = utc_now()
    await db.commit()
    return SurveySubmitResponse(submitted=True, can_update_until=meeting.survey_deadline)

# STEP 5: Generate Tension Map (POST /meetings/{id}/survey/tension-map)
@router.post("/tension-map", response_model=MeetingResponse)
async def generate_tension_map(meeting_id: UUID, current_user: CurrentUser, db: AsyncSession):
    meeting = await get_meeting_or_404(db, meeting_id, current_user.org_id)
    responses = await get_survey_responses(db, meeting_id)

    if not responses:
        raise ValidationError("No survey responses yet. Survey responses are required.")

    response_rate = meeting.survey_response_count / max(meeting.survey_participant_count, 1)
    if response_rate < 0.30:
        raise ValidationError(
            f"Only {response_rate:.0%} of participants responded. "
            "At least 30% participation is required. "
            "Consider sending a reminder or extending the deadline."
        )

    analyst = AgentFactory.get_tension_analyst()
    output, status = await analyst.generate(
        meeting_context={
            "title": meeting.title,
            "description": meeting.description or "",
            "scheduled_at": meeting.scheduled_at.isoformat(),
            "duration_minutes": meeting.duration_minutes,
        },
        question_set=meeting.generated_questions or [],
        responses=[
            {"respondent_hash": r.respondent_hash, "responses": r.responses}
            for r in responses
        ],
        response_rate=response_rate,
    )

    if output is None:
        raise ValidationError("Insufficient data to generate tension map.")

    meeting.tension_map = output.model_dump()
    meeting.tension_map_generated_at = utc_now()
    meeting.facilitator_brief = output.facilitator_opening_question
    meeting.status = MeetingStatus.SURVEY_CLOSED

    # Send brief-ready notification
    await notification_service.notify_facilitator_brief_ready(
        db=db, meeting=meeting, facilitator_user_id=current_user.user_id
    )
    await email_service.send_facilitator_brief_ready(
        to_email=current_user.email,
        meeting_title=meeting.title,
        brief_url=f"{settings.APP_URL}/meetings/{meeting.id}/brief",
        response_rate=response_rate,
    )

    await db.commit()
    await db.refresh(meeting)
    return _meeting_to_response(meeting)
```

### 9.2 Live Session Workflow

```python
# STEP 6: Start Live Session (POST /meetings/{id}/session/start)
@router.post("/start", response_model=SessionStartResponse, status_code=201)
async def start_session(meeting_id: UUID, request: Request, current_user: CurrentUser, db: AsyncSession):
    meeting = await get_meeting_or_404(db, meeting_id, current_user.org_id)

    allowed_statuses = {MeetingStatus.DRAFT, MeetingStatus.SURVEY_OPEN, MeetingStatus.SURVEY_CLOSED}
    if meeting.status not in allowed_statuses:
        raise ValidationError(f"Cannot start session. Meeting status is '{meeting.status}'.")

    meeting.status = MeetingStatus.LIVE
    meeting.live_session_started_at = utc_now()

    # Create or reset live session record
    session_q = await db.execute(select(LiveMeetingSession).where(LiveMeetingSession.meeting_id == meeting_id))
    session = session_q.scalar_one_or_none()
    if not session:
        session = LiveMeetingSession(meeting_id=meeting_id)
        db.add(session)
    else:
        session.started_at = utc_now()
        session.ended_at = None
        session.total_seconds = 0
        session.speaking_distribution = {}
        session.hippo_events = []
        session.groupthink_events = []

    await db.commit()
    await db.refresh(session)

    ws_scheme = "wss" if request.url.scheme == "https" else "ws"
    ws_url = f"{ws_scheme}://{request.url.netloc}/api/v1/meetings/{meeting_id}/session/stream"

    return SessionStartResponse(
        session_id=session.id,
        started_at=session.started_at,
        websocket_url=ws_url
    )

# STEP 7: WebSocket Intelligence Loop
# The WebSocket handler (existing in sessions.py) runs:
# - simulate_meeting_intelligence() in dev (sends mock data every 4-7 seconds)
# - run_live_intelligence() in parallel (evaluates every 30s using LiveIntelligenceAgent)

# STEP 8: Mark Decision During Meeting (via WebSocket or REST)
# WebSocket path: {"type": "mark_decision", "title": "...", "description": "..."}
# REST path: POST /meetings/{id}/decisions (from report page after meeting)

# STEP 9: End Session (POST /meetings/{id}/session/end)
@router.post("/end", response_model=SessionSummaryResponse)
async def end_session(meeting_id: UUID, current_user: CurrentUser, db: AsyncSession):
    meeting = await get_meeting_or_404(db, meeting_id, current_user.org_id)
    meeting.status = MeetingStatus.ENDED
    meeting.live_session_ended_at = utc_now()

    session_q = await db.execute(select(LiveMeetingSession).where(LiveMeetingSession.meeting_id == meeting_id))
    session = session_q.scalar_one_or_none()
    if session and not session.ended_at:
        session.ended_at = utc_now()
        if meeting.live_session_started_at:
            delta = session.ended_at - meeting.live_session_started_at
            session.total_seconds = max(int(delta.total_seconds()), 0)

    await db.commit()

    # Broadcast session ended to all WebSocket clients
    await manager.broadcast(str(meeting_id), {
        "type": "session_ended",
        "data": {
            "total_seconds": session.total_seconds if session else 0,
            "duration_minutes": (session.total_seconds // 60) if session else 0,
        }
    })

    # Queue post-mortem generation
    # (Celery task in production; inline in dev/test)
    from app.workers.tasks.generate_tension_map import generate_post_mortem_task
    generate_post_mortem_task.delay(str(meeting_id))

    return SessionSummaryResponse(
        session_id=session.id if session else uuid4(),
        duration_minutes=(session.total_seconds // 60) if session else 0,
        speaking_distribution=[
            {"speaker": k, "pct": v}
            for k, v in (session.speaking_distribution or {}).items()
        ] if session else [],
        alerts_delivered=session.hippo_events or [] if session else [],
        decisions_marked=0,
    )
```

### 9.3 Post-Meeting → Outcome Tracking Workflow

```python
# STEP 10: Post-Mortem Generation (Celery task, triggered after session end)
@shared_task(name="tasks.generate_post_mortem")
def generate_post_mortem_task(meeting_id: str):
    import asyncio
    asyncio.run(_generate_post_mortem_async(meeting_id))

async def _generate_post_mortem_async(meeting_id: str):
    from app.core.database import async_session_factory
    from app.intelligence.agents.factory import AgentFactory
    from app.models.models import Meeting, Decision

    async with async_session_factory() as db:
        result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
        meeting = result.scalar_one_or_none()
        if not meeting:
            return

        decisions_q = await db.execute(select(Decision).where(Decision.meeting_id == meeting_id))
        decisions = decisions_q.scalars().all()

        session_q = await db.execute(select(LiveMeetingSession).where(LiveMeetingSession.meeting_id == meeting_id))
        session = session_q.scalar_one_or_none()

        agent = AgentFactory.get_post_mortem_generator()
        try:
            output = await agent.generate(
                meeting_title=meeting.title,
                decisions=[{
                    "title": d.title,
                    "description": d.description,
                    "options_considered": d.options_considered or [],
                    "key_assumptions": d.key_assumptions or [],
                    "team_confidence": d.team_confidence,
                } for d in decisions],
                tension_map=meeting.tension_map,
                live_events=session.hippo_events + session.groupthink_events if session else [],
                duration_minutes=meeting.duration_minutes,
                survey_response_rate=(
                    meeting.survey_response_count / max(meeting.survey_participant_count, 1)
                ),
            )

            # Update all decisions with AI-generated post-mortem insights
            for i, d in enumerate(decisions):
                if i < len(output.decisions):
                    ai_dec = output.decisions[i]
                    d.key_assumptions = [{"assumption": a, "confidence": 0.7, "check_in_question": ""}
                                          for a in ai_dec.key_assumptions]
                    d.post_mortem_notes = ai_dec.rationale
                    d.post_mortem_status = PostMortemStatus.COMPLETED
                    d.post_mortem_completed_at = utc_now()

            meeting.status = MeetingStatus.POST_MORTEM_DONE
        except Exception as e:
            logger.error(f"Post-mortem generation failed for meeting {meeting_id}: {e}")
            meeting.status = MeetingStatus.POST_MORTEM_PENDING  # can retry manually

        await db.commit()

# STEP 11: View Report (GET /meetings/{id}/report — frontend route)
# Frontend fetches: meeting detail, decisions for this meeting, session summary
# Shows: speaking distribution, post-mortem, AI-generated insights, decision list

# STEP 12: Record Outcome (POST /decisions/{id}/outcomes)
@router.post("", status_code=201)
async def record_outcome(decision_id: UUID, data: OutcomeCreate, current_user: CurrentUser, db: AsyncSession):
    decision = await get_decision_or_404(db, decision_id, current_user.org_id)

    outcome = DecisionOutcome(
        decision_id=decision_id,
        recorded_by=current_user.user_id,
        check_in_period=data.check_in_period,
        outcome_verdict=data.outcome_verdict,
        outcome_description=data.outcome_description,
        what_we_got_right=data.what_we_got_right,
        what_we_missed=data.what_we_missed,
        key_assumptions_that_failed=data.key_assumptions_that_failed,
        # prediction_accuracy_score is set by DB trigger
        lessons_learned=data.lessons_learned,
    )
    db.add(outcome)

    # Mark check-in sent
    if data.check_in_period == "30d": decision.check_in_30d_sent = True
    elif data.check_in_period == "90d": decision.check_in_90d_sent = True
    elif data.check_in_period == "180d": decision.check_in_180d_sent = True

    await db.commit()
    await db.refresh(outcome)

    # Auto-refresh intelligence profile in background
    from app.workers.tasks.refresh_intelligence import refresh_intelligence_profile
    refresh_intelligence_profile.delay(str(current_user.org_id))

    return {
        "id": str(outcome.id),
        "recorded_at": outcome.recorded_at.isoformat(),
        "verdict": outcome.outcome_verdict,
    }
```

---

## SECTION 10: LLM COST MODEL (VALIDATED)

| Component | Input tokens | Output tokens | Cost/call |
|---|---|---|---|
| Survey Designer | ~800 | ~600 | ~$0.004 |
| Tension Analyst | ~2,000 | ~1,000 | ~$0.009 |
| Live Agent (per 30s eval) | ~1,500 | ~200 | ~$0.005 |
| Post-Mortem Generator | ~2,500 | ~1,500 | ~$0.012 |
| Pattern Detector | ~8,000 | ~2,000 | ~$0.030 |

**Org with 5 meetings/month on $490 MRR (10 seats × $49):**
- Survey: $0.02 + Tension: $0.045 + Live: $3.00 + Post-mortem: $0.06 + Patterns: $0.12 = **$3.25/month = 0.66%**

**Circuit Breaker (mandatory):**
```python
from app.core.circuit_breaker import CircuitBreaker

llm_cb = CircuitBreaker(name="LLM", failure_threshold=3, recovery_timeout=60)

@llm_cb
async def call_claude_with_instructor(client, model, max_tokens, response_model, messages):
    return await client.messages.create(
        model=model, max_tokens=max_tokens,
        response_model=response_model, messages=messages
    )
```

---

## SECTION 11: SECURITY & ENVIRONMENT VARIABLES

### All Required Environment Variables
```bash
# Core
APP_ENV=production|staging|development
SECRET_KEY=<openssl rand -hex 32>
APP_URL=https://app.quorum.ai               # NEW in V2
API_BASE_URL=https://api.quorum.ai          # NEW in V2

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
ANTHROPIC_MODEL=claude-sonnet-4-20250514
OPENAI_API_KEY=...
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
PINECONE_API_KEY=...
PINECONE_INDEX=quorum-decisions
DEEPGRAM_API_KEY=...

# Anonymization (AWS Secrets Manager in prod — NEVER commit)
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
SENDGRID_FROM_NAME=Quorum
STRIPE_SECRET_KEY=...
STRIPE_WEBHOOK_SECRET=...

# Observability
SENTRY_DSN=...
DATADOG_API_KEY=...

# AWS
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
S3_BUCKET=quorum-recordings

# Feature Flags
FEATURE_LIVE_MEETING=true
FEATURE_RECORDING=false
FEATURE_PATTERN_DETECTOR=true
FEATURE_SLACK_INTEGRATION=true

# Worker Settings (NEW in V2)
SURVEY_DEFAULT_DEADLINE_HOURS=48
SURVEY_MIN_RESPONSE_RATE=0.30
INTELLIGENCE_EVAL_INTERVAL_SECONDS=30
PATTERN_DETECTOR_MIN_DECISIONS=5

# Runtime
CELERY_TASK_ALWAYS_EAGER=false          # set true in test only
DATABASE_ECHO=false                     # set true in dev for SQL logging
```

---

## SECTION 12: REDIS KEY SCHEMA (COMPLETE)

```
# Session state (TTL: 4 hours)
quorum:session:{id}:state             → JSON {meeting_id, status, org_id}
quorum:session:{id}:speaking          → Hash {speaker_hash → seconds_integer}
quorum:session:{id}:alerts            → List {alert JSON strings, max 20}
quorum:session:{id}:buffer            → List {last 200 transcript chunk JSONs}
quorum:session:{id}:hp_count          → Integer (HiPPO alerts delivered)
quorum:session:{id}:mp_count          → Integer (Missing perspective alerts delivered)

# WebSocket connections (TTL: 4 hours)
quorum:ws:{session_id}:connections    → Set {connection IDs}

# Rate limiting (TTL: 60s — sliding window)
quorum:ratelimit:{org_id}:ai_gen      → Counter
quorum:ratelimit:{ip}:survey_submit   → Counter
quorum:ratelimit:{user_id}:ws         → Counter (concurrent connections)

# Survey response lock (prevents race on response count)
quorum:survey:{meeting_id}:lock       → Lock (TTL: 5s)

# Survey reminder dedup (prevents sending duplicate reminders)
quorum:reminder:{meeting_id}:50pct    → Flag (TTL: meeting deadline)
quorum:reminder:{meeting_id}:90pct    → Flag (TTL: meeting deadline)

# LLM response cache (idempotency)
quorum:llm:tension:{meeting_id}       → JSON (TTL: 1 hour)
quorum:llm:postmortem:{meeting_id}    → JSON (TTL: 24 hours)

# Intelligence profile cache (avoid recomputing on every request)
quorum:gip:{org_id}                   → JSON (TTL: 6 hours, busted on outcome record)
```

---

## SECTION 13: CELERY TASK SCHEDULE (COMPLETE V2)

```python
# app/workers/celery_app.py

CELERYBEAT_SCHEDULE = {
    # Every 30 minutes — send survey reminders at 50% and 90% of deadline
    "send_survey_reminders": {
        "task": "tasks.send_survey_reminders",
        "schedule": 1800.0,
    },
    # Daily at 09:00 UTC — send outcome check-in emails
    "send_outcome_checkins": {
        "task": "tasks.send_outcome_checkins",
        "schedule": crontab(hour=9, minute=0),
    },
    # Sunday 03:00 UTC — run pattern detector
    "run_pattern_detector": {
        "task": "tasks.run_pattern_detector",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),
    },
    # Daily at 02:00 UTC — clean expired audio + old transcript chunks
    "cleanup_expired_data": {
        "task": "tasks.cleanup_expired_data",
        "schedule": crontab(hour=2, minute=0),
    },
    # Every 2 minutes — check for pending tension map jobs (catch missed)
    "process_tension_map_queue": {
        "task": "tasks.process_tension_map_queue",
        "schedule": 120.0,
    },
    # Every 5 minutes — health check all active live sessions
    "ping_active_sessions": {
        "task": "tasks.ping_active_sessions",
        "schedule": 300.0,
    },
}

# CELERY QUEUES:
# default         → general tasks
# high-priority   → tension map generation (facilitators waiting)
# scheduled       → outcome check-ins, pattern detector, reminders
# background      → intelligence refresh, post-mortem generation
```

---

## SECTION 14: FILE STRUCTURE (V2 ADDITIONS HIGHLIGHTED)

```
quorum/
├── app/
│   ├── main.py
│   ├── api/routers/
│   │   ├── auth.py surveys.py meetings.py sessions.py
│   │   ├── decisions.py outcomes.py intelligence.py
│   │   ├── notifications.py          ← V2 NEW
│   │   ├── webhooks.py gdpr.py prompts.py
│   ├── services/
│   │   ├── survey_service.py
│   │   ├── tension_map_service.py
│   │   ├── stt_service.py            ← FIXED (remove duplicate method)
│   │   ├── platform_service.py       ← V2 NEW (replaces mock URL generation)
│   │   ├── intelligence_service.py
│   │   ├── notification_service.py   ← V2 ENHANCED
│   │   ├── email_service.py
│   │   ├── decision_service.py
│   │   ├── outcome_service.py
│   │   ├── pattern_service.py
│   │   ├── billing_service.py
│   │   ├── embedding_service.py
│   │   ├── pinecone_service.py
│   │   ├── slack_service.py
│   │   ├── audit_service.py
│   │   ├── websocket_manager.py
│   │   └── user_service.py
│   ├── workers/tasks/
│   │   ├── send_survey_invitations.py
│   │   ├── send_survey_reminders.py  ← V2 NEW
│   │   ├── generate_tension_map.py
│   │   ├── generate_post_mortem.py   ← V2 NEW (extracted from session end)
│   │   ├── schedule_outcome_checkins.py ← V2 ENHANCED
│   │   ├── run_pattern_detector.py
│   │   ├── refresh_intelligence.py   ← V2 NEW
│   │   ├── ping_active_sessions.py   ← V2 NEW
│   │   └── cleanup_expired_data.py
│   ├── intelligence/agents/
│   │   ├── factory.py survey_designer.py tension_analyst.py
│   │   ├── live_agent.py post_mortem_generator.py pattern_detector.py
│   │   ├── perspective_detector.py
│   │   └── mock_ai.py
│   ├── intelligence/prompts.py       ← UPDATED with correct production prompts
│   ├── models/models.py              ← ADD Notification model
│   ├── schemas/schemas.py
│   └── core/
│       ├── config.py                 ← ADD APP_URL + V2 settings
│       ├── database.py               ← FIX set_rls_org_id type
│       ├── security.py               ← FIX digestmod=
│       ├── exceptions.py
│       ├── logging.py
│       ├── circuit_breaker.py
│       └── jwt_utils.py
├── tests/
│   ├── unit/
│   │   ├── test_anonymization.py     ← All 7 adversarial tests REQUIRED
│   │   ├── test_detection_algorithms.py
│   │   ├── test_survey_validation.py
│   │   └── test_meeting_workflow.py  ← V2 NEW: end-to-end workflow tests
│   ├── integration/
│   │   ├── test_api_surveys.py       ← Include token expiry tests
│   │   ├── test_api_meetings.py
│   │   ├── test_api_decisions.py
│   │   ├── test_api_notifications.py ← V2 NEW
│   │   └── test_websocket_session.py
│   └── ai_evals/
│       ├── eval_survey_designer.py
│       ├── eval_tension_analyst.py
│       └── eval_live_agent.py
├── web/app/
│   ├── (app)/meetings/[id]/
│   │   ├── page.tsx                  ← Enhanced with pattern alerts
│   │   ├── brief/page.tsx
│   │   ├── live/
│   │   │   ├── page.tsx              ← FIX: remove hardcoded mock speakers
│   │   │   ├── MicCapture.tsx        ← V2 NEW: browser mic capture
│   │   │   └── IntelligenceDashboard.tsx ← V2 NEW
│   │   └── report/page.tsx
│   ├── (app)/intelligence/
│   │   ├── page.tsx
│   │   └── CalibrationChart.tsx      ← V2 NEW
│   └── components/layout/
│       ├── Sidebar.tsx
│       └── TopBar.tsx                ← FIX: localStorage SSR guard
├── migrations/
│   ├── 001_initial_schema.py
│   ├── 002_add_rls_policies.py
│   ├── 003_add_audit_log.py
│   ├── 004_add_notifications.py      ← V2 NEW
│   └── 005_add_survey_reminder_flags.py ← V2 NEW
├── .github/workflows/ci.yml deploy.yml
├── Dockerfile docker-compose.yml
├── pyproject.toml alembic.ini nginx.conf Makefile
```

---

## SECTION 15: NON-NEGOTIABLE CONSTRAINTS (V1 + V2 ADDITIONS)

### From V1 (unchanged):
1. Never call Claude without Instructor
2. RLS enabled before any production data
3. Anonymization secrets in AWS Secrets Manager only
4. 80% test coverage in CI (`--cov-fail-under=80`)
5. All AI prompts have eval suites
6. No `# type: ignore` without justification
7. `CELERY_TASK_ALWAYS_EAGER=true` in tests only
8. Facilitator brief NEVER visible to participants
9. `GET /meetings/{id}/survey/responses` returns 404 — endpoint MUST NOT EXIST
10. Circuit breaker on all LLM calls
11. All migrations backward-compatible
12. No stack traces in production errors
13. Never rotate HMAC secrets during open surveys
14. All dependencies pinned exactly
15. Never index `respondent_hash` column

### V2 Additions:
16. **Browser mic capture disabled in production unless DEEPGRAM_API_KEY is set** — no fake transcripts in prod
17. **Notification cleanup** — delete notifications older than 90 days via nightly Celery task
18. **Survey token must be single-use per question set version** — if generated_questions changes, all old tokens still work (surveys can be updated by facilitator before sending)
19. **Public WebSocket stream never exposes transcript content** — only speaking_update events, no intelligence_alert, no transcript_chunk
20. **All email links use APP_URL config** — never hardcode localhost in email bodies

---

## SECTION 16: BUILD ORDER (V1 FIXES THEN V2 FEATURES)

### Phase 0 — Bug Fixes (Do First, Before Any New Features)
```
BUG FIX 1: Remove duplicate _intelligence_evaluation_loop in stt_service.py
BUG FIX 2: Verify all hmac.new() calls use digestmod= keyword argument
BUG FIX 3: Replace mock platform URL generation with platform_service.py
BUG FIX 4: Add typeof window check in TopBar.tsx before localStorage access
BUG FIX 5: Remove hardcoded mock speakers fallback in live/page.tsx
BUG FIX 6: Move _scrub_sensitive_data above sentry_sdk.init() in app_main.py
BUG FIX 7: Fix set_rls_org_id to accept str | UUID
BUG FIX 8: Add APP_URL to Settings config class
BUG FIX 9: Add public WebSocket stream endpoint (/session/public-stream)
BUG FIX 10: Fix null-safety in intelligence/page.tsx metric rendering

Run full test suite — all must pass before proceeding to V2 features.
```

### Phase 1A — Foundation (Complete from V1, verify works)
```
[ ] PostgreSQL schema + RLS + Alembic (including notifications table)
[ ] FastAPI scaffold + Auth0 JWT
[ ] Org + User CRUD
[ ] Next.js auth flow (dev login + Auth0)
[ ] CI pipeline passing
```

### Phase 1B — Survey Engine (Working End-to-End)
```
[ ] Meeting CRUD (no mock URLs — platform_service.py)
[ ] Survey generation (SurveyDesignerAgent with quality gates)
[ ] Survey token + submission (HMAC anonymization, upsert allowed)
[ ] Tension map generation (response rate gating)
[ ] Facilitator brief (tension map visualization)
[ ] Survey participant UI (no auth, expiry handling)
[ ] Brief UI (facilitator role check)
[ ] SendGrid emails (invitation, reminders, brief ready)
[ ] Notification system (in-app)
[ ] Survey reminder Celery task (50% and 90% threshold)

MILESTONE: DEPLOY AND CHARGE. Test with real user going through full survey flow.
```

### Phase 2A — Live Intelligence (Working End-to-End)
```
[ ] Browser mic capture (MicCapture.tsx + audio-stream WebSocket endpoint)
[ ] Mock transcript loop for dev (no Deepgram key required in dev)
[ ] WebSocket facilitator stream (real-time transcript + speaking distribution)
[ ] WebSocket public stream (anonymous speaking distribution for participants)
[ ] 3-tier intelligence evaluation loop (HiPPO + Groupthink + Missing Perspective)
[ ] Alert delivery via WebSocket
[ ] Intelligence dashboard overlay (IntelligenceDashboard.tsx)
[ ] Session end → post-mortem generation Celery task
[ ] [Phase 2A+]: Real Deepgram Nova-2 integration when DEEPGRAM_API_KEY is set
[ ] [Phase 2A+]: Zoom Apps SDK sidebar
```

### Phase 2B — Decisions & Outcomes (Complete Flow)
```
[ ] Decision creation (during and after meeting)
[ ] Post-mortem generator (Celery task, AI-powered)
[ ] Meeting report page (speaking distribution, decisions, post-mortem)
[ ] Outcome check-in form (30d/90d/180d)
[ ] Outcome check-in emails (Celery Beat daily)
[ ] Auto-refresh intelligence profile after each outcome

MILESTONE: Full Phase 1 + 2 working with real data.
```

### Phase 3 — Group Intelligence (The Moat)
```
[ ] Pattern detector weekly job (LangGraph)
[ ] Group Intelligence Profile computation
[ ] Intelligence dashboard (domain accuracy radar, patterns list)
[ ] Confidence calibration chart (CalibrationChart.tsx)
[ ] Pre-meeting pattern alerts (GET /intelligence/meetings/{id}/alerts)
[ ] Decision library + Pinecone semantic search

MILESTONE: After 10+ decisions with outcomes, GIP starts showing patterns.
```

### Phase 4 — Production Hardening
```
[ ] Terraform AWS (ECS Fargate + RDS Multi-AZ + ElastiCache)
[ ] GitHub Actions CI/CD (staging auto, production manual approval)
[ ] Datadog dashboards + PagerDuty
[ ] Sentry error tracking
[ ] SOC 2 Type II controls
[ ] Auth0 SAML/SSO
[ ] Stripe billing + seat management
[ ] GDPR export + deletion
```

---

## SECTION 17: PRICING & BUSINESS MODEL

| Tier | Price | Seats | Features |
|---|---|---|---|
| Starter | $49/seat/mo | 5–15 | Surveys, tension maps, facilitator brief, decision library |
| Growth | $99/seat/mo | 16–100 | + Live intelligence, outcomes, Group Intelligence Profile |
| Enterprise | $149/seat/mo (custom) | 100+ | + SAML/SSO, dedicated instance, SLA, CSM |

Annual: 20% discount.

**The Compounding Moat**:
- 3 months: Knows your team's patterns
- 12 months: Predicts which decisions will be wrong
- 24 months: Group Intelligence Profile is irreplaceable

**Unit Economics (Growth, 25 seats)**:
MRR $2,475 — COGS ~$35 (LLM $15 + infra $8 + Deepgram $12) — **Gross margin 98.6%**

---


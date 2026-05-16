# QUORUM — API Specification
## RESTful API + WebSocket — complete endpoint reference

---

## Base URL
- Production: `https://api.quorum.ai/v1`
- Staging:    `https://api.staging.quorum.ai/v1`

## Authentication
All endpoints require: `Authorization: Bearer {access_token}`
Token obtained from Auth0 (OAuth 2.0 PKCE flow).
Enterprise: Auth0 SSO with SAML2.

## Error Format
```json
{
  "error": {
    "code": "MEETING_NOT_FOUND",
    "message": "No meeting found with this ID in your organization",
    "details": {}
  }
}
```

## Pagination
List endpoints use cursor-based pagination:
```json
{
  "data": [...],
  "pagination": {
    "cursor": "eyJpZCI6IjEyMyJ9",
    "has_more": true,
    "total": 142
  }
}
```
Pass `?cursor=...&limit=20` to paginate.

---

## ORGANIZATION ENDPOINTS

### GET /org
Get current organization profile and settings.
```json
Response 200:
{
  "id": "uuid",
  "name": "Acme Corp",
  "domain": "acme.com",
  "plan": "growth",
  "seat_count": 25,
  "seats_used": 18,
  "settings": {
    "recording_consent_enabled": false,
    "min_survey_response_rate": 0.5,
    "meeting_platforms": ["zoom", "teams"],
    "ai_context": "We are a B2B SaaS company building developer tools"
  },
  "created_at": "2024-01-15T10:00:00Z"
}
```

### PATCH /org
Update organization settings.
```json
Request:
{
  "settings": {
    "ai_context": "Updated org context",
    "min_survey_response_rate": 0.6
  }
}
Response 200: updated org object
```

### GET /org/intelligence-profile
Get the Group Intelligence Profile for this organization.
```json
Response 200:
{
  "overall_accuracy_score": 0.71,
  "confidence_calibration_score": 0.68,
  "total_decisions_tracked": 47,
  "decisions_with_outcomes": 23,
  "domain_accuracy": {
    "product": {"accuracy": 0.78, "decisions": 18, "trend": "improving"},
    "hiring":  {"accuracy": 0.55, "decisions": 12, "trend": "stable"},
    "strategy": {"accuracy": 0.65, "decisions": 17, "trend": "declining"}
  },
  "identified_patterns": [
    {
      "pattern_id": "pat_001",
      "pattern_name": "Friday Afternoon Effect",
      "description": "Decisions made in Friday afternoon meetings have 58% lower accuracy than avg",
      "confidence": "high",
      "data_points": 9,
      "severity": 0.74,
      "recommendation": "Avoid scheduling consequential decisions on Friday afternoons"
    }
  ],
  "meeting_health": {
    "avg_survey_response_rate": 0.72,
    "avg_speaking_time_gini": 0.41,
    "hippo_frequency_score": 0.28,
    "groupthink_frequency_score": 0.19
  },
  "last_updated": "2024-06-01T03:00:00Z"
}
```

---

## USER ENDPOINTS

### GET /users
List all users in organization. Admin only.
```json
Response 200:
{
  "data": [
    {
      "id": "uuid",
      "email": "user@acme.com",
      "display_name": "Jane Smith",
      "role": "facilitator",
      "last_active_at": "2024-06-10T14:22:00Z",
      "created_at": "2024-01-20T09:00:00Z"
    }
  ],
  "pagination": {...}
}
```

### POST /users/invite
Invite a user to the organization.
```json
Request: {"email": "newuser@acme.com", "role": "member"}
Response 201: {"id": "uuid", "email": "...", "invited_at": "..."}
```

### DELETE /users/{id}
Remove a user from the organization. Admin only. Does not delete their data.
```
Response 204: No Content
```

---

## MEETING ENDPOINTS

### POST /meetings
Create a new meeting.
```json
Request:
{
  "title": "Q3 Product Roadmap Decision",
  "description": "Deciding which 3 features to prioritize for Q3",
  "scheduled_at": "2024-07-15T14:00:00Z",
  "duration_minutes": 90,
  "platform": "zoom",
  "platform_meeting_id": "85123456789",
  "domain": "product",
  "tags": ["roadmap", "q3"],
  "agenda_items": [
    {"title": "Review shortlist", "duration_mins": 20, "type": "review"},
    {"title": "Decision: top 3 features", "duration_mins": 40, "type": "decision"},
    {"title": "Owners + timeline", "duration_mins": 20, "type": "planning"},
    {"title": "Risks and dependencies", "duration_mins": 10, "type": "risk"}
  ],
  "participant_emails": [
    "jane@acme.com",
    "bob@acme.com",
    "carol@acme.com"
  ]
}

Response 201:
{
  "id": "uuid",
  "title": "Q3 Product Roadmap Decision",
  "status": "draft",
  "survey_participant_count": 4,
  ...
}
```

### GET /meetings
List meetings.
```
Query params:
  status=upcoming|past|all  (default: upcoming)
  domain=product|hiring|...
  limit=20
  cursor=...

Response 200: paginated meeting list
```

### GET /meetings/{id}
Get full meeting detail including tension map (facilitator only for tension map).
```json
Response 200:
{
  "id": "uuid",
  "title": "...",
  "status": "survey_closed",
  "survey_response_count": 3,
  "survey_participant_count": 4,
  "survey_response_rate": 0.75,
  "tension_map": {
    "headline_insight": "...",
    "consensus_areas": [...],
    "tension_areas": [...],
    "missing_perspectives": [...],
    "recommended_questions": [...]
  },
  "facilitator_brief": "markdown string",
  ...
}
```

### PATCH /meetings/{id}
Update meeting details. Cannot update after status = 'live'.
```json
Request: {"title": "New title", "agenda_items": [...]}
Response 200: updated meeting object
```

### DELETE /meetings/{id}
Cancel a meeting. Only allowed if status = 'draft' or 'survey_open'.
```
Response 204
```

---

## SURVEY ENDPOINTS

### POST /meetings/{id}/survey/generate
Trigger AI survey question generation from agenda. Returns immediately with job ID; questions appear when done.
```json
Response 202:
{
  "job_id": "uuid",
  "status": "processing",
  "estimated_seconds": 8
}
```

### GET /meetings/{id}/survey/generate/{job_id}
Poll for generation result.
```json
Response 200:
{
  "status": "completed",
  "questions": [
    {
      "id": "q1",
      "text": "How confident are you that prioritizing feature X over Y is the right call?",
      "type": "scale",
      "scale_min_label": "Not at all confident",
      "scale_max_label": "Completely confident",
      "include_confidence": false,
      "question_category": "calibration"
    },
    ...
  ],
  "primary_tension_hypothesis": "...",
  "facilitator_note": "..."
}
```

### GET /meetings/{id}/survey
Get survey questions for a participant (via survey token link, no auth required).
```
Query: ?token={survey_token}

Response 200:
{
  "meeting_title": "...",
  "meeting_description": "...",
  "deadline": "2024-07-14T18:00:00Z",
  "questions": [...],
  "already_submitted": false
}
```

### POST /meetings/{id}/survey/respond
Submit anonymous survey response. Token-auth only.
```json
Request:
{
  "token": "{survey_token}",
  "responses": [
    {"question_id": "q1", "answer": 7, "confidence": 8},
    {"question_id": "q2", "answer": "My main concern is...", "confidence": 9},
    {"question_id": "q3", "answer": ["Option A", "Option C"]}
  ]
}

Response 201:
{
  "submitted": true,
  "can_update_until": "2024-07-14T18:00:00Z"
}
```

### GET /meetings/{id}/survey/status
Get response rate. Admin/facilitator only.
```json
Response 200:
{
  "response_count": 3,
  "participant_count": 4,
  "response_rate": 0.75,
  "deadline": "2024-07-14T18:00:00Z",
  "meets_threshold": true
}
```

### POST /meetings/{id}/tension-map/generate
Trigger tension map generation. Requires ≥50% response rate.
```json
Response 202: {"job_id": "uuid", "status": "processing", "estimated_seconds": 25}
```

### GET /meetings/{id}/tension-map
Get the generated tension map. Facilitator only.
```json
Response 200:
{
  "generated_at": "...",
  "signal_quality": 0.82,
  "headline_insight": "The team is aligned on the goal but fundamentally divided on timeline feasibility",
  "consensus_areas": [
    {
      "topic": "Feature importance",
      "summary": "Strong consensus that feature X is top priority",
      "agreement_strength": 0.91,
      "confidence_level": 0.85
    }
  ],
  "tension_areas": [
    {
      "topic": "Q3 timeline feasibility",
      "tension_description": "Deep disagreement on whether 3 features can ship by September",
      "tension_strength": 0.78,
      "perspective_a": "Timeline is achievable with current team",
      "perspective_b": "Timeline requires unacknowledged scope cuts",
      "why_this_matters": "If unresolved, this will create mid-sprint conflict"
    }
  ],
  "missing_perspectives": [...],
  "recommended_questions": [...],
  "facilitator_strategy": "...",
  "red_flags": [...]
}
```

### GET /meetings/{id}/facilitator-brief
Get the formatted markdown facilitator brief.
```json
Response 200: {"brief": "# Meeting Brief\n\n## Key Insight\n..."}
```

---

## LIVE SESSION ENDPOINTS

### POST /meetings/{id}/session/start
Start a live session. Triggers Zoom/Teams bot join.
```json
Response 201:
{
  "session_id": "uuid",
  "started_at": "...",
  "websocket_url": "wss://api.quorum.ai/v1/meetings/{id}/session/stream"
}
```

### WS /meetings/{id}/session/stream
WebSocket for real-time meeting intelligence.

Client → Server messages:
```json
{"type": "ping"}
{"type": "acknowledge_alert", "alert_id": "uuid", "response": "handle_it"}
{"type": "mark_decision", "title": "...", "description": "..."}
{"type": "request_question", "context": "We're discussing timeline now"}
```

Server → Client messages:
```json
{"type": "pong", "timestamp": 1234567890}
{"type": "transcript_chunk", "data": {"speaker_hash": "a1b2c3d4", "text": "I think we should...", "start_seconds": 342}}
{"type": "speaking_update", "data": {"distribution": [{"hash": "a1b2", "seconds": 180, "pct": 0.42}]}}
{"type": "intelligence_alert", "data": {
  "alert_id": "uuid",
  "type": "groupthink",
  "urgency": "high",
  "message": "The group is converging quickly. The pre-meeting data showed significant uncertainty about the timeline.",
  "suggested_question": "Before we finalize — what's the most optimistic assumption baked into this timeline?",
  "timestamp_seconds": 1840
}}
{"type": "decision_suggested", "data": {"title": "Shortlist to 3 features", "confidence": 0.85}}
{"type": "session_ended", "data": {"total_seconds": 4200, "alerts_delivered": 3}}
```

### POST /meetings/{id}/session/end
End the live session manually.
```
Response 200: {"ended_at": "...", "total_seconds": 4200}
```

### GET /meetings/{id}/session/summary
Get post-session summary.
```json
Response 200:
{
  "session_id": "uuid",
  "duration_minutes": 70,
  "speaking_distribution": [
    {"speaker_label": "Participant A", "pct": 0.38},
    {"speaker_label": "Participant B", "pct": 0.28},
    {"speaker_label": "Participant C", "pct": 0.22},
    {"speaker_label": "Participant D", "pct": 0.12}
  ],
  "alerts_delivered": [
    {"type": "hippo", "at_minutes": 12, "actioned": true},
    {"type": "missing_perspective", "at_minutes": 45, "actioned": false}
  ],
  "decisions_marked": 2
}
```

---

## DECISION ENDPOINTS

### POST /decisions
Create a decision (can be created outside of a meeting).
```json
Request:
{
  "meeting_id": "uuid | null",
  "title": "Prioritize features X, Y, Z for Q3",
  "description": "After reviewing the shortlist...",
  "domain": "product",
  "decision_type": "prioritization",
  "options_considered": [
    {"option": "Features X, Y, Z", "pros": ["..."], "cons": ["..."], "was_chosen": true},
    {"option": "Features X, Y, W", "pros": ["..."], "cons": ["..."], "was_chosen": false}
  ],
  "key_assumptions": [
    {"assumption": "We assume design capacity is not a bottleneck", "confidence": 0.7}
  ],
  "team_confidence": 0.8
}

Response 201: full decision object with check-in dates set
```

### GET /decisions
List decisions for organization.
```
Query: domain=product&verdict=incorrect&limit=20&cursor=...
Response 200: paginated decision list
```

### GET /decisions/{id}
Get full decision with all outcomes.
```json
Response 200:
{
  "id": "uuid",
  "title": "...",
  "domain": "product",
  "team_confidence": 0.80,
  "key_assumptions": [...],
  "outcomes": [
    {
      "check_in_period": "30d",
      "outcome_verdict": "partially_correct",
      "prediction_accuracy_score": 0.5,
      "what_we_missed": "Design capacity was indeed a bottleneck",
      "recorded_at": "..."
    }
  ],
  "similar_past_decisions": [
    {"id": "uuid", "title": "...", "similarity_score": 0.87, "outcome_verdict": "correct"}
  ]
}
```

### POST /decisions/{id}/post-mortem
Submit post-mortem.
```json
Request: {"notes": "markdown text", "status": "completed"}
Response 200: updated decision
```

### POST /decisions/{id}/outcomes
Record an outcome check-in.
```json
Request:
{
  "check_in_period": "90d",
  "outcome_verdict": "partially_correct",
  "outcome_description": "We shipped 2 of 3 features. Feature Z slipped to Q4.",
  "what_we_got_right": "Features X and Y shipped on time and are performing well.",
  "what_we_missed": "Design capacity was the real constraint as the dissenting view predicted.",
  "key_assumptions_that_failed": ["We assume design capacity is not a bottleneck"],
  "lessons_learned": "Always validate design capacity before committing to feature count."
}
Response 201: created outcome
```

---

## INTELLIGENCE ENDPOINTS

### GET /intelligence/patterns
Get all identified patterns for the organization.
```json
Response 200:
{
  "patterns": [
    {
      "pattern_id": "pat_001",
      "pattern_name": "Friday Afternoon Effect",
      "description": "...",
      "severity": 0.74,
      "confidence": "high",
      "data_points": 9,
      "recommendation": "..."
    }
  ],
  "last_updated": "..."
}
```

### GET /intelligence/domain/{domain}
Get domain-specific intelligence.
```json
Response 200:
{
  "domain": "hiring",
  "accuracy_score": 0.55,
  "trend": "stable",
  "decisions_tracked": 12,
  "top_blind_spots": ["Overweighting culture fit vs. skill", "Underestimating ramp time"],
  "recommended_questions_for_next_meeting": ["What's the realistic ramp time for this role?"]
}
```

### GET /intelligence/calibration
Get confidence calibration data (how well stated confidence predicts actual accuracy).
```json
Response 200:
{
  "calibration_curve": [
    {"stated_confidence_bucket": "0.9-1.0", "actual_accuracy": 0.71, "decisions": 8},
    {"stated_confidence_bucket": "0.7-0.9", "actual_accuracy": 0.62, "decisions": 15},
    {"stated_confidence_bucket": "0.5-0.7", "actual_accuracy": 0.58, "decisions": 11}
  ],
  "overconfidence_index": 0.23,
  "interpretation": "This team is systematically overconfident. When stating 90%+ confidence, they are right only 71% of the time."
}
```

---

## WEBHOOK ENDPOINTS (Zoom/Teams/Calendar)

### POST /webhooks/zoom
Receives Zoom webhook events. Verified via HMAC signature.
```
Events handled: meeting.started, meeting.ended, meeting.participant_joined
Response 200: {"acknowledged": true}
```

### POST /webhooks/stripe
Receives Stripe billing events. Verified via Stripe webhook signature.
```
Events handled: invoice.paid, customer.subscription.deleted, customer.subscription.updated
Response 200: {"acknowledged": true}
```

---

## RATE LIMITS

| Tier | Limit |
|---|---|
| Starter | 100 req/min per org |
| Growth | 500 req/min per org |
| Enterprise | 2000 req/min per org |
| Survey submit (no auth) | 10 req/min per IP |
| AI generation endpoints | 10 req/min per org |

Rate limit headers on every response:
```
X-RateLimit-Limit: 500
X-RateLimit-Remaining: 487
X-RateLimit-Reset: 1720000060
```

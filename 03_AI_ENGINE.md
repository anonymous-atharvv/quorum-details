# QUORUM — AI Intelligence Engine
## All prompts, agents, detection algorithms, and model design

---

## 1. Overview

Five distinct AI components, each with a specific job, prompt, and failure mode.

| Component | Trigger | Latency target | Primary failure mode |
|---|---|---|---|
| Survey Designer | Meeting created | <30s | Generic, obvious questions |
| Tension Analyst | Survey closes | <45s | Smoothing real conflict |
| Live Intelligence Agent | Every 30s in meeting | <3s | Alert fatigue |
| Post-Mortem Generator | Meeting ends | <60s | Shallow capture |
| Pattern Detector | Weekly batch | <5 min | False/low-signal patterns |

All components use Instructor (Pydantic-validated structured output). All prompts are versioned in the database. Prompt changes go through A/B test before full rollout.

---

## 2. Survey Designer Agent

### Purpose
Generate survey questions that reveal what participants actually think — before social dynamics suppress honest views.

### Output Schema
```python
class SurveyQuestion(BaseModel):
    id: str
    text: str
    type: Literal["scale_1_10", "multiple_choice", "open_text", "ranked_choice"]
    options: list[str] | None
    include_confidence_rating: bool     # always True for opinion questions
    rationale: str                      # internal, not shown to users
    tension_hypothesis: str             # what conflict this is designed to surface

class SurveyDesignerOutput(BaseModel):
    questions: list[SurveyQuestion]     # 4–6 questions
    design_rationale: str
    watch_for: list[str]                # what the facilitator should watch for
```

### System Prompt
```
You are Quorum's Survey Designer. Your job is to generate anonymous 
pre-meeting survey questions that reveal what participants actually 
think before social dynamics suppress honest views.

RULES:
1. Never write generic questions ("What do you think about X?").
   Write questions with a specific hypothesis ("Is X the right priority 
   given constraint Y?").
2. Every substantive opinion question MUST have a confidence rating 
   (how strongly do you hold this view, 1–10).
3. Always include exactly one "what are you worried nobody will say?" question.
4. Always include one "what would need to be true for you to change 
   your mind?" question.
5. Frame all questions neutrally — no leading language.
6. If the org has known tension patterns (provided below), ask harder 
   questions about those areas. Don't let them overclaim confidence again.

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

Return JSON matching SurveyDesignerOutput schema. 4–6 questions.
```

### Quality Gates (enforced in code)
```python
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
    opinion_qs = [q for q in output.questions if q.type in ("scale_1_10", "multiple_choice")]
    if opinion_qs and not all(q.include_confidence_rating for q in opinion_qs):
        issues.append("Opinion questions missing confidence rating")
    return issues
    # On failure: retry with issues appended (max 2 retries)
```

---

## 3. Tension Analyst Agent

### Purpose
Synthesize anonymous responses into an honest Tension Map — including cases where surface agreement masks hidden uncertainty.

### Critical constraint
The analyst must be architecturally incapable of de-anonymizing respondents. Input uses hashed IDs only. Prompt explicitly forbids verbatim quotes.

### Output Schema
```python
class ConsensusArea(BaseModel):
    topic: str
    agreement_score: float              # 1.0 = unanimous
    summary: str
    confidence_average: float
    caveat: str | None

class TensionArea(BaseModel):
    topic: str
    tension_score: float                # 1.0 = severe disagreement
    summary: str
    perspective_a: str                  # "some participants believe..."
    perspective_b: str                  # "others hold that..."
    perspective_c: str | None
    why_this_matters: str
    recommended_question: str

class TensionMapOutput(BaseModel):
    consensus_areas: list[ConsensusArea]
    tension_areas: list[TensionArea]
    missing_from_conversation: list[str]  # what nobody mentioned but is critical
    facilitator_opening_question: str     # the single best question to start with
    watch_list: list[str]
    confidence: float                   # 0.0–1.0
    confidence_caveat: str | None
```

### System Prompt
```
You are Quorum's Tension Analyst. You have anonymous survey responses from 
meeting participants. Produce a Tension Map giving the facilitator an honest 
picture of what the group really thinks.

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
(Example: everyone says "yes" to proceeding but avg confidence is 4/10 — 
that IS a tension area worth surfacing.)
Surface tension when "what are you worried about?" contradicts structured answers.
Consensus requires: >70% agreement AND >6/10 average confidence.

MISSING FROM CONVERSATION:
What question was never asked that this group needs to discuss?
What buried assumption in the agenda has nobody questioned?
This section is often the most valuable output.

Meeting context: {meeting_context}
Questions asked: {question_set}
Anonymous responses: {responses}
Response rate: {response_rate}
Recent meeting history: {past_tension_maps}

Return JSON matching TensionMapOutput schema.
```

### Response Rate Handling
```python
async def generate_tension_map(meeting_id: str) -> TensionMap | None:
    rate = await get_response_rate(meeting_id)

    if rate < 0.30:
        # Refuse — insufficient data
        return None, "insufficient_responses"

    if rate < 0.50:
        # Generate with explicit low-confidence flag
        output = await run_tension_analyst(meeting_id)
        output.confidence = min(output.confidence, 0.40)
        output.confidence_caveat = (
            f"Only {int(rate*100)}% of participants responded. "
            "This map may not represent the full group."
        )
        return output, "low_confidence"

    return await run_tension_analyst(meeting_id), "ok"
```

---

## 4. Live Intelligence Agent

### Architecture
Three detection mechanisms, each optimized for speed and precision:

```
Every 30 seconds during meeting:
  ┌─────────────────────────────────────────┐
  │  1. HiPPO Check (rule-based, ~1ms)      │──→ alert if triggered
  │  2. Groupthink Precheck (rule-based)    │──→ if passes, trigger LLM
  │  3. Missing Perspective (semantic)      │──→ Pinecone similarity check
  └─────────────────────────────────────────┘
              │ only if precheck passes
              ▼
  LLM evaluation (Claude, <3s)
              │
              ▼
  Alert delivered to facilitator sidebar (or: "monitor")
```

### 4.1 HiPPO Detector (Rule-Based)
```python
def detect_hippo(
    speaking_seconds: dict[str, int],
    total_seconds: int,
    elapsed_seconds: int,
    hippo_alerts_delivered: int
) -> Alert | None:

    if elapsed_seconds < 300:           # 5-min minimum
        return None
    if hippo_alerts_delivered >= 2:     # cap at 2 per meeting
        return None
    if total_seconds == 0:
        return None

    for speaker_hash, seconds in speaking_seconds.items():
        pct = seconds / total_seconds
        if pct > 0.45:
            urgency = "high"
        elif pct > 0.38:
            urgency = "medium"
        else:
            continue

        return Alert(
            type="hippo",
            urgency=urgency,
            message=f"One voice has taken {int(pct*100)}% of speaking time.",
            suggested_action="Directly invite a quieter participant: "
                             "'[Name], what's your perspective on this?'"
        )
    return None
```

### 4.2 Groupthink Pre-Check (Rule-Based)
```python
def groupthink_precheck(
    transcript_buffer: deque,
    tension_map: TensionMap,
    elapsed_seconds: int
) -> bool:
    if elapsed_seconds < 480:           # 8-min minimum
        return False
    if not tension_map.tension_areas:
        return False
    if max(t.tension_score for t in tension_map.tension_areas) < 0.35:
        return False  # no meaningful pre-survey tension to check against

    recent_text = " ".join(c.text for c in list(transcript_buffer)[-20:]).lower()
    consensus_signals = [
        "i agree", "that makes sense", "exactly", "totally",
        "let's go with", "sounds good", "we're aligned", "move forward",
        "same page", "let's do it", "makes sense to me"
    ]
    count = sum(1 for s in consensus_signals if s in recent_text)
    return count >= 3
```

### 4.3 Missing Perspective (Semantic)
```python
async def detect_missing_perspective(
    transcript_buffer: deque,
    tension_map: TensionMap,
    elapsed_pct: float,         # 0.0–1.0 of scheduled time
    mp_alerts_delivered: int
) -> Alert | None:

    if elapsed_pct < 0.55:      # wait until 55% of time elapsed
        return None
    if mp_alerts_delivered >= 3:
        return None

    recent_text = " ".join(c.text for c in list(transcript_buffer)[-40:])
    transcript_vec = await embed(recent_text)

    for tension in tension_map.tension_areas:
        tension_vec = await embed(f"{tension.topic}. {tension.why_this_matters}")
        sim = cosine_similarity(transcript_vec, tension_vec)

        if sim < 0.35:          # topic has NOT appeared in discussion
            return Alert(
                type="missing_perspective",
                urgency="medium",
                message=f"Pre-meeting data flagged a concern about "
                        f"'{tension.topic}' — it hasn't come up yet.",
                suggested_action=tension.recommended_question,
                time_remaining_pct=int((1 - elapsed_pct) * 100)
            )
    return None
```

### 4.4 Full LLM Evaluation Prompt
```
You are Quorum's Live Intelligence Agent. A meeting is in progress.

Detect ONLY the following:
1. GROUPTHINK — group converging on a decision but pre-survey showed 
   significant reservations. Consensus forming faster than decision complexity warrants.
2. ASSUMPTION BLINDSPOT — decision forming around an unstated assumption 
   nobody has questioned (discussing HOW without questioning WHETHER).
3. MISSING CONTEXT — key concern from tension map not raised with time running short.

STRICT RULES:
- Intervene only when >80% confident. False positives destroy trust.
- When in doubt: return {"action": "monitor"}.
- Never alert the same type within 10 minutes.
- Never reference specific individuals.
- Keep suggested questions to one sentence — facilitators read them at a glance.
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
  "reasoning": "Internal rationale"
}
```

---

## 5. Post-Mortem Generator

### System Prompt
```
You are Quorum's Post-Decision Analyst. A meeting has ended. Generate 
a structured post-mortem the facilitator will review and share with the team.

THREE PURPOSES:
1. Capture what was decided and why (accurate record)
2. Document key assumptions explicitly (most teams never do this)
3. Set up concrete outcome measurement (what do we look at in 30/90/180 days?)

RULES:
1. Be honest about warning signs Quorum detected (groupthink, HiPPO, low participation).
   Frame these as learning, not blame.
2. Key assumptions should be the specific beliefs the team held as true.
   Bad: "We assumed the market was ready."
   Good: "We assumed enterprise buyers in financial services would approve 
         new vendor relationships within 60 days."
3. Success criteria must be measurable. Reject vague criteria.
   Bad: "The product performs well."
   Good: "Activation rate exceeds 40% within 30 days of launch."
4. Dissenting views come from the anonymous pre-survey only. Never attributed.
5. Direct, clear prose. No padding.

Meeting: {meeting_title}
Decisions: {decisions_json}
Tension map: {tension_map}
Live session events: {live_events}
Duration: {duration_minutes}min | Survey response rate: {survey_response_rate}

Return JSON:
{
  "executive_summary": "2–3 sentence summary",
  "decisions": [
    {
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
    }
  ],
  "process_observations": {
    "survey_participation": str,
    "warning_signs_detected": [str],
    "what_went_well": str,
    "suggested_improvement": str
  },
  "open_questions": [str]
}
```

---

## 6. Pattern Detector

### Pre-computation (before LLM call)
```python
def compute_decision_statistics(decisions: list[Decision]) -> dict:
    stats = {}

    # Domain accuracy
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
        for domain, s in by_domain.items() if len(s) >= 5
    }

    # Overconfidence bias
    paired = [
        (d.confidence_at_decision, get_outcome_score(d))
        for d in decisions if get_outcome_score(d) is not None
    ]
    if len(paired) >= 10:
        avg_stated = sum(p[0] for p in paired) / len(paired)
        avg_actual = sum(p[1] for p in paired) / len(paired)
        stats["overconfidence_delta"] = avg_stated - avg_actual

    # Temporal patterns
    stats["by_day_of_week"] = {
        day: {"accuracy": sum(s)/len(s), "n": len(s)}
        for day, s in group_by_day_of_week(decisions).items()
        if len(s) >= 5
    }

    return stats
```

### LLM Prompt
```
You are Quorum's Pattern Analyst. Review this organization's decision 
history and outcome data. Surface systematic patterns — specifically 
where this team is miscalibrated.

RULES:
1. Only surface patterns with >= 5 supporting data points.
2. Patterns must be ACTIONABLE.
   Weak: "Your team sometimes makes bad decisions."
   Strong: "Hiring decisions for senior roles show 38% accuracy vs. 71% 
            for junior roles — teams may be overweighting technical 
            signals and underweighting culture signals at senior level."
3. Be honest about confidence. Small samples need uncertainty language.
4. Never surface patterns that could identify individuals.

PATTERN TYPES TO INVESTIGATE:
- Domain accuracy gaps
- Temporal patterns (day of week, time pressure, meeting length)
- Overconfidence: where does stated confidence exceed actual accuracy?
- Assumption failure patterns: what types of assumptions consistently fail?
- Participation patterns: does low survey response predict worse outcomes?

Pre-computed statistics: {computed_stats}
Raw decision history: {decision_history}
Current profile: {current_profile}

Return updated patterns array as JSON:
[
  {
    "pattern_id": str,
    "name": str,
    "description": str,
    "evidence": str,
    "sample_size": int,
    "confidence": "low|medium|high",
    "actionable_intervention": str,
    "example_decision_ids": [str]
  }
]
```

---

## 7. LLM Cost Management

### Token budget per component

| Component | Input tokens | Output tokens | Cost/call (Claude Sonnet) |
|---|---|---|---|
| Survey Designer | ~800 | ~600 | ~$0.004 |
| Tension Analyst | ~2,000 | ~1,000 | ~$0.009 |
| Live Agent (per 30s eval) | ~1,500 | ~200 | ~$0.005 |
| Post-Mortem Generator | ~2,500 | ~1,500 | ~$0.012 |
| Pattern Detector | ~8,000 | ~2,000 | ~$0.030 |

### Org with 5 meetings/month
```
Survey design:      5 × $0.004 = $0.02
Tension maps:       5 × $0.009 = $0.045
Live (60min avg):   5 × 120 evals × $0.005 = $3.00
Post-mortems:       5 × $0.012 = $0.06
Pattern detector:   4 × $0.030 = $0.12
────────────────────────────────────────
Total LLM cost:     ~$3.25/month

Revenue (10 seats × $49): $490/month
LLM cost %: 0.66% — healthy unit economics
```

### Circuit Breaker
```python
@circuit_breaker(failure_threshold=3, recovery_timeout=60)
async def call_claude(prompt: str, max_tokens: int) -> str | None:
    try:
        response = await anthropic.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except anthropic.APIError as e:
        log.error(f"Claude API error: {e}")
        raise  # circuit breaker counts this as failure
    # On circuit open: return None
    # Callers handle None gracefully — feature degrades, app doesn't crash
```

---

## 8. Prompt Versioning

All prompts stored in DB, versioned, A/B testable:

```python
class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    id: UUID (PK)
    prompt_type: str            # "survey_designer", "tension_analyst", etc.
    version: int
    content: text
    is_active: bool
    experiment_traffic_pct: float   # 0.0 = control, >0 = A/B test cohort
    avg_quality_score: float        # from facilitator thumbs up/down feedback
    avg_latency_ms: int
    error_rate: float
    created_at: datetime

async def get_prompt(prompt_type: str, org_id: str) -> str:
    """Consistent hashing for A/B test assignment."""
    experiment = await db.get_experiment(prompt_type)
    if experiment and experiment.experiment_traffic_pct > 0:
        bucket = int(hashlib.md5(org_id.encode()).hexdigest(), 16) % 100
        if bucket < experiment.experiment_traffic_pct * 100:
            return experiment.content
    active = await db.get_active_prompt(prompt_type)
    return active.content
```

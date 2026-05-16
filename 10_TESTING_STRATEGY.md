# QUORUM — Testing Strategy
## Full test pyramid: unit, integration, E2E, AI quality, load testing

---

## 1. Testing Philosophy

Three non-negotiables:
1. **80% backend code coverage** enforced in CI — not optional, not aspirational
2. **AI quality is tested like code** — prompts have eval suites, not just vibes
3. **Anonymization is tested adversarially** — we try to break it in tests before attackers do

The test pyramid (ratio of tests):
```
         ┌──────────────┐
         │   E2E (10%)  │   Playwright, full user flows
         ├──────────────┤
         │ Integration  │   FastAPI test client + real DB
         │    (30%)     │
         ├──────────────┤
         │  Unit (60%)  │   Pure Python, fully mocked
         └──────────────┘
```

---

## 2. Unit Tests

### Directory structure
```
tests/
├── unit/
│   ├── test_anonymization.py        ← CRITICAL: adversarial tests
│   ├── test_detection_algorithms.py ← HiPPO, groupthink, missing perspective
│   ├── test_survey_validation.py    ← quality gates
│   ├── test_pattern_statistics.py   ← pre-computation math
│   ├── test_decision_scoring.py     ← outcome accuracy scoring
│   └── services/
│       ├── test_survey_service.py
│       ├── test_tension_map_service.py
│       └── test_intelligence_service.py
├── integration/
│   ├── test_api_meetings.py
│   ├── test_api_surveys.py
│   ├── test_api_decisions.py
│   ├── test_api_auth.py
│   ├── test_websocket_session.py
│   └── test_celery_tasks.py
├── e2e/
│   ├── test_survey_flow.spec.ts     ← Playwright
│   ├── test_facilitator_flow.spec.ts
│   └── test_decision_capture.spec.ts
├── ai_evals/
│   ├── eval_survey_designer.py      ← AI quality evals
│   ├── eval_tension_analyst.py
│   ├── eval_live_agent.py
│   └── fixtures/
│       ├── sample_agendas.json
│       ├── sample_responses.json
│       └── expected_tensions.json
└── conftest.py                      ← shared fixtures
```

### Critical unit test: Anonymization adversarial suite

```python
# tests/unit/test_anonymization.py
import pytest
import hashlib
from app.core.security import anonymize_respondent, anonymize_speaker

class TestAnonymizationAdversarial:
    """
    These tests simulate an attacker with full database read access
    trying to de-anonymize respondents. All should fail.
    """

    def test_same_user_same_meeting_produces_same_hash(self):
        """Deterministic for correlation within a meeting."""
        h1 = anonymize_respondent("user-123", "meeting-456")
        h2 = anonymize_respondent("user-123", "meeting-456")
        assert h1 == h2

    def test_same_user_different_meetings_produce_different_hashes(self):
        """Cannot track a user across meetings."""
        h1 = anonymize_respondent("user-123", "meeting-456")
        h2 = anonymize_respondent("user-123", "meeting-789")
        assert h1 != h2

    def test_different_users_same_meeting_produce_different_hashes(self):
        """Two users cannot be confused for each other."""
        h1 = anonymize_respondent("user-123", "meeting-456")
        h2 = anonymize_respondent("user-456", "meeting-456")
        assert h1 != h2

    def test_hash_length_does_not_leak_input_length(self):
        """Hash length is fixed regardless of input length."""
        h1 = anonymize_respondent("u", "m")
        h2 = anonymize_respondent("user-" + "x" * 100, "meeting-" + "y" * 100)
        assert len(h1) == len(h2)

    def test_cannot_brute_force_with_known_user_list(self, monkeypatch):
        """
        Even with the full user list, attacker cannot match hashes
        without the HMAC secret.
        """
        # Attacker has: list of all users, all hashes, NO secret
        user_ids = [f"user-{i}" for i in range(1000)]
        meeting_id = "meeting-456"
        real_hash = anonymize_respondent("user-42", meeting_id)

        # Attacker tries to match with wrong secret
        attacker_secret = "wrong-secret"
        for uid in user_ids:
            attacker_hash = hmac.new(
                attacker_secret.encode(),
                f"{uid}:{meeting_id}".encode(),
                hashlib.sha256
            ).hexdigest()[:20]
            assert attacker_hash != real_hash

    def test_hash_does_not_appear_in_logs(self, caplog):
        """Ensure user_id never appears in log output."""
        import logging
        with caplog.at_level(logging.DEBUG):
            anonymize_respondent("user-secret-id", "meeting-456")
        assert "user-secret-id" not in caplog.text

    def test_two_hashes_from_different_meetings_are_uncorrelatable(self):
        """
        An attacker with hashes from two meetings cannot determine
        they came from the same person.
        """
        hash_m1 = anonymize_respondent("user-123", "meeting-001")
        hash_m2 = anonymize_respondent("user-123", "meeting-002")
        # They must be completely different
        assert hash_m1 != hash_m2
        # And share no detectable pattern (first 4 chars differ)
        assert hash_m1[:4] != hash_m2[:4]
```

### Detection algorithm tests

```python
# tests/unit/test_detection_algorithms.py
from app.intelligence.agents.live_agent import detect_hippo, groupthink_precheck

class TestHiPPODetector:
    def test_no_alert_before_5_minutes(self):
        speaking = {"hashA": 200, "hashB": 10}  # hashA dominates
        result = detect_hippo(speaking, total_seconds=210, elapsed_seconds=210, hippo_alerts_delivered=0)
        assert result is None  # too early

    def test_alert_fires_at_45_percent(self):
        speaking = {"hashA": 280, "hashB": 100, "hashC": 50}
        result = detect_hippo(speaking, total_seconds=430, elapsed_seconds=430, hippo_alerts_delivered=0)
        assert result is not None
        assert result.type == "hippo"
        assert result.urgency in ("medium", "high")

    def test_no_alert_at_38_percent_medium_threshold(self):
        speaking = {"hashA": 160, "hashB": 100, "hashC": 100, "hashD": 70}
        result = detect_hippo(speaking, total_seconds=430, elapsed_seconds=500, hippo_alerts_delivered=0)
        assert result is None  # 37%, below threshold

    def test_caps_at_2_alerts(self):
        speaking = {"hashA": 900, "hashB": 100}
        result = detect_hippo(speaking, total_seconds=1000, elapsed_seconds=600, hippo_alerts_delivered=2)
        assert result is None  # already at limit

    def test_no_division_by_zero_empty_speaking(self):
        result = detect_hippo({}, total_seconds=0, elapsed_seconds=0, hippo_alerts_delivered=0)
        assert result is None

class TestGroupthinkPrecheck:
    def test_triggers_on_consensus_signals_with_tension(self, sample_tension_map_high_tension):
        buffer = deque([
            Chunk(text="I agree, let's go with this"),
            Chunk(text="Totally, sounds good to me"),
            Chunk(text="I'm aligned, let's move forward"),
            Chunk(text="Makes sense, let's do it"),
        ])
        result = groupthink_precheck(buffer, sample_tension_map_high_tension, elapsed_seconds=600)
        assert result is True

    def test_no_trigger_without_tension_in_map(self, sample_tension_map_no_tension):
        buffer = deque([Chunk(text="I agree " * 10)])
        result = groupthink_precheck(buffer, sample_tension_map_no_tension, elapsed_seconds=600)
        assert result is False  # no pre-survey tension to compare against

    def test_no_trigger_before_8_minutes(self, sample_tension_map_high_tension):
        buffer = deque([Chunk(text="I agree totally, let's move forward")])
        result = groupthink_precheck(buffer, sample_tension_map_high_tension, elapsed_seconds=400)
        assert result is False
```

---

## 3. Integration Tests

### FastAPI test client with real database

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.main import app
from app.core.database import get_db
from app.models import Base

TEST_DATABASE_URL = "postgresql+asyncpg://quorum_test:quorum_test@localhost:5432/quorum_test"

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(test_engine):
    async with AsyncSession(test_engine) as session:
        yield session
        await session.rollback()  # Clean up after each test

@pytest_asyncio.fixture
async def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()

# Factory fixtures using factory-boy
@pytest.fixture
def org(db_session):
    return OrganizationFactory(session=db_session)

@pytest.fixture
def facilitator(db_session, org):
    return UserFactory(session=db_session, org=org, role="facilitator")

@pytest.fixture
def auth_headers(facilitator):
    token = create_test_jwt(facilitator)
    return {"Authorization": f"Bearer {token}"}
```

```python
# tests/integration/test_api_surveys.py
import pytest

class TestSurveySubmission:
    async def test_submit_anonymous_response_success(self, client, meeting, auth_headers):
        """Full happy path: submit survey, verify anonymization."""
        # Arrange
        survey_token = meeting.participants[0].survey_token
        payload = {
            "responses": [
                {"question_id": "q1", "answer": "7", "confidence": 8},
                {"question_id": "q2", "answer": "We need more data before deciding"}
            ]
        }

        # Act
        response = await client.post(
            f"/meetings/{meeting.id}/survey/respond",
            json=payload,
            headers={"X-Survey-Token": survey_token}  # no auth header
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["submitted"] is True

        # Verify: response stored with hash, not user_id
        from app.models import SurveyResponse
        stored = await db_session.execute(
            select(SurveyResponse).where(SurveyResponse.meeting_id == meeting.id)
        )
        record = stored.scalar_one()
        assert record.respondent_hash is not None
        assert "user_id" not in record.__dict__

    async def test_duplicate_submission_updates_not_duplicates(self, client, meeting):
        """Second submission from same token updates, doesn't create duplicate."""
        token = meeting.participants[0].survey_token
        await client.post(
            f"/meetings/{meeting.id}/survey/respond",
            json={"responses": [{"question_id": "q1", "answer": "5"}]},
            headers={"X-Survey-Token": token}
        )
        await client.post(
            f"/meetings/{meeting.id}/survey/respond",
            json={"responses": [{"question_id": "q1", "answer": "8"}]},  # updated
            headers={"X-Survey-Token": token}
        )
        count = await db_session.scalar(
            select(func.count(SurveyResponse.id))
            .where(SurveyResponse.meeting_id == meeting.id)
        )
        assert count == 1  # not 2

    async def test_facilitator_cannot_see_individual_responses(self, client, meeting, auth_headers):
        """Facilitator only sees aggregate tension map, never raw responses."""
        response = await client.get(
            f"/meetings/{meeting.id}/survey/responses",  # this endpoint should NOT exist
            headers=auth_headers
        )
        assert response.status_code == 404  # endpoint does not exist

    async def test_expired_survey_token_rejected(self, client, meeting):
        """Tokens expire 14 days after meeting creation."""
        expired_token = meeting.participants[0].survey_token
        # Simulate token expiry
        meeting.participants[0].invited_at = datetime.utcnow() - timedelta(days=15)
        response = await client.post(
            f"/meetings/{meeting.id}/survey/respond",
            json={"responses": []},
            headers={"X-Survey-Token": expired_token}
        )
        assert response.status_code == 410  # Gone
```

---

## 4. AI Quality Evaluation Suite

This is the most critical and most often skipped testing category.
**Prompts are code. They need tests.**

### Evaluation framework

```python
# tests/ai_evals/eval_framework.py
from dataclasses import dataclass
from typing import Callable

@dataclass
class EvalCase:
    name: str
    input: dict
    evaluators: list[Callable]  # functions that return (passed: bool, score: float, reason: str)

@dataclass
class EvalResult:
    case_name: str
    passed: bool
    score: float              # 0.0-1.0
    failures: list[str]
    latency_ms: int

async def run_eval_suite(cases: list[EvalCase], agent_fn: Callable) -> list[EvalResult]:
    results = []
    for case in cases:
        start = time.time()
        output = await agent_fn(case.input)
        latency = int((time.time() - start) * 1000)

        failures = []
        scores = []
        for evaluator in case.evaluators:
            passed, score, reason = evaluator(output)
            scores.append(score)
            if not passed:
                failures.append(reason)

        results.append(EvalResult(
            case_name=case.name,
            passed=len(failures) == 0,
            score=sum(scores) / len(scores),
            failures=failures,
            latency_ms=latency
        ))
    return results
```

### Survey Designer Evaluators

```python
# tests/ai_evals/eval_survey_designer.py

def eval_has_worried_question(output: SurveyDesignerOutput) -> tuple:
    has_worried = any(
        "worried" in q.text.lower() or "concern" in q.text.lower()
        for q in output.questions
    )
    return has_worried, 1.0 if has_worried else 0.0, \
           "Missing 'what are you worried about' question"

def eval_has_falsifiability_question(output: SurveyDesignerOutput) -> tuple:
    has_it = any(
        "change your mind" in q.text.lower() or "wrong" in q.text.lower()
        for q in output.questions
    )
    return has_it, 1.0 if has_it else 0.0, \
           "Missing 'what would change your mind' question"

def eval_questions_are_specific(output: SurveyDesignerOutput) -> tuple:
    generic_phrases = ["what do you think", "how do you feel", "any thoughts"]
    generic_count = sum(
        1 for q in output.questions
        if any(p in q.text.lower() for p in generic_phrases)
    )
    score = 1.0 - (generic_count / len(output.questions))
    return generic_count == 0, score, \
           f"{generic_count} generic question(s) detected"

def eval_confidence_on_opinion_questions(output: SurveyDesignerOutput) -> tuple:
    opinion_qs = [q for q in output.questions if q.type in ("scale_1_10", "multiple_choice")]
    if not opinion_qs:
        return True, 1.0, ""
    missing = [q for q in opinion_qs if not q.include_confidence_rating]
    return len(missing) == 0, 1.0 - len(missing)/len(opinion_qs), \
           f"{len(missing)} opinion question(s) missing confidence rating"

def eval_question_count_in_range(output: SurveyDesignerOutput) -> tuple:
    n = len(output.questions)
    in_range = 4 <= n <= 6
    return in_range, 1.0 if in_range else 0.5, \
           f"Question count {n} outside range [4,6]"

# Test cases
SURVEY_DESIGNER_CASES = [
    EvalCase(
        name="Product roadmap prioritization meeting",
        input={
            "meeting_title": "Q3 Product Roadmap Review",
            "meeting_description": "Deciding which features to build in Q3 given capacity constraints",
            "agenda_items": [
                {"title": "Review Q2 learnings", "duration_minutes": 15},
                {"title": "Rank top 5 feature candidates", "duration_minutes": 30},
                {"title": "Resource allocation", "duration_minutes": 15}
            ],
            "org_context": "B2B SaaS, 80 employees, Series B",
            "past_tension_patterns": []
        },
        evaluators=[
            eval_has_worried_question,
            eval_has_falsifiability_question,
            eval_questions_are_specific,
            eval_confidence_on_opinion_questions,
            eval_question_count_in_range,
        ]
    ),
    EvalCase(
        name="Hiring decision for senior engineer",
        input={
            "meeting_title": "Hiring Decision: Staff Engineer Candidate",
            "meeting_description": "Final decision on hiring Jane Doe for Staff Engineer role",
            "agenda_items": [
                {"title": "Review interview feedback", "duration_minutes": 20},
                {"title": "Go/no-go decision", "duration_minutes": 15},
            ],
            "org_context": "Engineering team, 25 engineers",
            "past_tension_patterns": ["Historically overconfident in hiring decisions (62% accuracy)"]
        },
        evaluators=[
            eval_has_worried_question,
            eval_questions_are_specific,
            eval_confidence_on_opinion_questions,
        ]
    ),
]

# Run: pytest tests/ai_evals/eval_survey_designer.py -v --no-header
# Cost: ~$0.05 per full suite run (budget 3 runs per PR)
```

### Tension Analyst Evaluators

```python
def eval_no_verbatim_quotes(output: TensionMap, responses: list[dict]) -> tuple:
    """Critical: Tension map must never quote responses verbatim."""
    tension_text = " ".join([
        t.summary + t.perspective_a + t.perspective_b
        for t in output.tension_areas
    ])
    for response in responses:
        for answer in response.get("responses", []):
            if isinstance(answer.get("answer"), str) and len(answer["answer"]) > 15:
                # Check for 5+ consecutive words from any response appearing in output
                words = answer["answer"].split()
                for i in range(len(words) - 4):
                    phrase = " ".join(words[i:i+5]).lower()
                    if phrase in tension_text.lower():
                        return False, 0.0, f"Verbatim quote detected: '{phrase}'"
    return True, 1.0, ""

def eval_tension_score_calibration(output: TensionMap) -> tuple:
    """Tension scores should be meaningful, not all 0.5."""
    if not output.tension_areas:
        return True, 1.0, ""
    scores = [t.tension_score for t in output.tension_areas]
    variance = sum((s - 0.5)**2 for s in scores) / len(scores)
    # Very low variance means all scores cluster around 0.5 (lazy model)
    calibrated = variance > 0.02
    return calibrated, min(variance * 20, 1.0), \
           "Tension scores are poorly calibrated (all ~0.5)"

def eval_missing_section_not_empty(output: TensionMap) -> tuple:
    has_missing = len(output.missing_from_conversation) > 0
    return has_missing, 1.0 if has_missing else 0.3, \
           "Missing-from-conversation section is empty (model didn't try)"
```

### Passing thresholds (enforced in CI weekly)
```
Survey Designer:  avg score >= 0.85 across all cases
Tension Analyst:  avg score >= 0.80 (lower due to complexity)
Live Agent:       false positive rate < 10% on monitor-only fixtures
Post-Mortem:      key_assumptions populated in >= 90% of cases
Pattern Detector: no patterns surfaced with n < 5 data points
```

---

## 5. End-to-End Tests (Playwright)

```typescript
// tests/e2e/test_survey_flow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Survey submission flow', () => {

  test('Participant submits survey via email link without account', async ({ page }) => {
    // Given: a meeting was created and survey sent
    const surveyUrl = await getSurveyUrl(); // helper that creates test meeting

    // When: participant opens survey link
    await page.goto(surveyUrl);

    // Then: no login required
    await expect(page.locator('text=Sign in')).not.toBeVisible();
    await expect(page.locator('[data-testid=survey-form]')).toBeVisible();

    // When: participant submits responses
    await page.locator('[data-testid=question-scale-0]').fill('7');
    await page.locator('[data-testid=confidence-0]').fill('8');
    await page.locator('[data-testid=question-text-1]').fill('I am worried about the timeline.');
    await page.locator('[data-testid=submit-survey]').click();

    // Then: success state shown
    await expect(page.locator('text=Your response has been recorded')).toBeVisible();
    await expect(page.locator('text=anonymous')).toBeVisible(); // remind them

    // And: can update response
    await page.locator('text=Update my response').click();
    await expect(page.locator('[data-testid=survey-form]')).toBeVisible();
  });

  test('Facilitator sees tension map after sufficient responses', async ({ page }) => {
    // Setup: create meeting with 5 participant responses
    const { meetingId, facilitatorToken } = await setupMeetingWithResponses(5);

    await page.goto(`/meetings/${meetingId}/brief`);
    await page.locator('[data-testid=auth-header]')
      .evaluate(el => el.setAttribute('Authorization', `Bearer ${facilitatorToken}`));

    await expect(page.locator('[data-testid=tension-map]')).toBeVisible();
    await expect(page.locator('[data-testid=tension-area]')).toHaveCount({ min: 1 });
    await expect(page.locator('[data-testid=facilitator-opening-question]')).not.toBeEmpty();

    // Tension map must NOT show individual names
    await expect(page.locator('text=user@company.com')).not.toBeVisible();
    await expect(page.locator('text=@')).not.toBeVisible({ timeout: 1000 });
  });
});
```

---

## 6. Load Testing

### Target performance benchmarks

| Endpoint | p50 | p95 | p99 | Max RPS |
|---|---|---|---|---|
| POST /meetings/{id}/survey/respond | 50ms | 150ms | 300ms | 500 |
| GET /meetings/{id}/tension-map | 200ms | 500ms | 1s | 100 |
| WS /meetings/{id}/session/stream | <400ms latency | — | — | 50 concurrent |
| POST /decisions | 100ms | 300ms | 500ms | 200 |
| GET /org/intelligence-profile | 300ms | 800ms | 1.5s | 50 |

### Load test script (k6)

```javascript
// tests/load/survey_submission.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 50 },    // ramp up
    { duration: '3m', target: 50 },    // sustained load
    { duration: '1m', target: 200 },   // spike (survey deadline approaching)
    { duration: '1m', target: 0 },     // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95th percentile < 500ms
    http_req_failed: ['rate<0.01'],    // error rate < 1%
  },
};

export default function () {
  const surveyToken = __ENV.SURVEY_TOKEN;
  const meetingId = __ENV.MEETING_ID;

  const res = http.post(
    `${__ENV.API_URL}/meetings/${meetingId}/survey/respond`,
    JSON.stringify({
      responses: [
        { question_id: 'q1', answer: '7', confidence: 8 },
        { question_id: 'q2', answer: 'Load test response' }
      ]
    }),
    {
      headers: {
        'Content-Type': 'application/json',
        'X-Survey-Token': surveyToken
      }
    }
  );

  check(res, {
    'status is 201 or 200': (r) => [200, 201].includes(r.status),
    'response time < 500ms': (r) => r.timings.duration < 500,
  });

  sleep(1);
}
```

Run: `k6 run -e API_URL=https://staging.api.quorum.ai -e SURVEY_TOKEN=xxx tests/load/survey_submission.js`

---

## 7. Test Data Management

```python
# tests/factories.py
import factory
from factory.alchemy import SQLAlchemyModelFactory

class OrganizationFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Organization
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(uuid4)
    name = factory.Sequence(lambda n: f"Test Org {n}")
    slug = factory.LazyAttribute(lambda o: o.name.lower().replace(" ", "-"))
    plan = "growth"
    seat_count = 25

class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(uuid4)
    org = factory.SubFactory(OrganizationFactory)
    org_id = factory.LazyAttribute(lambda o: o.org.id)
    auth0_id = factory.Sequence(lambda n: f"auth0|test_user_{n}")
    email = factory.Sequence(lambda n: f"user{n}@testorg.com")
    role = "member"

class MeetingFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Meeting

    id = factory.LazyFunction(uuid4)
    org = factory.SubFactory(OrganizationFactory)
    org_id = factory.LazyAttribute(lambda o: o.org.id)
    title = factory.Sequence(lambda n: f"Test Meeting {n}")
    scheduled_at = factory.LazyFunction(lambda: datetime.utcnow() + timedelta(days=1))
    status = "survey_open"
    agenda_items = [{"title": "Test agenda item", "duration_minutes": 30}]
```

# QUORUM — Complete Startup Build Package
## Collective Intelligence Platform | All files index and reading guide

---

## What This Package Is

This is the complete technical and business specification for **Quorum** — a B2B AI platform that makes organizational group decisions measurably better. Every file in this package is written to be immediately actionable: hand the AI Engine doc to your ML engineer, hand the Schema doc to your backend engineer, hand the Business Model doc to your co-founder or first sales hire.

---

## The Problem (One Paragraph)

Organizations lose $37 billion annually in the US from decisions made poorly in meetings. The root cause is not a lack of intelligence — it is social dynamics: the HiPPO effect (highest paid person's opinion wins), groupthink (social pressure kills honest dissent), and information pooling failure (people in the room have the answer but never say it). Every meeting AI tool built so far has solved the wrong problem: they make meetings faster to process, not better to be in. Quorum is the first platform designed specifically to improve the quality of the group decision itself — before, during, and after the meeting.

---

## The Product (Three Sentences)

Before the meeting: Quorum sends AI-generated anonymous surveys to all participants, synthesizes what people actually think (not what they'll say in the room), and gives the facilitator a tension map and recommended discussion structure. During the meeting: Quorum joins via Zoom/Teams/Meet, detects HiPPO dynamics, groupthink signals, and missing perspectives in real-time, and surfaces precise interventions to the facilitator. After the meeting: Quorum captures decisions structurally, generates post-mortems, schedules outcome check-ins at 30/90/180 days, and — over time — builds a Group Intelligence Profile: your team's specific blind spots, overconfidence patterns, and prediction accuracy by domain.

---

## Privacy Model (Why This Works)

Unlike Sovereign (the abandoned v1 concept), Quorum has no passive individual surveillance:

| Data point | How Quorum handles it |
|---|---|
| Survey responses | One-way HMAC hash at collection — mathematically irreversible |
| Speaker identity in meetings | Anonymous hash, meeting-scoped, resets each meeting |
| Individual performance | Never stored, never surfaced — product principle |
| Org data | Deleted within 24hrs on request via single API call |
| Audio recordings | Off by default. Org opt-in only. Deleted after 30 days. |

The result: GDPR compliant by design, SOC 2 Type II achievable, no DPA negotiations required for most customers.

---

## File Index

### `00_MASTER_BUILD_PROMPT.md`
**For:** AI coding agents (Claude Code, Cursor, GPT-4o)
**Contains:** Complete system context, architecture, tech stack, data models, API spec, build order, environment variables, critical constraints
**How to use:** Feed this file as the system prompt / context file to your AI coding agent before starting any development work. It is the single source of truth.

---

### `01_PRD.md`
**For:** Product manager, co-founder, first hire
**Contains:** Problem definition, target personas, full user story set (47 stories across all phases), feature priority matrix, non-functional requirements, out-of-scope list
**How to use:** Use this to align your team on what you're building and in what order. Use the priority matrix to cut scope when timelines slip. Share with design candidates as the design brief.

---

### `02_TECHNICAL_ARCHITECTURE.md`
**For:** CTO, lead engineer, infrastructure engineer
**Contains:** Full system architecture diagram (ASCII), component breakdown, file structure, real-time pipeline detail (MeetingStreamProcessor), frontend architecture, database design, integration architecture (Zoom, Calendar), security design (auth flow, anonymization), scalability plan, AWS infrastructure layout, CI/CD pipeline, observability strategy
**How to use:** This is the engineering blueprint. Every engineering decision made before the first line of code should be traceable to this document.

---

### `03_AI_ENGINE.md`
**For:** ML engineer, AI engineer, founding engineer
**Contains:** All five AI component designs (Survey Designer, Tension Analyst, Live Intelligence Agent, Post-Mortem Generator, Pattern Detector), all system prompts (production-ready), output schemas (Pydantic), quality gates, detection algorithms (HiPPO rule-based, Groupthink pre-check, Missing Perspective semantic), LLM cost model, circuit breaker pattern, prompt versioning and A/B test system
**How to use:** This is your AI layer specification. Implement exactly as written. Do not simplify the quality gates — they are what separates Quorum from a demo. The cost model proves unit economics work at scale.

---

### `04_DATABASE_SCHEMA.md`
**For:** Backend engineer, data engineer
**Contains:** Complete PostgreSQL 16 schema (all CREATE TABLE, CREATE INDEX, constraints), Row Level Security policies, anonymization functions (HMAC-SHA256), full-text search setup (tsvector trigger), audit log design, data retention and purge functions, seed data, Alembic migration structure
**How to use:** Run the SQL in order. Enable RLS before any production data enters the system — it is the last line of defence against cross-org data leakage. Never bypass it with a superuser connection from application code.

---

### `05_API_SPECIFICATION.md`
**For:** Backend engineer, frontend engineer, integration partners
**Contains:** All REST endpoints (grouped by domain), request/response schemas, WebSocket event protocol (server→client and client→server), error format, authentication spec, rate limits, webhook event design (Zoom/Teams), pagination convention
**How to use:** Frontend and backend teams build against this contract simultaneously. Use the WebSocket spec to implement the live meeting sidebar. Use the webhook design to build the Zoom integration.

---

### `06_BUSINESS_MODEL.md`
**For:** CEO, co-founder, first sales hire, investors
**Contains:** Pricing tiers (Starter/Growth/Enterprise) with full justification, unit economics (CAC, LTV, payback period targets), go-to-market strategy (ICP, sales motion, channels), competitive landscape (Otter, Fireflies, Slido — why they don't compete), moat analysis, 18-month revenue model, fundraising narrative, investor-facing metrics dashboard
**How to use:** Use the pricing section to set your first prices with confidence. Use the GTM section to hire your first sales rep. Use the metrics section to build your investor data room.

---

### `07_USER_STORIES.md`
**For:** Product manager, designer, QA engineer
**Contains:** 47 user stories organized by persona (Alex the Facilitator, Sam the Participant, Jordan the Admin, Morgan the Decision Maker) and phase (Pre-meeting, Live, Post-decision, Group Intelligence), each with Given/When/Then acceptance criteria and edge cases
**How to use:** Sprint planning input. QA test case source. Design brief for each screen. Every story has acceptance criteria tight enough to write automated tests against.

---

## Recommended Build Sequence

```
Month 1–2:  Phase 1A + 1B  (survey engine, tension map, facilitator brief)
             → Deploy. Charge for this alone. Validate product-market fit.

Month 3–4:  Phase 2A       (Zoom integration, real-time STT pipeline)
             → Add live meeting intelligence. Upgrade early customers.

Month 5:    Phase 2B       (HiPPO, groupthink, missing perspective detectors)
             → Full Phase 2. This is when the product becomes remarkable.

Month 6:    Phase 3        (decisions, post-mortems, outcome tracking)
             → Now you have longitudinal data. Moat starts building.

Month 7–8:  Phase 4        (Group Intelligence Profile, pattern detector)
             → Product becomes irreplaceable. Churn collapses.

Month 9–12: Phase 5        (Production hardening, SOC 2, enterprise sales)
             → Series A fundraise on outcome data proving decision improvement.
```

---

## The Moat, Clearly Stated

After 3 months: Quorum knows your team's patterns.
After 12 months: Quorum can predict which of your decision types will be wrong.
After 24 months: The Group Intelligence Profile is irreplaceable. Switching means losing years of calibrated decision history.

This is the rarest thing in B2B software: a product that is not just sticky because of integrations or workflow lock-in, but because the data itself — your team's specific decision fingerprint — cannot exist anywhere else.

---

## The Pitch (One Page Version)

**Problem:** Organizations lose $37B/year to bad meeting decisions. No tool addresses decision quality — only efficiency.

**Solution:** Quorum — AI that makes group decisions measurably better. Before (anonymous elicitation), during (real-time intelligence), and after (outcome tracking).

**Privacy:** Anonymous by design. No individual surveillance. GDPR compliant at architecture level.

**Traction target (Month 12):** 50 paying orgs, $180K ARR, 3 enterprise pilots, 500+ tracked decisions with outcome data.

**Moat:** Decision outcome database. Group Intelligence Profiles. The longer orgs use Quorum, the more irreplaceable it becomes.

**Ask:** $2.5M seed. 18 months runway. Full product through Phase 4. 3 enterprise design partners signed before raise closes.

---

*Package version: 1.0 | Generated: 2026*
*All files in this package are internally consistent. The Master Build Prompt references all other documents.*

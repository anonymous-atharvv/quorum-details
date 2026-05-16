# QUORUM — Product Requirements Document (PRD)
## Version 1.0 | Collective Intelligence Platform

---

## 1. Executive Summary

### Problem
Organizations lose $37 billion annually in the US to decisions made poorly in meetings. The root causes are not intelligence failures — they are social dynamics failures: the HiPPO effect (highest paid person's opinion dominates), groupthink (social pressure kills dissent), information pooling failure (people in the room have the answer but don't share), and recency bias (whoever spoke last shapes the conclusion).

Every meeting AI tool built to date addresses efficiency: faster transcription, better summaries, cleaner action items. Zero tools address decision quality.

### Solution
Quorum is the first AI platform designed to make the group decision itself better — not the record-keeping after the fact. It operates in three phases: anonymously surfacing what people actually think before the meeting, detecting social dynamics failures in real-time during the meeting, and tracking whether decisions turn out to be right.

### Business Case
- Target: B2B, knowledge-worker organizations
- Starting segment: technology companies 50-5,000 employees
- Pricing: $49-$149/seat/month
- TAM: $4.2B (US knowledge worker organizations with >20 employees)
- Unique moat: decision outcome database — gets more valuable the longer organizations use it

---

## 2. Target Customer

### Primary Persona: "The Frustrated Head of Product"
- Title: VP Product, Director of Product, Chief Product Officer
- Company size: 50-500 employees, Series A to Series C
- Pain: Endless meetings where the loudest voice wins, decisions get revisited constantly because people didn't actually commit, and post-mortems never happen so the same mistakes repeat
- Budget authority: yes
- Current tools: Notion, Linear, Miro, Otter — none of which address group decision quality
- Will pay for: clear ROI tied to decision quality, not just efficiency

### Secondary Persona: "The Thoughtful CEO"
- Title: CEO, Co-founder
- Company size: 20-200 employees
- Pain: Building a culture of rigorous decision-making; tired of decisions being made based on who argues longest
- Budget authority: yes
- Unique value: Quorum is a culture signal — "we take decision quality seriously"

### Enterprise Persona: "The Chief Strategy Officer"
- Title: CSO, SVP Strategy, Chief of Staff
- Company size: 1,000+
- Pain: Major strategic decisions made by committees that systematically overestimate confidence and underestimate risk
- Budget: Large — enterprise contract $100k-$500k/year
- Key need: SOC 2, SAML/SSO, dedicated instance

### Non-Customer (do NOT target)
- Individual contributors without meeting facilitation role
- Companies with <15 employees (too small for group dynamics problem to manifest clearly)
- Non-knowledge-worker industries (manufacturing, retail)
- HR departments (Quorum is explicitly NOT a performance tool)

---

## 3. User Stories by Phase

### Phase 1: Pre-Meeting Survey

**US-001: Meeting Creation**
As a facilitator, I can create a meeting in Quorum and connect it to my calendar event, so that survey invitations are automatically sent to all participants.
- Acceptance: Quorum auto-detects calendar event participants from Google Calendar or Outlook integration
- Acceptance: Meeting can be created manually if calendar not connected

**US-002: AI Question Generation**
As a facilitator, I can input my meeting agenda and have Quorum generate anonymous survey questions, so that I don't have to think of the right questions myself.
- Acceptance: Questions generated within 30 seconds of agenda submission
- Acceptance: Questions are genuinely insightful, not generic — specific to the agenda topics
- Acceptance: Facilitator can edit, add, or remove any generated question before sending
- Acceptance: Questions always include a confidence rating option (how strongly do you hold this view 1-10)

**US-003: Anonymous Survey Submission**
As a meeting participant, I can submit my honest views through Quorum before the meeting without my colleagues seeing my individual responses.
- Acceptance: Survey accessible via email link — no Quorum account required to respond
- Acceptance: UI clearly communicates anonymization (not just said but shown: "your response is anonymous even to your manager")
- Acceptance: Participant can update responses until deadline
- Acceptance: Response time under 5 minutes for a 5-question survey

**US-004: Tension Map**
As a facilitator, I receive a Tension Map after survey closes that shows me where views are aligned and where they diverge.
- Acceptance: Generated automatically when survey closes (or at deadline, whichever first)
- Acceptance: Shows consensus areas, tension areas, and confidence distribution
- Acceptance: Explicitly calls out "what nobody seems to be saying" as a separate section
- Acceptance: Never reveals which individual said what
- Acceptance: Includes recommended questions for the facilitator to ask

**US-005: Response Rate Gate**
As a platform, I require a minimum 50% response rate before generating a Tension Map, so that results aren't statistically meaningless.
- Acceptance: Reminder email sent at 50% of deadline elapsed, 90% of deadline elapsed
- Acceptance: Facilitator can request map generation with <50% rate but receives explicit confidence warning
- Acceptance: Dashboard shows live response rate counter

---

### Phase 2: Live Meeting Intelligence

**US-006: Meeting Room Join**
As Quorum, I join the meeting via Zoom/Teams/Meet integration and begin processing audio in real-time.
- Acceptance: Join happens automatically when facilitator starts session in Quorum app
- Acceptance: Participants see a notification that Quorum is active (transparency is required)
- Acceptance: Quorum never stores raw audio unless org has explicitly enabled recording with consent flow

**US-007: HiPPO Detection**
As a facilitator, I am alerted when one participant is dominating the conversation beyond healthy norms.
- Acceptance: Alert triggers when any participant exceeds 40% of total speaking time AND the meeting has been running >8 minutes
- Acceptance: Alert is shown only to the facilitator (not broadcast to all participants)
- Acceptance: Alert includes specific suggestion: "Consider inviting [role: quiet participant] to share their view on [current topic]"
- Acceptance: Alert can be dismissed with "I'm aware" or "handle it" options
- Acceptance: Maximum 2 HiPPO alerts per meeting (to prevent alert fatigue)

**US-008: Groupthink Detection**
As a facilitator, I am alerted when the group is converging on a decision too quickly given the pre-survey data.
- Acceptance: Triggers when: (a) consensus forming in <8 minutes on a complex decision, AND (b) pre-survey showed >30% of participants had reservations about this direction
- Acceptance: Alert surfaces the specific tension from the pre-survey: "Before this decision is finalized, note that the pre-meeting data showed uncertainty about X"
- Acceptance: Quorum suggests a specific question to ask: "What would need to be true for this decision to be wrong?"

**US-009: Missing Perspective**
As a facilitator, I am prompted when a key concern from the pre-survey has not been raised after substantial meeting time has elapsed.
- Acceptance: Triggers when: (a) a tension area from the Tension Map has not appeared in the transcript, AND (b) >60% of scheduled meeting time has passed
- Acceptance: Prompt is specific: names the topic and suggests the exact question to ask
- Acceptance: Maximum 3 missing-perspective prompts per meeting

**US-010: Participant Dashboard**
As a meeting participant, I can see the real-time speaking time distribution on my Quorum sidebar, so that I'm self-aware about participation balance.
- Acceptance: Shown as anonymous color-coded segments (participant A, B, C — not names)
- Acceptance: Updates every 60 seconds
- Acceptance: Does not show individual names even to self — only distribution

---

### Phase 3: Post-Decision Tracking

**US-011: Decision Capture**
As a facilitator, I can mark key decisions during or after the meeting for tracking.
- Acceptance: Can mark during meeting via sidebar button
- Acceptance: Quorum auto-suggests decisions based on transcript analysis ("It sounds like a decision was made about X — would you like to track it?")
- Acceptance: Each decision records: title, description, options considered, key assumptions, team confidence level

**US-012: Post-Mortem Generation**
As a facilitator, I receive an AI-generated post-mortem document within 24 hours of meeting end.
- Acceptance: Post-mortem includes: what was decided, why, key assumptions made, what the anonymous survey data showed, any warning signs detected (groupthink, HiPPO)
- Acceptance: Post-mortem is editable by facilitator before sharing with team
- Acceptance: Explicitly flags assumptions that were NOT discussed but might be critical

**US-013: Outcome Check-Ins**
As a facilitator, I receive automated prompts at 30, 90, and 180 days to record what actually happened.
- Acceptance: Check-in is a structured 5-question form (what happened, what we got right, what we missed, which assumptions failed, accuracy verdict)
- Acceptance: Takes <3 minutes to complete
- Acceptance: Can be skipped with "too early to tell" option (reschedules to next period)
- Acceptance: Outcome data feeds directly into Group Intelligence Profile

**US-014: Decision Library**
As a team, we have a searchable library of all past decisions and their outcomes.
- Acceptance: Search by: domain, date, decision type, outcome verdict
- Acceptance: Semantic search ("find decisions similar to this one we're about to make")
- Acceptance: Pattern tagging: "this decision matches the pattern 'overconfident timeline estimate'"
- Acceptance: Export as PDF for board/investor reporting

---

### Phase 4: Group Intelligence

**US-015: Group Intelligence Profile**
As an organizational admin, I can see our team's collective decision-making patterns, blind spots, and calibration over time.
- Acceptance: Shows: overall accuracy score, domain breakdown, top 3 patterns, participation health metrics
- Acceptance: Updates weekly (after pattern detector runs)
- Acceptance: Requires at least 10 tracked decisions with outcomes before patterns are surfaced
- Acceptance: Recommendations for improving specific patterns

**US-016: Pattern Alerts**
As a facilitator about to run a meeting, I am alerted if this meeting type matches a known poor-performance pattern for our team.
- Acceptance: Pre-meeting: "Your team historically underestimates complexity in vendor selection decisions. Watch for this."
- Acceptance: During meeting: if pattern is triggered, specific intervention language is customized to address it
- Acceptance: Pattern confidence score shown (how many data points support this)

---

## 4. Feature Priority Matrix

| Feature | Phase | Priority | Effort | Value |
|---|---|---|---|---|
| Survey question generation | 1A | P0 | M | H |
| Anonymous survey submission | 1A | P0 | S | H |
| Tension map generation | 1A | P0 | M | H |
| Facilitator brief | 1A | P0 | S | H |
| Email notifications | 1A | P0 | S | M |
| Zoom integration | 2A | P0 | L | H |
| Real-time STT pipeline | 2A | P0 | L | H |
| HiPPO detection | 2B | P0 | M | H |
| Groupthink detection | 2B | P0 | M | H |
| Missing perspective | 2B | P1 | M | H |
| Decision capture | 3 | P0 | S | H |
| Post-mortem generation | 3 | P1 | S | M |
| Outcome check-ins | 3 | P1 | S | H |
| Group intelligence profile | 4 | P1 | L | H |
| Teams integration | 2A | P1 | L | M |
| Meet integration | 2A | P2 | L | M |
| Decision library search | 3 | P2 | M | M |
| Pattern alerts | 4 | P2 | M | H |
| SAML/SSO | 5 | P1 | M | H |
| SOC 2 controls | 5 | P1 | L | H |

---

## 5. Non-Functional Requirements

### Performance
- Survey submission: <500ms response time
- Tension map generation: <30 seconds
- STT latency: <400ms (Deepgram Nova-2 target)
- Intelligence evaluation: <3 seconds from trigger to alert
- Dashboard load: <1.5 seconds

### Reliability
- Uptime: 99.9% SLA (excluding live meeting windows: 99.99%)
- Meeting intelligence must not interrupt the meeting if Quorum has an outage — fail silent
- Survey responses persist immediately on submission — no data loss

### Security
- All data encrypted at rest (AES-256) and in transit (TLS 1.3)
- SOC 2 Type II compliant architecture
- No individual performance data ever stored or surfaced
- Speaker anonymization is cryptographically irreversible

### Privacy
- GDPR Article 25 (Privacy by Design) compliance
- Anonymization at collection point — not post-hoc
- Full org data deletion within 24 hours of request
- Processing addendum (DPA) available for all enterprise customers

---

## 6. Out of Scope (v1)

- In-person meeting support (microphone array hardware) — Phase 2+ roadmap
- Individual performance scoring — NEVER in product (core principle)
- Public leaderboards or inter-org comparison — privacy risk
- Consumer (individual) tier — B2B only at launch
- Automatic decision execution (Quorum advises, humans decide)
- Integration with project management tools (Asana, Jira) — Phase 2 roadmap

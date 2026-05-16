# QUORUM — Detailed User Stories
## All phases, all personas, all edge cases

---

## Personas

- **Facilitator (Alex)** — VP Product, runs most important meetings, wants better decisions from her team
- **Participant (Ben)** — Senior Engineer, attends meetings but often holds back opinions around senior leadership
- **Admin (Claire)** — Chief of Staff, manages the org's Quorum account, cares about ROI and adoption
- **Executive (David)** — CEO, rarely attends meetings but cares deeply about decision quality across the org

---

## EPIC 1: Onboarding

### US-OB-01: Organization setup
As Claire (admin), I can set up my organization in Quorum so that my team can start using it.

Given I've signed up for Quorum with my work email,
When I complete the onboarding flow,
Then I should have:
- Created my organization with name and domain
- Connected at least one meeting platform (Zoom, Teams, or Meet)
- Invited at least 3 teammates
- Configured the AI context string (what does our org do?)

Acceptance criteria:
- Onboarding flow is max 5 steps, completable in under 5 minutes
- Calendar integration (Google/Outlook) is offered but optional
- Org can start creating meetings immediately after step 3 (invite teammates)
- AI context string has a placeholder example relevant to common org types

---

### US-OB-02: First meeting creation (guided)
As Alex (facilitator), after onboarding I am guided through creating my first meeting so I understand the product.

Given I've completed organization setup,
When I see my empty dashboard,
Then there is a prominent "Create your first meeting" CTA with a 3-step guided flow:
1. Meeting basics (title, date, who's attending)
2. Agenda builder (paste or build)
3. Survey preview (see what questions AI will generate)

Acceptance criteria:
- Guided flow skippable for returning users
- Completion of first meeting creation triggers celebration and tips
- First survey questions are generated automatically so the user sees value immediately

---

## EPIC 2: Pre-Meeting Survey (Phase 1)

### US-SV-01: Connecting meeting to calendar
As Alex, I can connect an existing calendar invite to Quorum so I don't have to re-enter participant information.

Given I have Google Calendar or Outlook connected,
When I create a new meeting in Quorum,
Then I can search for an existing calendar event and import:
- Meeting title, time, and duration
- All invited attendees as Quorum participants

Acceptance criteria:
- Calendar search finds events within next 14 days
- Attendees outside the org receive a guest survey link (no Quorum account needed)
- External attendees can respond to survey anonymously but cannot see facilitator brief

---

### US-SV-02: Reviewing and editing AI questions
As Alex, I can review, edit, add, and remove the AI-generated survey questions before sending.

Given the AI has generated 5 questions for my roadmap decision meeting,
When I open the question editor,
Then I can:
- Edit any question text inline
- Change the question type (scale → open text)
- Delete any question
- Add a custom question
- Drag to reorder questions
- See the "rationale" for each question (why the AI generated this)
- Preview how the question will appear to participants

Acceptance criteria:
- Question editor saves automatically (no "save" button needed)
- Changes to questions invalidate any existing responses (with warning)
- Minimum 2 questions, maximum 8 questions enforced
- Must include at least one confidence-rating question (enforced, with explanation of why)

---

### US-SV-03: Participant receives survey email
As Ben (participant), I receive a clear, non-spammy email invitation to share my views before a meeting.

Given Alex has sent the survey,
When I receive the email,
Then it:
- Is from "Quorum on behalf of [Alex's name]" — clearly attributed
- Has a clear subject: "[Meeting Title] — share your views before the meeting"
- Explains in 2 sentences what Quorum is and why my input matters
- Has a prominent "Share my views" button leading directly to the survey (no login required)
- Explicitly states that my responses are anonymous to my colleagues

Acceptance criteria:
- Email renders correctly in Gmail, Outlook, Apple Mail
- Link contains a unique token (one per participant per meeting)
- Token expires at survey deadline
- Email unsubscribe removes participant from survey emails only (not from Quorum account)

---

### US-SV-04: Completing the survey
As Ben, I can complete the survey quickly and honestly because I trust it's genuinely anonymous.

Given I've clicked the survey link,
When I see the survey,
Then:
- I see a clear anonymity guarantee at the top (not buried in footer)
- Questions are presented one at a time (not all at once — reduces anchoring)
- Each question shows my progress (Question 2 of 5)
- Scale questions have labeled endpoints
- Open text fields have a 300-character limit (encourages concise responses)
- I can go back and change previous answers
- After submitting, I see a confirmation that my response was recorded
- I can re-open the link and update my responses until the deadline

Acceptance criteria:
- Survey completion time target: <4 minutes for 5 questions
- No analytics, no tracking pixels on the survey page — pure anonymity
- Works on mobile without needing to scroll horizontally
- Accessible: all inputs keyboard-navigable, screen-reader compatible

---

### US-SV-05: Low response rate handling
As Alex, when fewer than 50% of participants have responded as the deadline approaches, I am notified so I can nudge the team.

Given my survey has a 60% deadline and only 2 of 5 participants have responded,
When the deadline is 2 hours away,
Then:
- I receive a Slack message (if connected) or email: "3 participants haven't responded yet"
- I can send a one-click reminder from Quorum to non-responders (system sends — I don't see who hasn't responded)
- Quorum shows me the response rate as a live counter in my dashboard

If the deadline passes below 50%:
- I can still generate the tension map with a clear warning: "Based on limited responses — treat as directional"
- Or I can extend the deadline by 24 hours

Acceptance criteria:
- Reminder email is clearly from Quorum, not from me personally
- I cannot see which individuals have/haven't responded (only the count)
- Deadline extension sends notification to all participants

---

### US-SV-06: Viewing the tension map
As Alex, I receive the tension map after the survey closes and understand exactly what I need to do differently in the meeting.

Given 75% of participants have responded and the tension map has been generated,
When I open the meeting in Quorum,
Then I see:
- A one-sentence "headline insight" at the top (the most critical thing to know)
- "Areas of consensus" with agreement strength indicators
- "Areas of tension" with competing perspectives described neutrally
- "What nobody seems to be saying" — perspectives that appear absent
- "Questions to ask" — specific, ready-to-use questions for me to raise
- "Meeting strategy" — 3-4 sentences on how to approach the meeting given this data
- "Red flags to watch for" — early warning signs of derailment

Acceptance criteria:
- Tension map is never shown to participants (facilitator-only)
- No individual responses are ever visible — only synthesized insights
- Export to PDF for offline reading
- Map accessible up to 30 days after meeting ends

---

## EPIC 3: Live Meeting Intelligence (Phase 2)

### US-LV-01: Starting a live session
As Alex, I can start a Quorum live session with one click from my laptop before the meeting begins.

Given my meeting is scheduled in 5 minutes,
When I open Quorum in my browser and click "Start live session",
Then:
- Quorum's bot joins the Zoom/Teams/Meet call automatically
- All meeting participants see a notification: "Quorum is active in this meeting"
- My Quorum sidebar shows: speaking distribution, tension map summary, alert panel
- Live transcript begins appearing in real-time

Acceptance criteria:
- Bot join takes <10 seconds
- Participant notification is non-intrusive (one-time banner, auto-dismisses)
- If bot fails to join (API error), session continues without live AI — fail silent
- Session can be started from mobile (Quorum web app is mobile-responsive)

---

### US-LV-02: Receiving and acting on an alert
As Alex, when Quorum detects a groupthink pattern, I receive a discreet, useful alert that I can act on.

Given the meeting has been running 25 minutes and the team is converging on a decision,
When the tension map shows this topic had high disagreement but nobody has raised the concern,
Then I see in my sidebar:
- A yellow (medium urgency) alert card
- "The pre-meeting data showed some uncertainty about the timeline. This concern hasn't surfaced yet."
- A suggested question: "Before we lock this in — what's the most optimistic assumption baked into this plan?"
- Two buttons: "I'll address this" | "Dismiss"

If I click "I'll address this":
- Alert changes to green "Handled"
- Alert is marked as actioned in session record

Acceptance criteria:
- Alert appears only in my sidebar (not shown to all participants)
- Alert is not disruptive to the meeting — it's my private assistant
- Maximum 5 alerts per meeting (not alert-fatiguing)
- I can dismiss any alert and it won't reappear
- Alerts are not opinions — they reference specific data from the pre-survey

---

### US-LV-03: Requesting a suggested question
As Alex, I can ask Quorum for a good question to ask right now, given the current conversation.

Given the meeting is in a lull after a decision was made too quickly,
When I click "Suggest a question" in my sidebar and type: "We just agreed on the timeline — what might I ask to stress-test this?",
Then Quorum responds in <5 seconds with:
- A specific question tailored to the meeting context and tension map
- One sentence explaining why this question is particularly relevant right now

Acceptance criteria:
- Response time <5 seconds
- Question is specific (not generic)
- Explicitly references data from the tension map when relevant
- Option to copy question to clipboard for easy asking

---

### US-LV-04: Speaking distribution awareness
As Ben (participant), I can see the real-time speaking distribution in the meeting so I'm aware if I'm dominating or under-contributing.

Given I'm in a Quorum-enabled meeting,
When I open the Quorum participant view (web link shared in chat),
Then I see:
- An anonymous bar chart showing speaking distribution (Participant A, B, C — not names)
- My own segment is highlighted "You" without revealing others
- A simple indicator: "Balanced" | "Slightly uneven" | "One voice dominating"

Acceptance criteria:
- Participant view shows only distribution data — no tension map, no alerts
- No participant can see how much any OTHER specific person has spoken
- Updates every 60 seconds (not jarring real-time)
- Optional — participants don't have to view this

---

## EPIC 4: Decisions and Outcomes (Phase 3)

### US-DC-01: Marking a decision during a meeting
As Alex, I can mark key decisions while the meeting is still happening so they're captured immediately.

Given the team has just agreed on the Q3 feature priorities,
When I click "Mark decision" in my Quorum sidebar,
Then I see a quick form:
- Decision title (auto-filled from transcript context if available)
- Brief description (what was decided)
- Domain (pre-selected from meeting settings)
- Options that were considered (optional)

Acceptance criteria:
- Form completes in <60 seconds
- Can mark multiple decisions in one meeting
- Decisions appear immediately in the Decision Library
- After the meeting, Quorum suggests additional decisions it detected in the transcript

---

### US-DC-02: Completing a post-mortem
As Alex, I complete a structured post-mortem within 24 hours of the meeting.

Given Quorum has generated a post-mortem template using the meeting data,
When I open the post-mortem within 24 hours,
Then I see:
- What was decided (pre-filled from decision records)
- Key assumptions made (pre-filled from AI analysis)
- Dissenting views not fully addressed (pre-filled from tension map)
- Outcome criteria — what would "success" look like in 30/90/180 days?
- What warning signs appeared (groupthink alert at minute 25, one voice dominated for 15 min)

I can edit any section before publishing to the team.

Acceptance criteria:
- Post-mortem is viewable by all meeting participants after publishing
- "Dissenting views" section is clearly marked as anonymous
- Warning signs section is matter-of-fact, not judgmental
- Assumptions are formatted as checkboxes — become the outcome check-in questions

---

### US-DC-03: Receiving an outcome check-in
As Alex, 90 days after a decision I receive a prompt to record what actually happened.

Given a decision was made on July 15,
When October 15 arrives,
Then I receive:
- An email: "[Decision title] — 90-day check-in"
- The original assumptions listed as questions: "Did [assumption] turn out to be true?"
- A 5-question structured form
- Estimated time: 3 minutes

After I submit:
- Decision is updated with outcome verdict
- If incorrect/partially correct: a "lesson" is offered based on what failed
- Accuracy data feeds into Group Intelligence Profile

Acceptance criteria:
- Check-in can be delegated to another team member
- "Too early to tell" option reschedules to +30 days
- Can skip with reason (decision became irrelevant)
- After submitting, see: how this compares to team's overall accuracy in this domain

---

## EPIC 5: Group Intelligence

### US-GI-01: Viewing the Group Intelligence Profile
As David (CEO), I can see my organization's collective decision-making patterns so I know where we systematically fail.

Given 6 months of decisions with outcomes have been tracked,
When I open the Intelligence dashboard,
Then I see:
- Overall accuracy score with trend (up/down from last quarter)
- Domain breakdown: where are we most/least accurate?
- Top 3 patterns: specific, named patterns with evidence count
- Meeting health metrics: survey participation, speaking balance, alert frequency
- Recommended practices: 2-3 specific changes to make

Acceptance criteria:
- No individual is named or implied in any data shown
- Each pattern shows: name, description, # of supporting data points, confidence level
- Recommended practices link to documentation explaining the "why"
- Dashboard exportable as executive summary PDF

---

### US-GI-02: Pattern applied to upcoming meeting
As Alex, when I create a meeting that matches a known poor-performance pattern for our team, I'm warned before it's too late.

Given our team has the "Senior Leader Anchor" pattern (first person to speak in strategy meetings anchors the group),
When I create a new strategy meeting with the CEO attending,
Then Quorum shows a pre-meeting notice:
- "Your team has a pattern of anchoring to the first senior leader's view in strategy meetings (7 data points, high confidence)"
- "Recommended: Start with anonymous input before any live discussion"
- With one-click action: "Apply recommendation to this meeting"

Acceptance criteria:
- Pattern alert is shown on meeting creation, not buried
- One-click recommendation changes meeting setup automatically (e.g., extends survey deadline, adjusts recommended opening structure)
- Pattern is linked to specific past decisions for evidence (titles only, no detailed content)

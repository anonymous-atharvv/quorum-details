# QUORUM — Business Model & Go-To-Market Strategy
## Pricing, revenue model, competitive positioning, and launch plan

---

## 1. The Business Case in One Paragraph

A Fortune 500 company makes thousands of decisions per year in meetings. McKinsey estimates organizations lose $37B annually to ineffective meetings and bad decisions in the US alone. The existing market of meeting tools (Otter, Fireflies, Notion AI) addresses transcription and efficiency — a $2B market. The decision quality market — which is actually where the value is — is $0 in software currently. Quorum enters an uncontested market with a product that generates measurable, attributable ROI (a 10% improvement in decision quality for a 200-person company is worth millions of dollars annually).

---

## 2. Pricing Model

### Tier Structure

| Tier | Price | Seats | Key features |
|---|---|---|---|
| Starter | $49/seat/month | 5–15 | Pre-meeting surveys, tension maps, facilitator brief, decision library |
| Growth | $99/seat/month | 16–100 | + Live meeting intelligence, post-mortems, outcome tracking, group intelligence profile |
| Enterprise | $149/seat/month (custom) | 100+ | + SAML/SSO, dedicated instance, API access, custom integrations, SLA, CSM |

Annual pricing: 20% discount (billed annually = 2 months free).

### Unit Economics (Growth tier example)

- 25-seat team at $99/seat/month = $2,475/month MRR = $29,700 ARR
- COGS per team/month:
  - LLM costs: ~$15/month (surveys + tension maps + live agent + post-mortems)
  - Infrastructure: ~$8/month (proportional AWS share)
  - Deepgram STT: ~$12/month (10 meetings × 60 min × $0.02/min)
  - Total COGS: ~$35/month
- Gross margin: ($2,475 - $35) / $2,475 = 98.6%

### Revenue Model Milestones

| Stage | MRR | ARR | Teams | Milestone |
|---|---|---|---|---|
| Pre-launch | $0 | $0 | 0 | Product built, 10 design partners |
| Beta | $25K | $300K | 12 | Charged beta, proof of retention |
| Seed | $150K | $1.8M | 60 | Series A readiness |
| Series A | $600K | $7.2M | 200 | Enterprise motion starts |
| Series B | $2.5M | $30M | 700 | Category leader |

---

## 3. Target Customer Segments (Prioritized)

### Segment 1: High-Growth Tech Companies (Primary Launch Segment)
- Size: 50-500 employees, Series A-C
- Decision profile: High-velocity, high-stakes decisions (product roadmaps, hiring, strategy pivots)
- Pain: Decisions get revisited because people didn't actually commit; no institutional memory
- Budget: $10-50K/year (easy approval, no procurement)
- Entry: Bottom-up via VP Product or Head of Engineering
- Why first: Fastest sales cycle, highest tolerance for new tools, loudest champions

### Segment 2: Management Consulting Firms
- Size: 20-2,000 consultants
- Decision profile: Client-facing decisions with enormous financial stakes
- Pain: Every engagement involves group decisions that go wrong; client blames consultant
- Budget: $50-500K/year
- Entry: Top-down via firm-wide licensing
- Why valuable: High decision volume, professional credibility as reference customers

### Segment 3: Investment Firms (VC, PE, Family Offices)
- Size: 5-100 investment professionals
- Decision profile: Investment committee decisions, portfolio company board decisions
- Pain: Investment thesis drift, confirmation bias, missing red flags
- Budget: $25-200K/year
- Entry: Partner relationship
- Why valuable: Highest stakes decisions, quantifiable outcome tracking (IRR), willingness to pay

### Segment 4: Large Enterprise (Scale Segment)
- Size: 1,000+ employees
- Decision profile: Strategic planning, M&A, cross-functional initiatives
- Budget: $500K-$5M/year
- Entry: Chief of Staff, CSO, or digital transformation team
- Why later: Longer sales cycle, procurement complexity — but highest ACV

---

## 4. Go-To-Market Strategy

### Phase 1: Design Partner Program (Months 1-4)
10 design partner companies, free access in exchange for:
- Weekly feedback sessions
- Named reference customer status
- Case study rights

Target profile: VP Product or CTO at Series A-B company, 20-80 employees, strong network.
How to find: Founder networks, Y Combinator alumni, LinkedIn outbound.

Success metric: 8 of 10 design partners use Quorum for ≥3 meetings/week after month 2.

### Phase 2: Charged Beta (Months 4-8)
Convert design partners to paid. Open to 50 additional companies via waitlist.
Pricing: 50% discount in exchange for quarterly feedback commitment.

Key activities:
- Case study with first 3 design partners (quantified: "X% improvement in decision follow-through")
- 1-2 thought leadership pieces ("The $37B Meeting Problem") published on founders' LinkedIn
- Product Hunt launch (timing: after 3 solid case studies)

Success metric: $25K MRR, NPS >55.

### Phase 3: PLG + Sales Motion (Months 8-18)
**Product-Led Growth (bottom-up):**
- Free trial: 3 meetings free (no credit card)
- Viral loop: survey participants get Quorum-branded brief → "Powered by Quorum" → click to sign up
- In-product upgrade: "Your team has tracked 10 decisions — upgrade to see patterns"

**Sales-led (top-down for >50 seat deals):**
- 1 AE + 1 SDR at $500K ARR
- ICP outbound: VP Product, CPO at Series B-C
- Sequence: email → LinkedIn → warm intro (founder-led at first)
- Demo: live tension map demo on prospect's actual next meeting (bespoke, high-conversion)
- Sales cycle: 2-6 weeks for SMB, 1-3 months for mid-market

### Phase 4: Enterprise Motion (Month 18+)
- Dedicated enterprise AE team
- Procurement-ready: SOC 2 Type II, DPA, custom MSA template, SAML/SSO
- Champion: Chief of Staff or Strategy team
- Economic buyer: CFO (decision quality ROI is quantifiable), COO
- ACV target: $200K-$2M

---

## 5. Key Sales Metrics

| Metric | Target (Year 1) | Target (Year 2) |
|---|---|---|
| ACV (Starter) | $3,000 | $4,000 |
| ACV (Growth) | $15,000 | $18,000 |
| ACV (Enterprise) | $150,000 | $300,000 |
| Sales cycle (Starter) | 7 days | 5 days |
| Sales cycle (Growth) | 21 days | 14 days |
| Sales cycle (Enterprise) | 90 days | 60 days |
| CAC (Starter) | $500 | $400 |
| CAC (Growth) | $3,000 | $2,500 |
| Payback period | 3.5 months | 3 months |
| Gross churn (annual) | <15% | <10% |
| Net Revenue Retention | >115% | >125% |

---

## 6. Competitive Positioning

### Competitive Landscape

| Competitor | Category | Why they lose to Quorum |
|---|---|---|
| Otter.ai | Meeting transcription | Transcribes, does not improve decisions |
| Fireflies.ai | Meeting intelligence | Summaries + action items only |
| Notion AI | Knowledge management | Post-meeting documentation |
| Slido | Live meeting engagement | Polling, not intelligence |
| Lattice | Performance management | Individual focus, HR tool — Quorum is not this |
| Dovetail | Research synthesis | Research insights, not real-time decisions |
| None | Decision intelligence | **Uncontested category** |

### Positioning Statement
"Quorum is the only platform that makes the group decision itself better — not just faster to document afterward."

### Competitive Moat (Why this is defensible)

1. Decision outcome database: After 2 years of data, Quorum has the world's largest dataset of organizational decisions and their outcomes. This enables predictive intelligence no competitor can replicate without starting over.

2. Group Intelligence Profile: After 18+ months, an organization's GIP becomes institutionally irreplaceable. Switching to a competitor means losing the team's entire decision history, pattern library, and calibration scores.

3. Network effects within organizations: More decisions → better patterns → better pre-meeting intelligence → higher value → more decisions tracked. Virtuous cycle within each organization.

4. Privacy-first architecture: Quorum's anonymization model is designed into the architecture, not bolted on. Competitors entering the space will have to rebuild from scratch to match this.

---

## 7. Key Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Meeting platform API breaks | Medium | High | Abstract integration layer; fail-silent design; multiple platform support |
| Anthropic API cost increase | Low | Medium | Prompt optimization; fallback to smaller model for simpler tasks |
| "Surveillance" perception | Medium | High | Radical transparency in UI; anonymization guarantees; no individual performance use case ever |
| Slow adoption (meetings are habitual) | High | Medium | Phase 1 (surveys only) has no meeting habit change required; prove value before live intelligence |
| Enterprise sales cycle too long | Medium | Medium | PLG motion covers SMB while enterprise deals close |
| Competitor (e.g. Zoom, Microsoft) builds this | Medium | High | Build moat (GIP + outcome database) as fast as possible; 18+ months head start |

---

## 8. Fundraising Strategy

### Pre-Seed ($1.5M)
Use: 2 engineers + 1 designer + founder for 18 months.
Build: Phase 1 (surveys + tension maps) fully launched, Phase 2 (live meeting) in beta.
Milestone: $25K MRR, 3 case studies, NPS >55.

Investor profile: Pre-seed funds, angels with enterprise SaaS or future-of-work thesis.

### Seed ($5M)
Use: Full team (5 engineers, 2 sales, 1 CS, 1 marketing).
Build: Phase 2 complete, Phase 3 (outcomes) shipped, Group Intelligence Profile live.
Milestone: $150K MRR, enterprise motion started.

Investor profile: Seed funds with enterprise SaaS portfolio (Craft, First Round, Pear, Boldstart).

### Series A ($18M)
Use: Scale sales team, enterprise motion, international expansion.
Milestone: $600K MRR, NRR >115%, 3 enterprise logos.

Investor profile: Series A firms with Future of Work / Enterprise AI thesis.

---

## 9. Key Metrics Dashboard (Investor-facing)

Weekly:
- New MRR
- Churned MRR
- Net new MRR
- Meetings run on Quorum
- Survey response rate (platform avg)
- Alerts delivered and actioned rate

Monthly:
- MRR by tier
- NRR
- CAC by channel
- Payback period
- Active orgs (ran ≥1 meeting in last 30 days)
- Decisions tracked with outcomes

Quarterly:
- GIP accuracy scores (are organizations actually making better decisions?)
- NPS by tier
- Expansion revenue (seat adds)
- Enterprise pipeline

The north star metric: **Decision outcome accuracy improvement over time.**
If organizations using Quorum for 12+ months are making measurably better decisions than in their first month, the product is working. Everything else follows.

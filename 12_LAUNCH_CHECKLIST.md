# QUORUM — Launch Checklist
## Pre-launch gates, launch day plan, first 30 days playbook

---

## How to use this document

Work through Section 1 (Pre-Launch Gates) top-to-bottom. Every checkbox must be green before accepting the first paying customer. No exceptions. The gates exist because launching with a broken item costs 10x more to fix than delaying by a week.

Section 2 is the launch day timeline. Section 3 is the first 30 days operating playbook.

---

## Section 1: Pre-Launch Gates

### Gate 1: Product — Phase 1 Complete
*Minimum viable product: surveys + tension maps. Live meeting intelligence (Phase 2) is NOT required for launch.*

```
CORE FUNCTIONALITY
[ ] Meeting creation flow works end-to-end
[ ] Survey question generation produces high-quality questions (eval score >= 0.85)
[ ] Anonymous survey submission works without a Quorum account
[ ] Tension map generates correctly with >50% response rate
[ ] Tension map correctly refuses to generate at <30% response rate
[ ] Facilitator brief visible only to facilitator, not participants
[ ] Decision creation and tagging works
[ ] Post-mortem generation works
[ ] Outcome check-in scheduling and delivery works
[ ] Decision library search works (title + semantic)

EDGE CASES
[ ] Meeting with 0 survey responses — handled gracefully
[ ] Meeting with 2 participants (very small group) — tension map extra cautious
[ ] Survey submitted after deadline — rejected with friendly message
[ ] Facilitator tries to see individual responses — 404 (endpoint does not exist)
[ ] Org admin tries to query another org's data — 403 (RLS enforced)
[ ] Survey token reuse after expiry — 410 Gone with clear message

EMAIL FLOWS
[ ] Survey invitation email sends correctly (test with real email)
[ ] Survey reminder at 50% of deadline
[ ] Survey reminder at 90% of deadline
[ ] Facilitator brief email sends when tension map is ready
[ ] Outcome check-in email sends at 30/90/180 days
[ ] All emails render correctly in Gmail, Outlook, Apple Mail
[ ] Unsubscribe link works (CAN-SPAM compliance)
```

### Gate 2: Engineering Quality
```
CODE QUALITY
[ ] All CI checks passing on main branch
[ ] Test coverage >= 80% on app/ directory
[ ] No high or critical Bandit security findings unaddressed
[ ] No known CVEs in dependencies (pip-audit clean)
[ ] TypeScript strict mode, no type errors in frontend
[ ] Bundle size: largest chunk < 500KB

PERFORMANCE (on staging with production-like data)
[ ] Survey submission: p95 < 300ms
[ ] Tension map generation: completes in < 45 seconds
[ ] Dashboard load: p95 < 1.5 seconds
[ ] API under 100 concurrent users: error rate < 0.1%

RELIABILITY
[ ] Deployed successfully to staging 3+ times without incident
[ ] Rollback tested: confirmed rollback completes in < 5 minutes
[ ] Database migration rollback tested
[ ] What happens when Anthropic API is down? App degrades gracefully (cached state shown)
[ ] What happens when Deepgram is down? Meeting proceeds, intelligence paused (Phase 2)
[ ] What happens when Redis is down? App serves degraded (no real-time, cache miss)
```

### Gate 3: Security
```
[ ] SSL Labs rating: A+ on api.quorum.ai and app.quorum.ai
[ ] No secrets in GitHub repo (TruffleHog scan clean)
[ ] All secrets in AWS Secrets Manager (not .env files)
[ ] PostgreSQL RLS tested: confirmed cross-org data access impossible
[ ] Anonymization adversarial tests passing (tests/unit/test_anonymization.py)
[ ] Auth0 production tenant configured (not dev tenant)
[ ] JWT expiry set correctly (1 hour access, 7 day refresh)
[ ] Rate limiting active on all endpoints
[ ] CORS configured to exact allowed origins only
[ ] No stack traces in API error responses
[ ] No PII in application logs (verified manually)
[ ] S3 bucket: no public access, encryption enabled
[ ] RDS: no public access, Multi-AZ enabled
[ ] Security checklist from 09_SECURITY_COMPLIANCE.md: 100% complete
```

### Gate 4: Legal & Compliance
```
DOCUMENTS (must be published on quorum.ai before first customer)
[ ] Privacy Policy — reviewed by lawyer, published
[ ] Terms of Service — reviewed by lawyer, published
[ ] Data Processing Agreement (DPA) template — reviewed by lawyer, available on request
[ ] Sub-processor list published and current
[ ] Cookie policy (if using cookies beyond strictly necessary)

BUSINESS
[ ] Company incorporated (Delaware C-Corp recommended for US startups)
[ ] Business bank account open
[ ] Stripe account verified and live keys configured
[ ] Accountant/bookkeeper set up
[ ] Business insurance: general liability + cyber liability

GDPR
[ ] GDPR export endpoint tested end-to-end
[ ] GDPR deletion endpoint tested end-to-end (purge_org_data function verified)
[ ] privacy@quorum.ai email monitored
[ ] security@quorum.ai email monitored
[ ] If serving EU customers: Standard Contractual Clauses (SCCs) in DPA
```

### Gate 5: Operations
```
MONITORING
[ ] Datadog dashboards configured (API health, business metrics)
[ ] PagerDuty on-call configured for P0 alerts
[ ] Sentry error tracking active and receiving events
[ ] Uptime monitor active (Datadog or Pingdom) — alerts if down > 2 minutes
[ ] Database backup verified: point-in-time recovery tested (RB-09)

RUNBOOKS
[ ] All 10 runbooks in 11_DEVOPS_RUNBOOKS.md reviewed and tested
[ ] Emergency contacts list current (CTO, founding engineer, lawyer)
[ ] Incident response Slack channel (#incidents) created
[ ] RDS Multi-AZ enabled
[ ] Auto-scaling configured for ECS services

SUPPORT
[ ] support@quorum.ai email monitored (response SLA: 4 hours for paid customers)
[ ] Intercom or equivalent live chat configured (optional but strongly recommended)
[ ] Help documentation: at minimum, "getting started" guide published
[ ] First 10 customers have direct Slack channel (white-glove for early adopters)
```

### Gate 6: Business Readiness
```
CUSTOMERS
[ ] At least 3 design partners have used the product for 2+ weeks
[ ] At least 1 design partner willing to be named reference customer
[ ] NPS from design partners: >= 50
[ ] At least 1 customer willing to do a case study (even if not published at launch)

PRICING
[ ] Stripe products and prices created matching pricing doc
[ ] Stripe checkout flow tested (upgrade, downgrade, cancel)
[ ] Seat-based billing tested (invite user → charge increases)
[ ] Stripe webhook handler tested (subscription.created, subscription.deleted)

CONTENT
[ ] Product website (quorum.ai) live with clear value proposition
[ ] "Book a demo" flow works and leads to actual calendar booking
[ ] 3 screenshots or a product video on homepage
[ ] LinkedIn company page created
[ ] Founder LinkedIn updated to mention Quorum
```

**ALL 6 GATES COMPLETE → APPROVED FOR FIRST PAYING CUSTOMER**

---

## Section 2: Launch Day Timeline

### T-7 days: Soft launch prep
```
[ ] Send "coming soon" to waitlist (if any)
[ ] Prepare design partner case study (even 3 sentences is enough)
[ ] Draft founder LinkedIn post announcing launch
[ ] Confirm 3 design partners are ready to be references
[ ] Final security check: run full security checklist one more time
[ ] Dry run: simulate new customer signup flow top-to-bottom
```

### T-1 day: Pre-launch
```
[ ] All CI/CD green on main
[ ] Deploy to staging, verify clean
[ ] Datadog dashboards loaded and showing baseline
[ ] PagerDuty test alert sent and received
[ ] Customer support team briefed (even if it's just you)
[ ] Intercom configured with welcome message
[ ] DNS TTL reduced to 60 seconds (allows faster failover if needed)
[ ] AWS Support plan upgraded to Business (if not already)
```

### Launch Day: Hour by Hour
```
09:00  Final health check: all services green
09:15  Publish founder LinkedIn post announcing launch
09:30  Submit to Product Hunt (if doing a PH launch):
       - Title: "Quorum — AI that makes your group decisions smarter"
       - Tagline: "Anonymous pre-meeting surveys + live intelligence + outcome tracking"
       - Hunter: founder
       - Makers: all co-founders

10:00  Email waitlist (if any)
10:30  Post in relevant Slack communities (YC alumni, specific industry groups)
11:00  Monitor: Datadog + Sentry + support inbox
12:00  First check-in with team: any issues? user questions?

Throughout day:
       [ ] Respond to every inbound message within 2 hours
       [ ] Monitor Datadog for error spikes
       [ ] Log every conversation with a potential customer
       [ ] Screenshot and save first signup (you'll want this for the Series A deck)

EOD:
       [ ] Count: signups, new orgs, support tickets, conversion rate
       [ ] Document: top 3 questions people asked
       [ ] Note: top 3 friction points you observed
       [ ] Write: 1 paragraph on what surprised you today
```

---

## Section 3: First 30 Days Playbook

### Week 1: White-Glove Onboarding
Every new customer gets direct founder attention.

```
Day 1 of each new customer:
  [ ] Personally email: "Welcome to Quorum — I'm {name}, co-founder. 
      I'd love to join your first meeting and help you get started."
  [ ] Offer to join their first meeting as silent observer
  [ ] Set a check-in call for Day 7

Day 7 check-in (30 minutes):
  Questions to ask:
  1. "What happened in your first meeting with Quorum? Tell me everything."
  2. "What did the tension map get right? What did it miss?"
  3. "What would have made it 10% better?"
  4. "Would you recommend Quorum to a colleague? Why / why not?"
  
  Record answers verbatim. This is your product roadmap.
```

### Week 2: Metric Baselines
```
By Day 14, establish baselines for:
[ ] Survey response rate (target: >60%)
[ ] Time from meeting created to survey sent (target: <2 hours)
[ ] Time from survey closed to tension map ready (target: <5 minutes)
[ ] Facilitator brief open rate (target: >80%)
[ ] Decisions tracked per meeting (target: >1)
[ ] Daily active orgs (ran at least 1 meeting with Quorum)

If any metric below target: debug and fix before Week 3.
```

### Week 3: Expansion and Retention
```
Early retention signals to watch:
[ ] Did org create a SECOND meeting? (if not by Day 14: reach out)
[ ] Is survey response rate stable or declining? (declining = product isn't sticking)
[ ] Are participants actually opening survey emails? (check SendGrid open rates)
[ ] Did anyone invite new users to their org? (virality signal)

Expansion actions:
[ ] For every org that ran 3+ meetings: ask for a testimonial
[ ] For every org with >5 users: ask if other teams would benefit
[ ] Begin case study interviews with happiest customers
```

### Week 4: Growth Initialization
```
[ ] Publish first case study (even a short LinkedIn post quote is fine)
[ ] Post first "Quorum insight" content (e.g., "We analyzed 100 meeting decisions — 
    here's what we learned about groupthink")
[ ] Apply to 2-3 relevant accelerator programs or startup communities
[ ] Begin outbound: 10 personalized emails/day to ICP targets (VP Product at Series B+)
[ ] Set up first referral mechanism: "Refer a company, get 1 month free"
```

### Month 1 Success Criteria
```
RETENTION
[ ] >70% of orgs that created a meeting ran at least 2 meetings
[ ] No involuntary churn in first month

PRODUCT
[ ] NPS from first customers: >= 55
[ ] Average survey response rate: >= 60%
[ ] At least 10 decisions tracked with outcome scheduled

BUSINESS
[ ] MRR: $X (set your own target based on design partners converted)
[ ] At least 2 reference customers willing to take sales calls
[ ] At least 1 case study publishable (even anonymized)

LEARNING
[ ] Top 3 reasons customers love Quorum: documented
[ ] Top 3 friction points: documented and on roadmap
[ ] One surprising insight about how customers use the product: documented
[ ] Pricing: validated (did anyone object to price? did anyone say it was too cheap?)
```

---

## Section 4: The 10 Questions to Answer in Month 1

These are the questions that determine whether Quorum becomes a company or a project. Answer them with data, not intuition.

1. **Do customers come back?** After the first meeting, do they run a second? Third? This is the only retention metric that matters in month 1.

2. **What is the activation moment?** At what point does a customer "get it"? (Hypothesis: it's when they read the tension map and see something they didn't know.)

3. **Who is the real champion?** Is it always VP Product? Or are there surprising champions (CTO, Chief of Staff, CEO)?

4. **What is the real objection?** Is it price? Privacy concerns? "We already have Otter"? "Our meetings aren't the problem"? Know the objection cold.

5. **What do they tell their colleagues?** Ask: "How would you describe Quorum to someone who hasn't heard of it?" Their words become your homepage copy.

6. **What breaks first?** Which feature gets the first bug report? Which integration fails first?

7. **Is the AI good enough?** Read every tension map generated in month 1. Are they actually insightful? Or are they generic? This is an honest self-assessment.

8. **What's the viral coefficient?** For every new org, how many other orgs do they tell? Even 0.2 is meaningful at this stage.

9. **What's the real ICP?** Your hypothesis was VP Product at Series B tech companies. Is the data supporting that? Or is it a different buyer?

10. **Would you pay for this?** If you were a customer and not the founder — would you pay $99/seat/month for what you've built? Why or why not?

---

*This checklist is a living document. Update it after every launch and every major incident.*

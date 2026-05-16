# QUORUM — Security & Compliance
## SOC 2 Type II controls, GDPR framework, threat model, and incident response

---

## 1. Security Principles

1. **Privacy by design** — anonymization at collection, not post-hoc
2. **Least privilege everywhere** — every component has only the permissions it needs
3. **Defense in depth** — no single control is relied on; multiple layers
4. **Zero trust network** — every service authenticates every call; no implicit trust
5. **Audit everything** — every data access leaves an immutable trail

---

## 2. SOC 2 Type II Controls Map

SOC 2 Type II is the enterprise sales requirement. Build for it from day one.
Target: audit-ready by Month 12, certified by Month 18.

### CC1: Control Environment

| Control | Implementation | Evidence |
|---|---|---|
| CC1.1 Board oversight of security | Security reviewed in monthly board update | Board meeting minutes |
| CC1.2 Management commitment | Security policy signed by CEO | Policy document + signature |
| CC1.3 Org structure | Security owner designated (CTO at seed) | Org chart |
| CC1.4 HR policies | Background checks for engineers with prod access | HR records |
| CC1.5 Accountability | Access reviewed quarterly | Quarterly access review logs |

### CC2: Communication & Information

| Control | Implementation | Evidence |
|---|---|---|
| CC2.1 Internal communication | Security policy in company wiki | Confluence/Notion page |
| CC2.2 External communication | Privacy policy, Terms of Service, DPA | Legal docs on website |
| CC2.3 Incident communication | Customer notification within 72 hrs of breach | Incident response procedure |

### CC3: Risk Assessment

| Control | Implementation | Evidence |
|---|---|---|
| CC3.1 Risk identification | Annual threat modeling exercise | Threat model document |
| CC3.2 Risk analysis | Risk register with likelihood × impact | Risk register |
| CC3.3 Risk mitigation | Controls mapped to each risk | This document |

### CC6: Logical & Physical Access

| Control | Implementation | Evidence |
|---|---|---|
| CC6.1 Access control | Auth0 + RLS in PostgreSQL | Auth0 config, DB RLS policies |
| CC6.2 New access | Access requires ticket + manager approval | Ticket system records |
| CC6.3 Access removal | Offboarding checklist, Auth0 user deactivated within 24hrs | Offboarding records |
| CC6.6 Network controls | VPC, security groups, no public DB access | AWS config |
| CC6.7 Transmission encryption | TLS 1.3 enforced on all endpoints | SSL Labs A+ rating |
| CC6.8 Vulnerability management | Dependabot + quarterly pen test | Scan reports |

### CC7: System Operations

| Control | Implementation | Evidence |
|---|---|---|
| CC7.1 Vulnerability detection | Dependabot + Bandit + pip-audit in CI | CI run logs |
| CC7.2 Anomaly detection | Datadog alerts on error rate spikes | Datadog alert config |
| CC7.3 Incident response | Documented runbook + on-call rotation | This document, PagerDuty |
| CC7.4 Incident resolution | Post-incident review within 48 hours | Post-mortem documents |
| CC7.5 Vulnerability remediation | Critical CVEs patched within 48 hrs | Patch records |

### CC8: Change Management

| Control | Implementation | Evidence |
|---|---|---|
| CC8.1 Change authorization | All changes via PR, required reviewer | GitHub PR history |
| CC8.2 Change testing | CI must pass before merge | GitHub branch protection |
| CC8.3 Change deployment | Blue/green deploy with smoke test | Deploy workflow logs |

### CC9: Risk Mitigation

| Control | Implementation | Evidence |
|---|---|---|
| CC9.1 Vendor management | Security review for all vendors with data access | Vendor list + reviews |
| CC9.2 Business continuity | RDS Multi-AZ, cross-region backup | AWS config |

---

## 3. GDPR Compliance Framework

Quorum processes data for organizations in EU and serves EU customers.
GDPR compliance is both a legal requirement and a sales asset.

### 3.1 Lawful Basis for Processing

| Data type | Lawful basis | Notes |
|---|---|---|
| User account data (email, name) | Contract performance | Required to provide service |
| Survey responses (anonymous) | Legitimate interest | Anonymized at collection — arguably not personal data under GDPR |
| Meeting transcripts (anonymous) | Legitimate interest | Same — anonymized at source |
| Decision records | Contract performance | Org's business data |
| Billing data | Legal obligation | Required for tax compliance |
| Usage analytics | Legitimate interest | Minimized, aggregate only |

### 3.2 Data Subject Rights Implementation

```python
# Each right implemented as an API endpoint and tested
# GDPR Article 15: Right of Access
GET /gdpr/export
# Returns: all data associated with the requesting user's email
# Response time SLA: within 72 hours
# Format: JSON file, downloadable link via email

# GDPR Article 17: Right to Erasure
DELETE /gdpr/erase
# Triggers: purge_org_data() for org admin
# Or: anonymize user from org records for individual user
# Completion SLA: within 24 hours
# Evidence: deletion confirmation email + audit log entry

# GDPR Article 20: Data Portability
GET /gdpr/export?format=json
# Returns: all decisions, outcomes, tension maps in portable JSON
# Note: anonymous data (survey responses, transcripts) excluded — 
# not linked to individual identities

# GDPR Article 77: Right to Lodge Complaint
# Documented in Privacy Policy: contact DPA at authority in user's country
```

### 3.3 Data Processing Agreement (DPA)

Quorum provides a DPA to all enterprise customers. Standard template covers:
- Controller / Processor relationship (org is controller, Quorum is processor)
- Processing purposes and legal basis
- Data retention periods
- Sub-processor list (AWS, Anthropic, Deepgram, Auth0, Stripe, SendGrid)
- Security measures (this document)
- Data transfer mechanisms (SCCs for EU → US transfers)
- Breach notification (72 hours)
- Deletion/return on contract termination

**Sub-processor list** (must be kept current and communicated to customers):

| Sub-processor | Purpose | Location | Transfer mechanism |
|---|---|---|---|
| AWS (Amazon) | Infrastructure hosting | US (eu-west-1 for EU) | SCCs |
| Anthropic | LLM inference | US | SCCs |
| Deepgram | Speech-to-text | US | SCCs |
| Auth0 (Okta) | Identity management | US/EU | SCCs |
| Stripe | Payment processing | US | SCCs |
| SendGrid (Twilio) | Email delivery | US | SCCs |
| Pinecone | Vector database | US | SCCs |
| Datadog | Monitoring | US | SCCs |
| Sentry | Error tracking | US | SCCs |

### 3.4 Data Retention Periods

| Data type | Retention period | Deletion trigger |
|---|---|---|
| User account | Duration of org subscription + 30 days | Org cancellation |
| Survey responses (anonymous) | 3 years | Org deletion or request |
| Meeting transcripts (anonymous) | 90 days | Rolling deletion job |
| Decision records | Duration of subscription + 1 year | Org cancellation |
| Decision outcomes | Duration of subscription + 1 year | Org cancellation |
| Audit logs | 7 years | Immutable (legal requirement) |
| Audio recordings (if enabled) | 30 days | Rolling deletion job |
| Billing records | 7 years | Legal obligation |

---

## 4. Threat Model

### 4.1 Assets to Protect

1. Survey response data (highest sensitivity — could embarrass individuals if de-anonymized)
2. API keys and secrets (could lead to account takeover)
3. Decision library (confidential strategic information)
4. Meeting transcripts (sensitive business discussions)
5. Customer PII (email, names)

### 4.2 Threat Actors

| Actor | Motivation | Capability | Priority |
|---|---|---|---|
| External attacker | Data theft, ransomware | Medium | High |
| Malicious insider (employee) | Data exfiltration | High | Medium |
| Compromised vendor | Supply chain attack | Medium | Medium |
| Curious customer employee | Access others' anonymous data | Low | High (privacy core promise) |
| Competitor | IP theft | Low | Low |

### 4.3 Threat Scenarios & Controls

**T1: Attempt to de-anonymize survey responses**
- Attack: Admin queries DB trying to correlate respondent_hash to user_id
- Control: HMAC uses a secret not in the DB (AWS Secrets Manager only)
- Control: No user_id → hash lookup table exists
- Control: RLS prevents cross-org queries
- Control: Audit log records all survey_responses table access
- Residual risk: LOW

**T2: LLM prompt injection via survey response**
- Attack: Participant submits survey response containing "Ignore previous instructions..."
- Control: All survey responses are passed to LLM as data, not as system prompt
- Control: Instructor Pydantic validation rejects responses that don't match schema
- Control: Responses stored and displayed as user content, clearly labeled
- Residual risk: LOW

**T3: API credential theft**
- Attack: ANTHROPIC_API_KEY leaked via logs, error messages, or code repo
- Control: Secrets in AWS Secrets Manager (never in code or .env files in production)
- Control: Log sanitization strips known secret patterns
- Control: TruffleHog secret scanning in CI
- Control: Separate API keys for dev/staging/prod with minimal scopes
- Residual risk: MEDIUM (supply chain compromise possible)

**T4: SQL injection**
- Attack: Malicious input in meeting title, description, or survey question
- Control: SQLAlchemy ORM with parameterized queries always (no raw SQL)
- Control: Pydantic input validation on all API inputs
- Control: `pg_trgm` search uses parameterized queries
- Residual risk: LOW

**T5: Zoom meeting infiltration**
- Attack: Attacker joins a Zoom meeting to get Quorum's live transcript
- Control: Quorum only joins meetings it was explicitly configured for
- Control: Meeting join URL validated against org's registered meetings
- Control: Quorum participant has distinct display name ("Quorum Intelligence")
- Residual risk: LOW (same as Zoom's own security model)

**T6: Broken access control (cross-org data)**
- Attack: API request uses JWT from org A to access org B's data
- Control: JWT claims include org_id; validated on every request
- Control: PostgreSQL RLS enforced at DB level (app can't bypass)
- Control: All queries include org_id filter (defense in depth)
- Residual risk: LOW

---

## 5. Security Testing Schedule

| Activity | Frequency | Owner | Output |
|---|---|---|---|
| Dependency vulnerability scan (pip-audit) | Every CI run | Engineering | Automated report |
| SAST scan (Bandit) | Every CI run | Engineering | Automated report |
| Secret scanning (TruffleHog) | Every CI run | Engineering | Automated report |
| Internal penetration test | Quarterly | Security champion | Findings report |
| External penetration test | Annually | Third-party firm | Pentest report |
| SOC 2 Type II audit | Annually | External auditor | Audit report |
| Threat model review | Annually | CTO + team | Updated threat model |
| Access review (all systems) | Quarterly | Engineering manager | Access review record |

---

## 6. Incident Response Procedure

### Severity Levels

| Level | Definition | Response time | Examples |
|---|---|---|---|
| P0 | Data breach, service down, active attack | 15 minutes | DB compromised, prod down |
| P1 | Significant data exposure, major feature broken | 1 hour | API returning wrong org data |
| P2 | Performance degradation, non-critical bug | 4 hours | Slow queries, UI broken |
| P3 | Minor bug, cosmetic issue | Next sprint | Wrong label, typo |

### P0 Response Playbook

```
T+0:    PagerDuty alert fires → on-call engineer acknowledges
T+5:    Declare incident in #incidents Slack channel
T+10:   Assess scope: what data? how many orgs? is attack ongoing?
T+15:   If ongoing attack: block source IP at ALB level
T+20:   Notify CEO and legal counsel
T+30:   If personal data involved: assess GDPR 72-hour notification requirement
T+60:   Preliminary customer notification if data exposure confirmed
T+72:   GDPR notification to DPA if required (EU personal data)
T+2d:   Full post-incident review document
T+2d:   Customer notification with full details
T+7d:   Remediation implemented and verified
T+14d:  Post-mortem published internally
```

### Customer Notification Template

```
Subject: Security Incident Notice — Quorum [date]

Dear [Organization Name] team,

We are writing to notify you of a security incident affecting Quorum.

What happened: [factual description, no speculation]
When it happened: [date/time]
What data was affected: [specific data types]
What we've done: [remediation actions taken]
What you should do: [any required customer action, or "no action required"]

We take the security of your data extremely seriously. We are committed to 
transparency and will provide updates as our investigation continues.

If you have any questions, please contact security@quorum.ai.

[CEO name]
CEO, Quorum
```

---

## 7. Security Checklist (Pre-Launch Gate)

Run this checklist before accepting the first paying customer.

### Authentication & Authorization
- [ ] Auth0 production tenant configured
- [ ] JWT validation on every protected endpoint
- [ ] PostgreSQL RLS policies enabled and tested
- [ ] API key hashing uses bcrypt (not MD5 or SHA1)
- [ ] Password reset flow tested end-to-end
- [ ] Session timeout configured (1 hour access token, 7 day refresh)

### Data Protection
- [ ] TLS 1.3 enforced (no TLS 1.0/1.1/1.2) — verify with SSL Labs
- [ ] All secrets in AWS Secrets Manager (none in env files or code)
- [ ] Database encryption at rest enabled (RDS default)
- [ ] S3 bucket policy: no public access, encryption enabled
- [ ] Anonymization HMAC verified: confirm hash cannot be reversed
- [ ] Audit log table tested: records all data access events

### Application Security
- [ ] CORS configured to exact allowed origins (not *)
- [ ] Rate limiting enabled and tested
- [ ] SQL injection tested: confirm SQLAlchemy ORM used everywhere
- [ ] XSS: Content-Security-Policy header configured
- [ ] CSRF: SameSite cookie attribute set
- [ ] Input validation: all API inputs validated by Pydantic
- [ ] Error messages: no stack traces or secrets in error responses
- [ ] Logging: no PII or secrets in log output

### Infrastructure
- [ ] VPC: databases in private subnet (no public IP)
- [ ] Security groups: least privilege (only required ports open)
- [ ] S3 bucket ACL: private (no public access)
- [ ] CloudTrail enabled for AWS API audit
- [ ] Backup: RDS automated backup enabled (7-day retention)
- [ ] Multi-AZ: RDS Multi-AZ enabled

### Compliance
- [ ] Privacy Policy published and linked from product
- [ ] Terms of Service published
- [ ] DPA template drafted and legal-reviewed
- [ ] Sub-processor list current and accurate
- [ ] GDPR export endpoint tested
- [ ] GDPR deletion endpoint tested and verified
- [ ] Cookie banner (if applicable) implemented

### Operational
- [ ] PagerDuty on-call rotation configured
- [ ] Runbooks written for top 5 incident types
- [ ] Slack #incidents channel created
- [ ] Incident response contacts list current
- [ ] Security email (security@quorum.ai) monitored

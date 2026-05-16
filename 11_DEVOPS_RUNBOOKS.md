# QUORUM — DevOps Runbooks
## Deployment, incident response, rollback, scaling, and data operations

---

## 1. Runbook Index

| Runbook | When to use |
|---|---|
| RB-01: Deploy to staging | Every merge to `main` |
| RB-02: Deploy to production | Manual release decision |
| RB-03: Rollback production | Deploy caused issues |
| RB-04: Database migration | Schema change required |
| RB-05: Incident response (P0) | Production down or data breach |
| RB-06: Scale up under load | Unusual traffic spike |
| RB-07: GDPR data deletion | Customer requests data purge |
| RB-08: Rotate secrets | Scheduled or on compromise |
| RB-09: Restore from backup | Data loss or corruption |
| RB-10: Onboard new engineer | Access setup checklist |

---

## RB-01: Deploy to Staging

**Trigger:** Automated on merge to `main`
**Expected time:** 8–12 minutes
**Owner:** On-call engineer (monitors)

```bash
# Staging deploys automatically via GitHub Actions (deploy.yml)
# Monitor at: https://github.com/quorum-ai/quorum/actions

# Verify staging health after deploy:
curl https://staging.api.quorum.ai/health
# Expected: {"status": "ok", "version": "abc1234", "db": "ok", "redis": "ok"}

# Check Datadog for errors in first 10 minutes:
# Dashboard: https://app.datadoghq.com/dashboard/quorum-staging

# If health check fails, check logs:
aws logs tail /ecs/quorum-api-staging --follow --since 10m

# Manual trigger if needed:
gh workflow run deploy.yml -f environment=staging
```

---

## RB-02: Deploy to Production

**Trigger:** Manual — requires CTO or senior engineer
**Expected time:** 15–20 minutes (includes smoke test wait)
**Owner:** Release owner + on-call engineer monitoring

### Pre-deploy checklist
```
[ ] Staging deploy succeeded in last 24 hours with same image tag
[ ] No P0 or P1 incidents open
[ ] DB migration tested on staging (if applicable, see RB-04)
[ ] Notify #engineering: "Deploying to production — image: {tag}"
[ ] Verify Datadog staging error rate < 0.5% in last 1 hour
[ ] Confirm Sentry shows no new high-priority errors on staging
```

### Deploy steps
```bash
# 1. Trigger production deploy via GitHub Actions (requires manual approval)
gh workflow run deploy.yml -f environment=production -f image_tag={tag}

# 2. Monitor the deploy
# GitHub Actions: watch job in browser
# Datadog: watch API error rate + latency in real-time

# 3. Verify post-deploy health
curl https://api.quorum.ai/health
# Expected: {"status": "ok", "version": "{tag}", "db": "ok", "redis": "ok"}

# 4. Run manual smoke tests
./scripts/smoke_test_production.sh

# 5. Monitor for 15 minutes in Datadog
# Watch: error rate, p95 latency, DB connection pool, Redis memory

# 6. Announce: "Production deploy complete ✅ — image: {tag}"
```

### smoke_test_production.sh
```bash
#!/bin/bash
set -e
API="https://api.quorum.ai"

echo "Testing health endpoint..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API/health")
[ "$STATUS" = "200" ] || (echo "FAIL: health check returned $STATUS" && exit 1)

echo "Testing auth endpoint (unauthenticated)..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API/v1/meetings")
[ "$STATUS" = "401" ] || (echo "FAIL: unauth endpoint returned $STATUS (expected 401)" && exit 1)

echo "Testing survey submission (no-auth endpoint)..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$API/v1/meetings/nonexistent/survey/respond" \
  -H "Content-Type: application/json" \
  -d '{"responses":[]}')
[ "$STATUS" = "404" ] || (echo "FAIL: expected 404, got $STATUS" && exit 1)

echo "All smoke tests passed ✅"
```

---

## RB-03: Rollback Production

**Trigger:** Production deploy caused errors or data issues
**Time to rollback:** < 5 minutes
**Owner:** On-call engineer — do NOT wait for CTO if production is down

### Immediate rollback (ECS — revert to previous task definition)
```bash
# 1. Find previous task definition revision
aws ecs describe-services \
  --cluster quorum-production \
  --services quorum-api-production \
  --query 'services[0].taskDefinition'
# Returns something like: arn:aws:ecs:us-east-1:xxx:task-definition/quorum-api-production:47
# Previous version is :46

# 2. Update service to previous revision
aws ecs update-service \
  --cluster quorum-production \
  --service quorum-api-production \
  --task-definition quorum-api-production:PREVIOUS_REVISION \
  --force-new-deployment

# 3. Wait for service stability (~5 minutes)
aws ecs wait services-stable \
  --cluster quorum-production \
  --services quorum-api-production

# 4. Verify health
curl https://api.quorum.ai/health

# 5. Announce in #engineering:
# "🔄 Rolled back production to task def :PREVIOUS_REVISION due to {issue}"

# 6. Open incident ticket, document:
#   - What went wrong
#   - Time to detection
#   - Time to rollback
#   - Root cause (once known)
```

### If DB migration was applied and needs reverting
```bash
# WARNING: Only if migration is reversible (has downgrade function)
# First: ensure API is rolled back to previous version
# Then:

aws ecs run-task \
  --cluster quorum-production \
  --task-definition quorum-migrate-production \
  --overrides '{"containerOverrides":[{
    "name":"quorum-api",
    "command":["alembic","downgrade","-1"]
  }]}'

# Verify DB state
psql $DATABASE_URL -c "SELECT version_num FROM alembic_version;"
```

---

## RB-04: Database Migration

**Run before EVERY production deploy that includes schema changes**
**Expected time:** 1–10 minutes (depends on table size and lock needs)

### Safe migration principles
```
1. All migrations must be backward-compatible with the previous app version
   (old code must be able to run against new schema)
2. Adding columns: always nullable or with a default value
3. Dropping columns: two-step (first remove from code, then drop column in next deploy)
4. Adding indexes: use CONCURRENTLY to avoid locking
5. Never rename columns in a single deploy (add new → migrate data → remove old)
```

### Migration checklist
```bash
# 1. Generate migration (auto-detect from model changes)
poetry run alembic revision --autogenerate -m "add_outcome_checkin_fields"

# 2. Review the generated migration file carefully
# Check: is the downgrade() function correct?
# Check: any table locks? (ALTER TABLE on large tables can cause downtime)

# 3. Test on local
poetry run alembic upgrade head
poetry run alembic downgrade -1  # verify rollback works
poetry run alembic upgrade head  # re-apply

# 4. Test on staging
# Staging deploy automatically runs: alembic upgrade head

# 5. Check migration duration on staging
# If > 30 seconds on staging: expect 5-10x longer on production
# If > 5 minutes on production data size: plan for maintenance window

# 6. Long-running migrations: use CONCURRENTLY for indexes
# BAD:  CREATE INDEX idx_decisions_org ON decisions(org_id);
# GOOD: CREATE INDEX CONCURRENTLY idx_decisions_org ON decisions(org_id);

# Add to migration:
def upgrade():
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
        "idx_decisions_org ON decisions(org_id)"
    )
    # CONCURRENTLY cannot run inside a transaction
    # Must call: op.execute() directly

# Set: transaction_per_migration = False in alembic.ini for this migration
```

### Migration in production deploy
```bash
# Production deploy workflow automatically runs:
aws ecs run-task \
  --cluster quorum-production \
  --task-definition quorum-migrate-production \
  --overrides '{"containerOverrides":[{"name":"quorum-api","command":["alembic","upgrade","head"]}]}'

# Monitor migration task logs:
aws logs tail /ecs/quorum-migrate-production --follow --since 5m
```

---

## RB-05: P0 Incident Response

**Definition:** Production down, active data breach, data corruption
**Response time:** 15 minutes to first action
**Owner:** On-call engineer — wake up CTO if needed

```
T+0:   PagerDuty fires → acknowledge (stops escalation)
T+2:   Join #incidents on Slack, post:
       "🔥 P0 INCIDENT: [brief description]
        Investigating... [your name] is IC (incident commander)"

T+5:   ASSESS:
       □ Is the service completely down? (check: curl https://api.quorum.ai/health)
       □ Is data being leaked? (check: Datadog anomalous query patterns)
       □ Is an attack ongoing? (check: CloudWatch access logs for unusual IPs)
       □ How many customers affected? (check: active sessions in Redis)

T+10:  CONTAIN:
       If service down → attempt rollback (RB-03)
       If active attack → block at ALB WAF:
         aws wafv2 update-ip-set --name quorum-blocklist --scope REGIONAL \
           --addresses ["ATTACKER_IP/32"] --id WAF_IP_SET_ID --lock-token TOKEN

       If data breach suspected:
         → Do NOT delete logs (preserve evidence)
         → Screenshot Datadog/CloudWatch anomalies immediately

T+15:  NOTIFY:
       → CEO via phone (not Slack) if:
         - Data breach confirmed
         - Service down > 15 minutes
         - Personal data possibly exposed

T+30:  STATUS UPDATE in #incidents every 30 minutes until resolved

T+resolution:
       → Post resolution message in #incidents:
         "✅ RESOLVED: [what was fixed] at [time]
          Duration: [X minutes]
          Customers affected: [N orgs]
          Root cause: [brief]
          Post-mortem: [link, due within 48 hours]"

T+48h: Post-mortem document published to #engineering
       Use Quorum's own post-mortem template (ironic but real)
```

### P0 diagnostic commands
```bash
# API health
curl -v https://api.quorum.ai/health

# Recent error logs
aws logs filter-log-events \
  --log-group-name /ecs/quorum-api-production \
  --start-time $(date -d '30 minutes ago' +%s000) \
  --filter-pattern '"ERROR"'

# DB connection count
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=quorum-production \
  --start-time $(date -d '1 hour ago' -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 \
  --statistics Average

# Redis memory
aws elasticache describe-events \
  --source-identifier quorum-production \
  --source-type cache-cluster \
  --duration 60

# Celery queue depth
redis-cli -u $REDIS_URL LLEN celery

# Active ECS tasks
aws ecs list-tasks --cluster quorum-production --service-name quorum-api-production
aws ecs describe-tasks --cluster quorum-production \
  --tasks $(aws ecs list-tasks --cluster quorum-production --service-name quorum-api-production --query taskArns --output text)
```

---

## RB-06: Scale Up Under Load

**Trigger:** Celery queue depth > 50 OR API p95 latency > 2s sustained
**Expected time:** 3–5 minutes

```bash
# Scale API service (add tasks)
aws ecs update-service \
  --cluster quorum-production \
  --service quorum-api-production \
  --desired-count 8   # default is 4

# Scale worker service
aws ecs update-service \
  --cluster quorum-production \
  --service quorum-worker-production \
  --desired-count 8   # default is 4

# Scale back down after load subsides
aws ecs update-service \
  --cluster quorum-production \
  --service quorum-api-production \
  --desired-count 4

# Monitor queue drain:
watch -n 5 'redis-cli -u $REDIS_URL LLEN celery'

# Increase DB connection pool (requires deploy with env var change):
# DATABASE_POOL_SIZE=20  (from default 10)
# Caution: don't exceed RDS max_connections (default 100 on db.r7g.xlarge)
```

---

## RB-07: GDPR Data Deletion (Customer Request)

**Trigger:** Customer submits data deletion request
**SLA:** Complete within 24 hours
**Owner:** CTO approves, engineer executes

```bash
# Step 1: Verify the requester is authorized
# Must be: org admin, or employee with valid GDPR right-to-erasure claim
# For org deletion: org admin must submit via support@quorum.ai
# For individual: individual must submit via privacy@quorum.ai

# Step 2: Log the request (required for compliance)
psql $DATABASE_URL << EOF
INSERT INTO audit_log (action, org_id, metadata, occurred_at)
VALUES (
  'gdpr.deletion_request',
  '{ORG_ID}',
  '{"requester_email": "{EMAIL}", "request_date": "{DATE}", "type": "full_org"}',
  NOW()
);
EOF

# Step 3: Execute deletion
psql $DATABASE_URL << EOF
SELECT purge_org_data('{ORG_ID}'::UUID);
EOF

# Step 4: Purge S3 recordings (if any)
aws s3 rm s3://quorum-recordings-prod/{ORG_ID}/ --recursive

# Step 5: Remove from Pinecone (decision embeddings)
# Run via API or Python script:
python scripts/purge_pinecone_org.py --org-id {ORG_ID}

# Step 6: Remove from InfluxDB
influx delete \
  --bucket meeting_metrics \
  --predicate "org_id=\"{ORG_ID}\"" \
  --start 1970-01-01T00:00:00Z \
  --stop $(date -u +%Y-%m-%dT%H:%M:%SZ)

# Step 7: Deactivate Auth0 users
# List users with @{ORG_DOMAIN}, deactivate via Auth0 Management API

# Step 8: Verify deletion
psql $DATABASE_URL -c "SELECT COUNT(*) FROM organizations WHERE id = '{ORG_ID}';"
# Expected: 0

# Step 9: Confirm to customer (within 24 hours of request)
# Email template: templates/gdpr_deletion_confirmation.txt

# Step 10: Log completion
psql $DATABASE_URL << EOF
INSERT INTO audit_log (action, metadata, occurred_at)
VALUES (
  'gdpr.deletion_completed',
  '{"org_id": "{ORG_ID}", "completed_at": "{TIMESTAMP}", "executed_by": "{ENGINEER_EMAIL}"}',
  NOW()
);
EOF
```

---

## RB-08: Rotate Secrets

**Schedule:** 
- `SPEAKER_HASH_SECRET` + `RESPONDENT_HASH_SECRET`: Annually (January)
- Database passwords: Every 90 days (RDS auto-rotation)
- API keys (Anthropic, Deepgram, etc.): On engineer offboarding
- Auth0 client secret: Annually

### Annual HMAC secret rotation

```
⚠️  WARNING: Rotating anonymization secrets DOES NOT de-anonymize existing data.
Existing hashes remain valid but new responses to old meetings get different hashes.
This means: post-rotation responses to old meetings cannot be correlated with pre-rotation ones.
This is ACCEPTABLE — correlation only needed within same meeting, and meetings close within days.

⚠️  WARNING: Do NOT rotate these secrets if you have open meetings (survey_open status).
Wait until all active meetings are closed.
```

```bash
# 1. Verify no open surveys
psql $DATABASE_URL -c "SELECT COUNT(*) FROM meetings WHERE status = 'survey_open';"
# Must be 0 before proceeding

# 2. Generate new secrets
NEW_SPEAKER_SECRET=$(openssl rand -hex 32)
NEW_RESPONDENT_SECRET=$(openssl rand -hex 32)

# 3. Update in AWS Secrets Manager
aws secretsmanager put-secret-value \
  --secret-id quorum/production/SPEAKER_HASH_SECRET \
  --secret-string "$NEW_SPEAKER_SECRET"

aws secretsmanager put-secret-value \
  --secret-id quorum/production/RESPONDENT_HASH_SECRET \
  --secret-string "$NEW_RESPONDENT_SECRET"

# 4. Force ECS service restart to pick up new secrets
aws ecs update-service \
  --cluster quorum-production \
  --service quorum-api-production \
  --force-new-deployment

# 5. Log the rotation
psql $DATABASE_URL -c "
INSERT INTO audit_log (action, metadata, occurred_at)
VALUES ('secret.rotated', '{\"secret_names\": [\"SPEAKER_HASH_SECRET\", \"RESPONDENT_HASH_SECRET\"]}', NOW());
"
```

---

## RB-09: Restore from Backup

**RDS automated backups:** 7-day retention, point-in-time recovery

```bash
# 1. Identify restore point (find time before corruption)
aws rds describe-db-instance-automated-backups \
  --db-instance-identifier quorum-production

# 2. Restore to new instance (do NOT overwrite production directly)
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier quorum-production \
  --target-db-instance-identifier quorum-production-restored-20260115 \
  --restore-time 2026-01-15T10:00:00Z

# 3. Wait for restore to complete (~20 minutes)
aws rds wait db-instance-available \
  --db-instance-identifier quorum-production-restored-20260115

# 4. Verify data on restored instance
psql postgresql://admin:password@restored-instance.rds.amazonaws.com/quorum \
  -c "SELECT COUNT(*) FROM decisions;"

# 5. If data looks correct: 
#    Option A: Point application to restored instance (update DATABASE_URL in Secrets Manager)
#    Option B: Export specific tables and import to production (surgical recovery)

# 6. Delete restored instance after confirmed recovery
aws rds delete-db-instance \
  --db-instance-identifier quorum-production-restored-20260115 \
  --skip-final-snapshot
```

---

## RB-10: Onboard New Engineer

**Checklist for first day access**

```
ACCOUNTS TO CREATE:
[ ] GitHub: add to quorum-ai org, assign team (frontend/backend/infra)
[ ] AWS IAM: create user with read-only prod, full staging access
[ ] Auth0: add to engineering tenant (read-only production)
[ ] Datadog: add user, assign Dashboard Viewer role
[ ] Sentry: add to quorum project
[ ] PagerDuty: add to on-call rotation (after 30 days)
[ ] Stripe: add as Developer (no production access until 90 days)
[ ] Anthropic Console: add as member

LOCAL SETUP:
[ ] Clone repo: git clone git@github.com:quorum-ai/quorum.git
[ ] Copy: cp .env.example .env
[ ] Fill in ANTHROPIC_API_KEY and OPENAI_API_KEY (from 1Password)
[ ] Run: docker compose up -d
[ ] Run: docker compose exec api alembic upgrade head
[ ] Verify: curl http://localhost:8000/health returns {"status":"ok"}
[ ] Run: poetry run pytest (should pass)

EDUCATION:
[ ] Read: README.md (product overview)
[ ] Read: 00_MASTER_BUILD_PROMPT.md (system architecture)
[ ] Read: 09_SECURITY_COMPLIANCE.md (security model)
[ ] Read: This runbook (operations)
[ ] Shadow: one production deploy with senior engineer
[ ] Shadow: one incident response with senior engineer (simulated)

ACCESS REMOVED ON OFFBOARDING:
[ ] Auth0 account deactivated immediately
[ ] AWS IAM user deactivated immediately
[ ] GitHub org removed
[ ] API keys generated by this engineer rotated (see RB-08)
[ ] Remove from on-call rotation
```

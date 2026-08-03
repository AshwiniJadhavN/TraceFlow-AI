# Deployment Guide for TraceFlow AI

This guide covers deploying TraceFlow AI in staging and production environments, with specific focus on medical device compliance and audit readiness.

---

## Pre-Deployment Checklist

Before any deployment, ensure the following requirements are met:

### Code Quality
- [ ] All CI checks passing (code quality, type checking, coverage >60%)
- [ ] Linting and formatting validated with `make lint`
- [ ] Type checking passed with `make type-check`
- [ ] Test suite passed with `make test`

### Security & Compliance
- [ ] Security scan completed (bandit) - no HIGH/CRITICAL issues
- [ ] Dependency audit passed - no known vulnerabilities
- [ ] API keys rotated and not committed
- [ ] SBOM (Software Bill of Materials) generated and reviewed
- [ ] No hardcoded secrets in code

### Documentation & Change Control
- [ ] Change log entry added (semver versioning)
- [ ] IEC 62304 traceability verified
- [ ] SECURITY.md requirements verified
- [ ] Release notes prepared
- [ ] Previous version backed up (for rollback)

---

## Building & Publishing Container Image

### Automated Build (Recommended)

```bash
# 1. Create a version tag (semver)
git tag -a v0.2.0 -m "Release v0.2.0: Enhanced risk matrix visualization"

# 2. Push tag to trigger CD pipeline
git push origin v0.2.0

# 3. Monitor the workflow
gh run list --workflow=cd.yml --limit 5

# 4. Verify image published to GHCR
docker pull ghcr.io/your-username/traceflow-ai:v0.2.0
docker inspect ghcr.io/your-username/traceflow-ai:v0.2.0
```

### Manual Build (Local Testing)

```bash
# Build image locally
docker build -t traceflow-ai:v0.2.0-local .

# Run and validate
docker run \
  -e ANTHROPIC_API_KEY="your-key" \
  traceflow-ai:v0.2.0-local \
  --help

# Tag and push manually (if needed)
docker tag traceflow-ai:v0.2.0-local ghcr.io/your-username/traceflow-ai:v0.2.0
docker push ghcr.io/your-username/traceflow-ai:v0.2.0
```

---

## Kubernetes, Helm, and Terraform

TraceFlow AI is a CLI batch workload. Production packaging therefore centers on `Job` and optional `CronJob` resources, not a long-lived HTTP deployment.

### Raw Kubernetes manifests

The repository includes a complete baseline under `infra/kubernetes/base/`:

- namespace and service account
- API-key secret template
- run configuration `ConfigMap`
- persistent output claim
- one-shot `Job`
- scheduled `CronJob`
- namespace-scoped `NetworkPolicy`

```bash
kubectl apply -k infra/kubernetes/base
kubectl create secret generic traceflow-anthropic \
  --from-literal=ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl create job --from=cronjob/traceflow-ai-scheduled traceflow-manual-$(date +%s) -n traceflow-ai
```

### Helm chart

The Helm chart under `charts/traceflow-ai/` exposes the batch command mode, requirement payload, schedule, OTLP endpoint, image tag, and secret strategy.

```bash
helm template traceflow-ai charts/traceflow-ai \
  --set image.repository=ghcr.io/your-username/traceflow-ai \
  --set image.tag=v1.0.0 \
  --set anthropic.existingSecret=traceflow-anthropic \
  --set workload.requirement="The system shall detect infusion occlusion within 5 seconds."
```

### Terraform workflow

Terraform wraps the chart deployment and can optionally install an OpenTelemetry Collector into a dedicated namespace.

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

Key variables:

- `namespace`: target namespace for the TraceFlow workload
- `image_repository` / `image_tag`: published container image
- `anthropic_api_key`: sensitive input used to create or populate the runtime secret
- `enable_otel_collector`: install the collector via Helm
- `job_enabled` / `cronjob_enabled`: choose one-shot versus scheduled execution
- `requirement` / `system_context`: runtime payload injected into the Job/CronJob

---

## OpenTelemetry observability

Python instrumentation is wired into the CLI entrypoints, orchestrators, and agent model calls. Export spans by setting `OTEL_EXPORTER_OTLP_ENDPOINT` to an OTLP/HTTP collector, for example:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://otel-collector.observability.svc.cluster.local:4318/v1/traces"
python main.py analyze "The system shall verify user identity before delivering therapy."
```

For quick local verification without a collector:

```bash
export TRACEFLOW_OTEL_CONSOLE=true
python main.py analyze "The system shall log all remote configuration changes."
```

---

## Policy-as-Code

Policy bundles are included under `policy/`:

- `policy/kyverno/`: admission policies for non-root execution, secret-backed credentials, and pinned images.
- `policy/opa/`: equivalent Rego rules for OPA or Gatekeeper-style validation workflows.

Example Kyverno validation:

```bash
kyverno apply policy/kyverno -r infra/kubernetes/base/job.yaml -r infra/kubernetes/base/cronjob.yaml
```

---

## Staging Deployment

### Manual Trigger

```bash
# Trigger CD workflow for staging environment
gh workflow run cd.yml -f environment=staging

# Monitor real-time
gh run list --workflow=cd.yml --status in_progress

# Get run details
gh run view <RUN_ID> --log
```

### Docker Compose (Local Staging Simulation)

```bash
# Start application in container
docker compose up traceflow

# In another terminal, test the CLI
docker compose exec traceflow python main.py analyze \
  --requirement "The system shall verify user identity" \
  --output staging_results.json
```

### Validation

```bash
# Health check
curl -X GET http://localhost:8000/health -w "\n"

# Verify agent orchestration completes
timeout 120 docker compose exec traceflow \
  python main.py system-analyze \
  --requirement "System shall encrypt patient data" \
  --output /app/output/test-report.json

# Check output directory
ls -la output/
cat output/test-report.json | jq '.metadata.agents_completed'
```

---

## Production Deployment

### Prerequisites for Production

- [ ] Staging deployment validated for 24+ hours
- [ ] Zero errors in staging logs
- [ ] Performance acceptable (agents complete within SLA)
- [ ] Approval from medical device compliance team
- [ ] Audit log access configured
- [ ] Backup/rollback procedure tested

### Production Release

```bash
# Create production release tag
git tag -a v1.0.0 -m "Production Release v1.0.0

- IEC 62304 compliance verified
- Security audit passed
- Load testing completed
- Medical device team approved"

# Push to trigger production deployment
git push origin v1.0.0

# Monitor deployment
gh run list --workflow=cd.yml --limit 3
gh run view <PROD_RUN_ID> --log

# Verify production image
docker pull ghcr.io/your-username/traceflow-ai:v1.0.0
docker run --rm ghcr.io/your-username/traceflow-ai:v1.0.0 --version
```

### Verify Production Deployment

```bash
# Check image metadata (SBOM, provenance)
docker inspect --format='{{json .Config.Labels}}' \
  ghcr.io/your-username/traceflow-ai:v1.0.0 | jq .

# Run health check
PROD_API_ENDPOINT="your-production-url:port"
curl -s -w "\nHTTP Status: %{http_code}\n" \
  http://$PROD_API_ENDPOINT/health

# Verify no secrets in logs
docker logs $(docker ps -q -f ancestor=ghcr.io/your-username/traceflow-ai:v1.0.0) \
  | grep -i "api_key\|secret" || echo "✅ No secrets in logs"
```

---

## Post-Deployment Verification

### Immediate (5-10 minutes)

1. **Health Check Endpoint**
   ```bash
   curl -f http://traceflow-prod:8000/health || echo "❌ Health check failed"
   ```

2. **Agent Orchestration SLA**
   ```bash
   # Agent orchestration should complete within 60s per requirement
   time python main.py analyze --requirement "Test" --output /tmp/test.json
   # Expected: ~30-45 seconds
   ```

3. **Output Validation**
   ```bash
   # Verify output format and completeness
   jq '.metadata | keys' output/latest-report.json
   # Should include: agents_completed, timestamp, risk_level, etc.
   ```

4. **Log Inspection (No Errors)**
   ```bash
   # Check for exceptions or API errors
   docker logs <container_id> | grep -i "error\|exception\|failed" | wc -l
   # Expected: 0 errors
   ```

### Short-term (30 minutes - 1 hour)

- Run smoke test suite: `make smoke-test`
- Verify multi-agent pipeline completeness
- Check resource usage (CPU, memory, API calls)
- Validate output quality (test with known requirements)

### Long-term (Daily/Weekly)

- Monitor error rates and response times
- Track API usage and cost
- Audit log review for compliance
- Scheduled health checks

---

## Rollback Procedure

### If Issues Detected

**Quick Rollback (Same Image Version)**

```bash
# Revert to previous working version
git checkout <PREVIOUS_TAG>
git push origin <PREVIOUS_TAG>

# Or manually redeploy previous image
docker run -d \
  -e ANTHROPIC_API_KEY="your-key" \
  ghcr.io/your-username/traceflow-ai:v1.0.0 \  # Previous version
  python main.py
```

**Full Rollback**

```bash
# Stop current deployment
docker compose down

# Start previous version from backup
docker compose -f docker-compose.v0.9.5.yml up -d

# Verify rollback successful
curl http://localhost:8000/health
```

### Post-Rollback

1. Analyze logs for root cause
2. Document issue in TROUBLESHOOTING.md
3. Fix in feature branch
4. Re-test thoroughly before next release

---

## Version Management

### Semantic Versioning

TraceFlow AI follows [Semantic Versioning](https://semver.org/):

```
v<MAJOR>.<MINOR>.<PATCH>
v1        .2      .3

- MAJOR: Breaking changes to agent outputs or IEC 62304 classifications
- MINOR: New agents, new analysis types
- PATCH: Bug fixes, output formatting improvements
```

### Release Artifacts

Each release includes:
- ✅ Docker image (signed with provenance)
- ✅ SBOM (Software Bill of Materials)
- ✅ Release notes (with change log)
- ✅ Hash checksums for integrity
- ✅ Deployment instructions

---

## Troubleshooting Deployments

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for:
- Common deployment failures
- API key configuration issues
- Container startup problems
- Performance tuning

---

## Emergency Contacts

For urgent production issues:
- **On-call Engineer**: Check team wiki/Slack
- **Medical Device Compliance**: Internal contact list
- **Security Incident Response**: security@...

---

## References

- [CONTRIBUTING.md](CONTRIBUTING.md) - Development guidelines
- [SECURITY.md](SECURITY.md) - Security best practices
- [README.md](README.md) - Project overview
- [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) - Architecture details

**Last Updated**: July 29, 2026

# Sprint 28 — Definition of Done

- [x] Persistent rate limiter.
- [x] PostgreSQL atomic rate-limit upsert path.
- [x] Hashed IP/phone limiter keys.
- [x] OTP send limiting.
- [x] OTP verify limiting.
- [x] Refresh limiting.
- [x] Payment webhook limiting.
- [x] 429 Retry-After headers.
- [x] Persistent security events.
- [x] Admin security inspection.
- [x] Trusted hosts.
- [x] Safe request IDs.
- [x] Request body limit.
- [x] Security headers.
- [x] HSTS production setting.
- [x] Production config fail-fast.
- [x] HTTP metrics.
- [x] Request duration header.
- [x] Prometheus endpoint.
- [x] Observability health.
- [x] Admin observability summary.
- [x] Security cleanup worker job.
- [x] Non-root Docker image.
- [x] Production Compose topology.
- [x] Migration job.
- [x] Deployment preflight.
- [x] PostgreSQL integration-check harness.
- [x] CI PostgreSQL service.
- [x] Alembic migration.
- [x] Regression tests.

## Not claimed locally
The ChatGPT container does not expose a live PostgreSQL server, so the PostgreSQL concurrency integration script is included and CI-wired but not claimed as locally executed.

## خارج Scope Sprint 28
- Managed object storage.
- Push notification provider.
- SMS provider.
- Email provider.
- CDN/WAF provisioning.
- Kubernetes/Terraform.

Next: Sprint 29.

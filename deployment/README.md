# Baytna Deployment Foundation — Sprint 28

## Production boot sequence

1. Create `.env.production` from `.env.production.example`.
2. Replace every placeholder secret.
3. Point `BAYTNA_DATABASE_URL` at PostgreSQL.
4. Configure explicit CORS origins and allowed hosts.
5. Use a real payment provider adapter.
6. Run deployment preflight.
7. Run Alembic migrations.
8. Start API.
9. Start worker.
10. Verify readiness, observability and dead-letter counters.

## Preflight

```bash
cd backend
python ../scripts/deployment_preflight.py
```

Production settings fail fast if:
- development OTP is exposed
- demo data seeding is enabled
- payment provider is mock
- database is not PostgreSQL
- CORS uses wildcard/localhost
- Allowed Hosts is wildcard/empty
- HSTS is disabled
- secrets are weak/development placeholders

## Containers

```bash
docker compose -f docker-compose.production.yml up --build
```

Services:
- PostgreSQL
- one-shot migration container
- API
- background worker

## Observability

Health:
- `/health/live`
- `/health/ready`
- `/health/reliability`
- `/health/observability`

Metrics:
- `/metrics`

Admin:
- `/api/v1/admin/observability/summary`
- `/api/v1/admin/observability/security-events`
- `/api/v1/admin/observability/rate-limit-buckets`

## PostgreSQL integration

Sprint 28 includes a dedicated integration script intended for CI/real PostgreSQL:
`python ../scripts/postgres_integration_check.py`

It validates:
- actual PostgreSQL dialect
- database connectivity
- current Alembic schema
- concurrent persistent rate-limit increments
- `SKIP LOCKED` Outbox claim behavior

This must run against a real PostgreSQL instance. SQLite cannot prove those locking semantics.

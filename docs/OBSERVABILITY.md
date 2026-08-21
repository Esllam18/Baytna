# Sprint 28 — Observability

## Request metrics
The API tracks process-local:
- total requests
- total 5xx responses
- average request duration
- response status counts
- HTTP method counts
- process uptime

No phone/user/order identifiers are used as metric labels.

This avoids high-cardinality and sensitive metric dimensions.

## Headers
Every processed response exposes:
- `X-Request-ID`
- `X-Process-Time-Ms`

## Metrics
Prometheus-compatible plaintext:
`GET /metrics`

## Admin view
`GET /api/v1/admin/observability/summary`

Combines:
- process HTTP snapshot
- security-event count
- rate-limit bucket count

## Scale boundary
Metrics registry is process-local.

In multi-replica production, Prometheus scrapes each replica and aggregates across instances.

Security/rate-limit records are database-backed and shared.

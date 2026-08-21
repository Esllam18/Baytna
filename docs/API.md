# Sprint 27 API Additions

## Reliability Summary — Admin
`GET /api/v1/admin/reliability/summary`

Returns:
- outbox status counts
- background job counts
- worker heartbeats

## Outbox — Admin
- `GET /api/v1/admin/reliability/outbox`
- `POST /api/v1/admin/reliability/outbox/{event_id}/retry`

Optional list query:
- `status`
- `limit`

## Background Jobs — Admin
- `GET /api/v1/admin/reliability/jobs`
- `POST /api/v1/admin/reliability/jobs/{job_id}/retry`

## Manual worker tick — Admin
`POST /api/v1/admin/reliability/run-once`

Useful for operations/testing. Continuous production execution should use the standalone worker process.

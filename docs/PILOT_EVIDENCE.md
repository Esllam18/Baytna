# Sprint 44 — Pilot Timing Evidence

## Evidence collector

```bash
python scripts/pilot_delivery_timing_evidence.py \
  --api https://pilot-api.example.com \
  --admin-token "$BAYTNA_STAGING_ADMIN_BEARER_TOKEN" \
  --order-id "<REAL_DELIVERED_ORDER_ID>" \
  --incident-id "<OPTIONAL_REAL_INCIDENT_ID>" \
  --output deployment/pilot/delivery-timing-evidence.json
```

## The script proves

For the order:
- delivered state is real,
- immutable promise exists,
- actual delivery timestamp exists,
- stored timing status matches timestamps,
- stored late minutes match timestamps.

For the Control Room:
- On-Time KPI is not null,
- Promise Coverage is 100% for the selected launch sample.

With `--incident-id`:
- incident is present,
- Admin has an `ops_incident` notification associated with it.

## It does not prove

By itself it does not prove:
- the FCM provider delivered the Push to a physical device,
- Paymob funded/captured a real transaction,
- Twilio delivered SMS,
- S3 is production-ready.

Those remain separate release evidence gates.

## Required release evidence

The main release evidence file must mark true only after proof:

```text
delivery_promise_live_order_verified
on_time_kpi_measurable
ops_auto_escalation_verified
ops_incident_notification_verified
```

and reference:

```text
delivery_timing_evidence_file
ops_incident_evidence_id
```

## Fail closed

Missing or false evidence keeps:

```text
GO-LIVE: BLOCKED
```

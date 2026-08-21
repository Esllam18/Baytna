# Sprint 50 — Post-Launch Evidence & Stabilization Gate

## Live collector

Run only against a real HTTPS deployment:

```bash
python scripts/pilot_post_launch_stabilization_evidence.py \
  --api https://pilot-api.example.com \
  --admin-token "$BAYTNA_STAGING_ADMIN_BEARER_TOKEN" \
  --zone-id "<REAL_ZONE_ID>" \
  --session-id "<REAL_SESSION_ID>" \
  --output deployment/pilot/post-launch-stabilization-evidence.json
```

It does not mutate the pilot.

It verifies:

- release `0.50.0`,
- migration `0025_sprint50`,
- stamped commit,
- Auto-Pause enabled with anti-flapping threshold,
- persisted Capacity Forecast,
- at least one closed system-prepared cadence row and no overdue open row,
- final evidence packs are permanent,
- incomplete packs carry working retention metadata,
- latest Expansion Review is Healthy/Continue with no blockers.

## Independent gate

```bash
python scripts/expansion_review_gate.py \
  deployment/pilot/post-launch-stabilization-evidence.json
```

Only:

```text
STABILIZATION DECISION: PASS
```

supports the next expansion decision.

The example evidence file intentionally returns `BLOCKED`.
Local/mock results are not live evidence.

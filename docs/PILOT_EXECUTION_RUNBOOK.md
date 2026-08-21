# Pilot Execution Runbook

## Before start

1. Complete the separate Go-Live Gate.
2. Create the pilot program in `/pilot`.
3. Confirm area scope and dates.
4. Confirm targets.
5. Activate the pilot.

## Daily

1. Use `/control-room` for operational incidents.
2. Use `/pilot` for stability progress.
3. Confirm Worker health.
4. Confirm `pilot.snapshot` remains schedulable.
5. Do not manually edit historical order promises or delivery outcomes to improve KPIs.

## Weekly review

Review every completed full week:

- evaluability,
- promise coverage,
- rating,
- repeat,
- On-Time,
- cancellation,
- support/refunds,
- weekly PASS/FAIL.

If a week is `NOT EVALUABLE`, fix the missing instrumentation/data quality issue; do not mark it as passed manually.

## QA evidence

As reviewed artifacts become available, store references for:

```text
operational_profit_positive
pilot_qa_exit
operations_signoff
```

Do not mark a passed evidence item without an actual reference.

## End of pilot

1. Complete the pilot program.
2. Refresh snapshots.
3. Review Post-Pilot Analytics.
4. Confirm no Critical incident.
5. Confirm Payment Reconciliation clean.
6. Export live scale evidence:

```bash
python scripts/pilot_scale_evidence.py \
  --api https://pilot-api.example.com \
  --admin-token "$BAYTNA_STAGING_ADMIN_BEARER_TOKEN" \
  --program-id "<PILOT_PROGRAM_ID>" \
  --output deployment/pilot/real-scale-evidence.json
```

7. Run the independent scale gate:

```bash
python scripts/pilot_scale_gate.py \
  deployment/pilot/real-scale-evidence.json
```

Only:

```text
SCALE DECISION: PASS
```

means the machine evidence is complete enough for the human expansion decision.

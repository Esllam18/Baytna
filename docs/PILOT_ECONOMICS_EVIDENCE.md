# Sprint 46 — Live Pilot Economics Evidence

## Collector

```bash
python scripts/pilot_economics_evidence.py \
  --api https://pilot-api.example.com \
  --admin-token "$BAYTNA_STAGING_ADMIN_BEARER_TOKEN" \
  --program-id "<PILOT_PROGRAM_ID>" \
  --min-contribution-margin-pct 15 \
  --output deployment/pilot/pilot-economics-evidence.json
```

## It checks

- HTTPS source,
- release `0.46.0`,
- migration `0021_sprint46`,
- backend economics evaluable,
- Revenue Coverage = 100%,
- Cost Coverage = 100%,
- no unverified costs,
- operational profit positive,
- optional contribution-margin threshold.

## It does not invent provider costs

Before this collector can pass, actual cost entries must already exist and be verified.

No chef payout, courier fee, payment fee, or fixed overhead is auto-guessed by the evidence collector.

## Scale evidence

`pilot_scale_evidence.py` now collects:
- release,
- pilot,
- stability,
- cohorts,
- QA/sign-off evidence,
- post-pilot report,
- economics report.

`pilot_scale_gate.py` verifies backend profitability directly.

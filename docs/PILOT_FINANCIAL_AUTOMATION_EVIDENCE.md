# Sprint 47 — Pilot Financial Automation Evidence

Run against the deployed HTTPS pilot:

```bash
python scripts/pilot_financial_automation_evidence.py \
  --api https://pilot-api.example.com \
  --admin-token "$BAYTNA_STAGING_ADMIN_BEARER_TOKEN" \
  --program-id "<REAL_PILOT_PROGRAM_ID>" \
  --zone-id "<REAL_EXPANSION_ZONE_ID>" \
  --output deployment/pilot/financial-automation-evidence.json
```

The script requires:

```text
release = 0.47.0
migration head = 0022_sprint47
```

It proves:
- at least one Applied provider-cost import for the program,
- a clean Reconciled Paymob settlement for the program,
- no blocked settlement batch for the program,
- Zone Budget Ready,
- persisted controlled rollout evidence,
- current Zone in Canary/Limited/Full.

It does not prove a Push reached a physical device, Paymob funded a merchant bank account, or Twilio billed the real account unless those provider facts are independently present in the staging evidence.

The output should be referenced by:

```text
financial_automation_evidence_file
settlement_batch_reference
expansion_rollout_event_id
```

in the main release evidence.

Missing evidence keeps the main gate blocked.

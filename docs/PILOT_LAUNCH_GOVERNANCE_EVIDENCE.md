# Sprint 48 — Pilot Launch Governance Evidence

Run only against deployed HTTPS staging/pilot:

```bash
python scripts/pilot_launch_governance_evidence.py \
  --api https://pilot-api.example.com \
  --admin-token "$BAYTNA_STAGING_ADMIN_BEARER_TOKEN" \
  --program-id "<REAL_PILOT_PROGRAM_ID>" \
  --zone-id "<REAL_EXPANSION_ZONE_ID>" \
  --output deployment/pilot/launch-governance-evidence.json
```

Required deployment identity:

```text
release = 0.48.0
migration_head = 0023_sprint48
commit = real stamped commit
```

The script checks:
- Traffic Policy enabled,
- rollout bucket enforcement,
- daily/hourly/Chef caps,
- active rollout stage,
- persisted monitoring,
- latest health not Red,
- at least one admitted real Order,
- independently reviewed + Applied provider cost import,
- Reconciled + Closed provider settlement.

The output should support:

```text
traffic_governance_policy_verified
capacity_admission_verified
vendor_accounting_dual_control_verified
settlement_operations_closed
expansion_monitoring_verified
```

and artifact references:

```text
launch_governance_evidence_file
monitoring_snapshot_id
vendor_accounting_evidence_file
```

No local/mock run should be treated as live evidence.

# Current Go-Live Checklist — Sprint 50 Release

## Release
- [ ] API `0.50.0`
- [ ] Migration `0025_sprint50`
- [ ] Real commit stamped
- [ ] API/Worker/Admin same release

## Existing launch proof
- [ ] PostgreSQL staging
- [ ] HTTPS API/Admin
- [ ] mobile builds
- [ ] FCM × 3
- [ ] Sentry × 4
- [ ] Paymob real payment/webhook
- [ ] S3
- [ ] Twilio
- [ ] cross-app journey
- [ ] delivery promise / On-Time KPI
- [ ] Operations Control Room
- [ ] backend economics
- [ ] 100% cost coverage
- [ ] provider import
- [ ] settlement reconciliation + accounting close
- [ ] Expansion Budget
- [ ] Traffic Governance

## Launch Command
- [ ] Active Launch Command Session created
- [ ] Incident Commander assigned
- [ ] Finance Admin assigned
- [ ] Operations Admin assigned
- [ ] 12 Runbook steps Passed with references
- [ ] zero active Traffic Overrides before final evidence
- [ ] Launch Date Financial Close Closed
- [ ] Financial Close checksum captured
- [ ] Daily Close maker-checker satisfied
- [ ] Rollback Drill Passed
- [ ] Rollback Drill within recovery target
- [ ] Rollback independent verifier
- [ ] latest Monitoring not Red
- [ ] no Critical Zone incident
- [ ] Backend Launch Evidence Pack = Complete
- [ ] Evidence Pack checksum captured

## Release evidence booleans
- [ ] `launch_command_session_verified`
- [ ] `canary_runbook_complete`
- [ ] `daily_financial_close_closed`
- [ ] `rollback_drill_verified`
- [ ] `launch_evidence_pack_complete`

## Artifacts
- [ ] `launch_command_evidence_file`
- [ ] `launch_command_session_id`
- [ ] `daily_financial_close_id`
- [ ] `rollback_drill_id`
- [ ] `launch_evidence_pack_id`
- [ ] `launch_evidence_pack_checksum`

## Final gate

```bash
python scripts/go_live_gate.py \
  deployment/pilot/release-evidence.json
```

Only:

```text
GO-LIVE: PASS
```

authorizes launch.

# Current Go-Live Evidence Pack — Sprint 50 Release

## Backend Pack

Generated via:

```text
POST /api/v1/admin/launch-command/sessions/{session_id}/evidence-packs
```

The pack stores:

```text
release
session
zone
runbook
monitoring
financial close
rollback drill
traffic overrides
vendor accounting
critical incidents
```

plus:

```text
blockers
SHA-256 checksum
```

## Complete criteria

A pack is Complete only when all launch evidence is present and clean.

An operator cannot manually override the pack status.

## Live collector

Run against real HTTPS pilot:

```bash
python scripts/pilot_launch_command_evidence.py \
  --api https://pilot-api.example.com \
  --admin-token "$BAYTNA_STAGING_ADMIN_BEARER_TOKEN" \
  --session-id "<REAL_SESSION_ID>" \
  --output deployment/pilot/launch-command-evidence.json
```

The collector separately verifies:

- release `0.50.0`,
- migration `0025_sprint50`,
- stamped commit,
- operational session,
- complete Runbook,
- zero active overrides,
- closed launch-day financial close,
- passed rollback drill within target,
- complete Backend Evidence Pack.

Local/mock execution is not go-live evidence.

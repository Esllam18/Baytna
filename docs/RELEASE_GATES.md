# Sprint 49 — Release Gates

## Source

```bash
python scripts/release_source_preflight.py
python scripts/verify_sprint49_contract.py
python scripts/verify_sprint49_static.py
python scripts/verify_sprint49_structure.py
python scripts/verify_crash_reporting_static.py
```

## Identity

```text
version = 0.49.0
migration = 0024_sprint49
```

## Production startup policy

Required:

```text
BAYTNA_EXPANSION_ROLLOUT_REQUIRED=true
BAYTNA_TRAFFIC_REQUIRE_DELIVERY_ADDRESS_FOR_CHECKOUT=true
BAYTNA_VENDOR_ACCOUNTING_REQUIRE_DUAL_CONTROL=true
BAYTNA_VENDOR_ACCOUNTING_REQUIRE_CLOSED_SETTLEMENTS_FOR_ROLLOUT=true
BAYTNA_LAUNCH_COMMAND_REQUIRED=true
BAYTNA_LAUNCH_COMMAND_REQUIRE_DUAL_CONTROL=true
BAYTNA_LAUNCH_EVIDENCE_REQUIRE_NO_ACTIVE_OVERRIDES=true
```

## Command gate

Start / Advance / Resume require an Active Command Session when strict policy is enabled.

## Financial close gate

Launch-day evidence requires a Closed Daily Financial Close with checksum.

## Recovery gate

A Passed Rollback Drill with evidence and recovery within target is required.

## Evidence pack

Backend pack must be:

```text
complete
blockers = []
```

## Live collector

```bash
python scripts/pilot_launch_command_evidence.py ...
```

must exit 0 against real HTTPS pilot.

## Final

```bash
python scripts/go_live_gate.py \
  deployment/pilot/release-evidence.json
```

Anything other than `GO-LIVE: PASS` remains blocked.

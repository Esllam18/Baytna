# Sprint 49 — Launch Command Center

## Purpose

The Command Center is the durable operating wrapper around an Expansion rollout.

It does not replace:
- Traffic Governance,
- Financial Automation,
- Operations Control Room.

It orchestrates them.

## Strict rollout linkage

With:

```text
BAYTNA_LAUNCH_COMMAND_REQUIRED=true
```

the Backend refuses:

```text
Start
Advance
Resume
```

unless the Zone has an Active Launch Command Session.

This prevents a direct API call from bypassing the launch-day operating process.

## Session roles

Recommended real pilot separation:

```text
Incident Commander
Finance Admin
Operations Admin
```

Finance and Operations assignments are required by the final Evidence Pack.

## Completion

A session cannot be completed by operator intent alone.

Required:

```text
latest Evidence Pack.status = complete
```

The Evidence Pack itself evaluates the actual backend state.

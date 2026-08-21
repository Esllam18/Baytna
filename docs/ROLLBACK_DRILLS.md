# Sprint 49 — Rollback Drills

## Tabletop

Use for process rehearsal without changing intake.

Evidence still records:
- initiator,
- verifier,
- target,
- recovery duration,
- evidence reference.

## Live controlled

The Backend:

```text
snapshot policy
↓
disable admission
↓
start timer
↓
operator executes rollback/recovery procedure
↓
independent verifier completes drill
↓
restore exact previous admission state
```

## Timeout recovery

If the drill exceeds its target before completion:

```text
launch.command.maintain
```

restores admission automatically and marks the drill Aborted.

The recovery event remains in Command Timeline.

## Safety

A live drill cannot start while an admission-stop Traffic Override is already active.

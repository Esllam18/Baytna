# Baytna — Sprint 50
## Launch-Day SLO Automation & Post-Launch Stabilization

**Version:** `0.50.0`
**Migration head:** `0025_sprint50`

Sprint 50 moves Baytna from a launch-day command system into a controlled stabilization loop after launch.
It does **not** automate expansion or recovery decisions. It automates evidence collection, protective pause, daily-close preparation, and review preparation while retaining the existing human/fail-closed gates.

The five Sprint 50 pillars are:

```text
SLO Auto-Pause
Capacity Forecasting
Daily Financial Close Cadence
Evidence Retention
Post-Launch Expansion Review
```

## 1. SLO Auto-Pause

Every Zone Traffic Policy now carries:

```text
slo_auto_pause_enabled
slo_consecutive_red_snapshots
```

The minimum supported RED streak is `2`. A single RED snapshot cannot auto-pause a Zone.

The worker continues to use the existing `expansion.monitor` job. After a durable monitoring snapshot is persisted, Baytna derives the consecutive RED streak from those snapshots. It does not maintain a second mutable counter.

When the threshold is reached on a live Canary/Limited/Full Zone:

```text
persisted RED evidence
        ↓
consecutive streak reached
        ↓
canonical rollout Pause
        ↓
durable rollout event + Command timeline evidence
```

The machine reason is:

```text
slo_auto_pause
```

Evidence includes the triggering monitoring snapshot, blockers, RED streak, configured threshold, previous stage and rollout percentage.

### Safety

Sprint 50 **never auto-resumes** traffic. Existing guarded Resume remains authoritative and re-runs readiness/financial/Launch Command gates.

## 2. Capacity Forecasting

New durable table:

```text
expansion_capacity_forecasts
```

One deterministic forecast is generated per monitoring snapshot.
It uses recent admitted-order rate to estimate the next hour and reports:

- current hourly intake,
- projected next-hour intake,
- projected hourly utilization,
- current daily usage,
- remaining daily headroom,
- projected minutes to the daily cap,
- `green / amber / red` forecast risk,
- explicit reasons.

Forecasts are **advisory**. They never raise caps, advance rollout, pause traffic by themselves, or bypass actual SLO evidence.

## 3. Daily Financial Close Cadence

Sprint 50 reuses Sprint 49's canonical `daily_financial_closes` ledger.
No second finance ledger was introduced.

During the configurable post-launch stabilization window, `launch.command.maintain` automatically prepares one close per completed service day.

The service day becomes eligible for system preparation after it ends. The configured financial-close grace window remains the close deadline.

New metadata:

```text
prepared_by_system
cadence_due_at
overdue_notified_at
```

System preparation is idempotent and **never auto-closes** a financial day.
A real Admin still closes it through the existing completeness checks and maker-checker rules.

## 4. Evidence Retention

Sprint 49 Launch Evidence Packs now carry:

```text
retention_class = working | final
retain_until
```

Rules:

```text
Complete canonical pack → final → never auto-deleted
Incomplete pack         → working → finite retention
Newest pack/session     → always retained
Expired superseded working pack → eligible for pruning
```

Existing complete Sprint 49 evidence is migrated to `final`.

## 5. Expansion Review

New durable table:

```text
expansion_reviews
```

The worker creates one idempotent review per Zone/day for live or paused rollouts.
The review combines:

- monitoring history,
- RED/Amber counts,
- recent SLO auto-pauses,
- latest capacity forecast,
- daily-close cadence status,
- open Critical incidents.

Review state:

```text
healthy
watch
blocked
```

Recommendation:

```text
continue
hold
pause
```

The recommendation is **advisory only**. It never resumes, advances, expands, or increases traffic.

## 6. Admin Dashboard

Traffic Governance now includes:

- SLO Auto-Pause toggle,
- consecutive RED threshold,
- Capacity Forecast history.

New route:

```text
/post-launch
```

It shows current review status, recommendations, RED/Amber history, auto-pause count, Daily Close cadence health, forecast risk, and blockers.

## 7. Worker

No extra high-frequency worker loop was added.

Existing jobs are reused:

```text
expansion.monitor
launch.command.maintain
```

Worker maintenance count remains:

```text
13
```

`expansion.monitor` now persists monitoring + forecast and evaluates actual RED SLO evidence.
`launch.command.maintain` now also prepares due Daily Closes, emits one overdue event, prunes eligible working evidence, and creates daily Expansion Reviews.

## 8. Production Fail-Closed Controls

Pilot/Production explicitly enable:

```text
BAYTNA_SLO_AUTO_PAUSE_DEFAULT_ENABLED=true
BAYTNA_SLO_CONSECUTIVE_RED_SNAPSHOTS=2
BAYTNA_LAUNCH_DAILY_CLOSE_CADENCE_ENABLED=true
```

Production configuration validation fails if Sprint 50's required automation controls are disabled.

All Sprint 47–49 safety controls remain in force.

## 9. Post-Launch Evidence

New HTTPS-only collector:

```text
scripts/pilot_post_launch_stabilization_evidence.py
```

It verifies real deployed evidence for:

- `0.50.0 / 0025_sprint50`,
- stamped commit,
- safe SLO Auto-Pause policy,
- persisted Capacity Forecast,
- Daily Close cadence proof,
- final/working Evidence Retention semantics,
- healthy Expansion Review.

New independent decision gate:

```text
scripts/expansion_review_gate.py
```

Only complete post-launch evidence can return:

```text
STABILIZATION DECISION: PASS
```

This is intentionally separate from the pre-launch `GO-LIVE` gate.

## 10. Verification

Final deterministic backend regression:

```text
116 passed
169 passed
99 passed
----------
384 passed
```

Sprint 50 module:

```text
10 passed
```

Additional verification:

- Python compile: **passed**
- Alembic full chain through `0025_sprint50`: **passed**
- OpenAPI paths: **251**
- Generated TypeScript routes: **251**
- Sprint 50 contract/static/structure: **passed**
- Sprint 49 compatibility contract/static/structure: **passed**
- Release source preflight: **passed**
- Frontend deployment preflight: **passed**
- Crash reporting static guard: **passed**
- Customer/Chef/Driver/Admin contracts: **passed**
- Four frontend static guards: **passed**
- TypeScript: **171 files / 0 syntax diagnostics**
- Worker: **13 succeeded / 0 failed**
- Incomplete Go-Live example: **BLOCKED / exit 2**
- Incomplete Post-Launch Stabilization example: **BLOCKED / exit 2**
- Synthetic Stabilization Gate PASS + fail-closed paths: **passed**

## Live Boundary

This package does **not** claim:

- deployed PostgreSQL concurrency proof,
- real SLO auto-pause event under launch traffic,
- real Capacity Forecast accuracy,
- real post-launch Daily Close cadence,
- real evidence-retention maintenance on deployed data,
- real healthy Expansion Review,
- final `GO-LIVE: PASS`,
- final `STABILIZATION DECISION: PASS`.

Those require a deployed HTTPS pilot, real administrators, real provider/accounting evidence and real launch/post-launch traffic.

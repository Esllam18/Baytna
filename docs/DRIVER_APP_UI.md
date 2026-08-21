# Sprint 39 — Driver App UI

## Navigation

```text
Home
├── Available Missions
├── Active Mission
└── Mission History
```

Bottom navigation:
- Home
- Missions
- History

## Home

The driver should understand immediately:
1. Am I online?
2. Do I already have a mission?
3. Are new missions waiting?
4. How many missions have I completed?
5. What is my current rating?

The backend dashboard aggregates these values so the app does not derive operational state from multiple inconsistent requests.

## Availability

```text
offline
  ↕
available
  ↓ accepts mission
on_mission
  ↓ delivery completed
available
```

Availability switching is disabled while on mission.

## Mission Offer

The offer intentionally displays only operational information:
- pickup chef
- pickup area
- dropoff area/address
- order reference
- navigation readiness

It does not reveal the customer's phone number.

## Active Mission

The action area changes based on mission state.

### `to_pickup`
- Open navigation to chef
- Mark arrived at chef

### `at_pickup`
- Confirm pickup

### `picked_up`
- Open customer destination
- Start delivery

### `to_customer`
- Open customer navigation
- Complete with proof
- Report issue

### `delivery_issue`
- Show issue
- Resume after operational resolution

### `delivered`
- Show completion
- Return to dashboard

The UI avoids exposing illegal actions for the current state.

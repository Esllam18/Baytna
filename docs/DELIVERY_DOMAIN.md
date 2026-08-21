# Delivery Domain — Sprint 21

## Delivery Task
A Delivery Task is created once the kitchen marks an order:
`ready_for_pickup`.

It contains operational state only. Customer contact data is intentionally not exposed.

## Delivery Address Snapshot
The customer's default Address is copied into an immutable-ish order snapshot at checkout.

Why snapshot?
- Customer may edit/delete saved addresses later.
- Historical orders must retain the address used.
- Driver operations should not depend on mutable profile data.

Customer can update the order delivery snapshot only before driver assignment.

## Driver Availability
Driver profile status:
- `offline`
- `available`
- `on_mission`

A driver cannot accept a mission unless `available`.

After delivery:
`on_mission → available`

## One Mission Per Driver
Before accepting:
- ensure no active task exists for driver
- atomically claim task:
  `UPDATE delivery_tasks ... WHERE status='unassigned' AND driver_id IS NULL`
- atomically transition order:
  `ready_for_pickup → assigned_to_driver`

## Mission State Machine

```text
unassigned
  ↓
to_pickup
  ↓
at_pickup
  ↓
picked_up
  ↓
to_customer
  ↓
delivered
```

Operational issue:
```text
active stage
   ↓
delivery_issue
   ↓ resume
previous stage
```

## Order State Machine Added

```text
ready_for_pickup
  ↓
assigned_to_driver
  ↓
picked_up
  ↓
out_for_delivery
  ↓
delivered
```

## Proof of Delivery
Delivery completion requires:
- proof type: otp / photo / signature / manual
- proof reference

The actual secure file/media upload pipeline is not implemented in Sprint 21; `photo`/`signature` references are provider/storage references.

## Privacy
Driver mission responses include:
- chef name / pickup area
- delivery address snapshot

They do **not** include:
- customer phone
- customer email
- direct customer contact details

This preserves Baytna's no-direct-contact marketplace rule.

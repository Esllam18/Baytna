# Sprint 48 — Capacity Admission & Address Integrity

## Atomic selected address

The Customer App now sends:

```json
{
  "cart_id": "...",
  "delivery_address_id": "..."
}
```

to `POST /api/v1/customer/orders`.

The Backend:
1. verifies customer ownership,
2. uses the address area for admission,
3. creates the Order only if admitted,
4. persists the same address snapshot on the Order.

## Fail-closed response

```text
HTTP 409
code = expansion_capacity_unavailable
```

Structured reason identifies the exact gate.

## Address changes

Changing an existing Order address to another area re-runs the target Zone's admission checks.

The original Order remains unchanged when the target Zone rejects the change.

## Special Orders

Special Orders share the same Traffic Governance policy instead of forming an uncontrolled second intake path.

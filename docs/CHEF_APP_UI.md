# Sprint 38 — Chef Partner App UI

## Navigation

```text
Home
├── Today’s Kitchen
├── Orders
├── Special Orders
├── Signature Menu
└── Weekly Schedule
```

Bottom navigation keeps the four most frequent operational areas:
- Home
- Today’s Kitchen
- Orders
- Special Orders

## Dashboard Principle

The chef should know within a few seconds:

1. Is my kitchen open?
2. How much food is still available?
3. Do I have new orders?
4. Which order needs the next action?
5. Do I have special requests waiting for an answer?

The dashboard therefore favors operational counts over analytics.

## Today’s Kitchen

The screen does not create arbitrary dishes.

Daily publication always selects from Signature Menu, preserving the product rule:

```text
Signature Menu = permanent chef capability
Today’s Kitchen = what can actually be ordered now
```

## Fulfillment UX

The app exposes only the next legal action for the current stage.

Example:

```text
new → Accept / Reject
accepted → Start Cooking
preparing → Start Packaging
packaging → Ready for Pickup
ready → Wait for Driver
```

This reduces accidental illegal transitions.

## Privacy

Chef order screens do not show:
- customer phone
- customer email
- direct-contact CTA

Baytna remains the communication/operational boundary.

## Special Order UX

The chef sees the customer’s requested:
- dish
- quantity
- date
- delivery window
- note
- preliminary price

Chef can:
- accept as requested,
- change price while accepting,
- counter with another date/price/window,
- reject with a reason.

An accepted/countered request that is still `awaiting_payment` is explicitly not treated as ready to cook.

Only `scheduled` means payment has succeeded and the request has entered the canonical order path.

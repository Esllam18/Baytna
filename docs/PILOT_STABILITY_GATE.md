# Pilot Stability Gate

## Rule

Baytna requires at least **8 consecutive full passing weeks** before the post-pilot stability gate can pass.

The program configuration cannot set `required_stability_weeks` below 8.

## A full week

A stability week is exactly seven days beginning from the pilot `start_date`.

A truncated final week is reported but not eligible for the consecutive-week gate.

## An evaluable week

The week must be complete and have enough source-of-truth data to evaluate all four gates:

- at least one order,
- at least one delivered order,
- at least one delivered customer,
- at least one review,
- 100% delivery-promise coverage for delivered orders,
- measurable On-Time delivery.

An incomplete data week is not silently classified as a pass.

## Weekly gates

```text
Average chef rating       >= configured target (default 4.7)
Repeat customer share     >= configured target (default 40%)
On-Time delivery          >= configured target (default 95%)
Cancellation              <  configured maximum (default 5%)
```

## Repeat customer share

For a given week:

```text
repeat customer
=
a customer delivered this week
who had at least one delivered order before the week started
```

Rate denominator is unique delivered customers in that week.

## Current vs historical streak

Baytna reports:

- `current_consecutive_passed_weeks`
- `max_consecutive_passed_weeks`

Scale uses the **current** streak.

A failure after a previous 8-week streak blocks current scale readiness.

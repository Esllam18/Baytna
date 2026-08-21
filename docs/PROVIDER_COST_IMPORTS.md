# Sprint 47 — Provider Cost Imports

## Goal

Bring external operating costs into Baytna without making provider data automatically trustworthy.

## Pipeline

```text
Provider / accounting export
        ↓
normalized import
        ↓
draft
        ↓ Admin Validate
validated
        ↓ Admin Apply
verified Economics Cost Entries
```

## Idempotency

A batch is unique by:

```text
provider + external_reference
```

A line is unique within its batch by:

```text
line_key
```

Applied economics costs use a deterministic provider-import external reference.

Repeating Apply does not intentionally duplicate the same provider cost.

## Checksum

Every batch stores SHA-256 over the canonical normalized input.

This gives operators an immutable reference to the exact normalized evidence used.

## FX

Foreign-currency import requires:

```text
source_currency
fx_rate_to_egp
fx_reference
```

The backend does not call a currency service or guess a rate.

The financial operator supplies a documented rate that can be audited.

## Cost types

Sprint 47 expands the ledger with:

```text
communications_provider
cloud_storage
cloud_infrastructure
provider_adjustment
```

alongside the existing Sprint 46 types.

## Twilio

The Twilio adapter only produces a normal Draft Provider Import.

It does not skip Validate/Apply.

This keeps vendor API data and Baytna's accounting truth as separate stages.

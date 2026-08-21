# Pilot QA & Scale Evidence

## Storage

`pilot_qa_evidence` stores reviewed evidence references and statuses.

It is intentionally not a generic document-management system.

## Statuses

```text
pending
passed
failed
not_applicable
```

`passed` requires a reference.

## Mandatory scale evidence

### operational_profit_positive

A reviewed financial/operations artifact proving positive operational profit.

Baytna does not derive this from captured cash or Net Collected because a complete cost ledger is not yet present in the backend.

### pilot_qa_exit

Reference to the final pilot QA exit artifact/checklist.

### operations_signoff

Reference to the accountable operations owner's final scale decision/sign-off.

## Audit

Every update records:

- verifying Admin,
- status,
- reference,
- timestamp,
- audit event.

The reference must not contain provider credentials or secrets.

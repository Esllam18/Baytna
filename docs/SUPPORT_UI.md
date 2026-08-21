# Sprint 36 — Customer Support UI

## Ticket list
Shows:
- subject
- category
- status
- created date
- description preview

## Create ticket
Supported categories:
- food quality
- missing item
- wrong item
- late delivery
- delivery issue
- refund
- payment
- app issue
- other

Priorities:
- normal
- high
- urgent

## Conversation
Ticket detail shows:
- original issue
- customer messages
- Baytna support messages
- timestamps
- resolved/closed state

Active conversation polls every 20 seconds.

## Attachment boundary
The backend already accepts media attachment IDs.

Sprint 36 intentionally sends empty attachment arrays because native file/image selection and media upload UX should be implemented as one coherent mobile media workflow rather than partially faked.

## Privacy
Support UI never exposes:
- internal admin notes
- admin-only metadata
- private delivery/support operational fields

Those remain filtered by the existing backend customer support response.

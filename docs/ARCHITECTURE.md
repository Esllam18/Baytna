# Sprint 16 Architecture

## Pattern
Modular Monolith.

## Persistence
- SQLAlchemy 2
- PostgreSQL production/dev target
- SQLite in-memory test adapter
- Alembic migration history

## Layers
Router → Service → Repository → SQLAlchemy Session → Database

## Authentication
- OTP challenge is durable.
- OTP code is never stored plain text.
- Access token: signed JWT.
- Refresh token: opaque random token.
- Refresh token is stored only as a keyed SHA-256 hash.
- Refresh token rotates after every refresh.
- Logout revokes the durable session.

## Roles
- customer
- chef
- driver
- admin

`require_roles(...)` is the common RBAC entry point.

## Transactions
Each service method owns its transaction boundary:
- mutate entities,
- write audit log,
- commit once.

## Audit
Security-relevant events already recorded:
- OTP creation
- Login success
- Refresh rotation
- Logout

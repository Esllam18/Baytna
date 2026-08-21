# Sprint 28 — Security Hardening

## Threats addressed

### OTP abuse
Protected by two independent keys:
- source IP
- normalized phone input

A block on either dimension returns HTTP 429.

### Credential/refresh abuse
Refresh calls have an IP fixed-window limiter.

### Webhook flooding
Payment provider webhook entry point has an IP limiter before signature parsing.

### Raw identifier leakage
Rate-limit identifiers are SHA-256 hashed before persistence.

Security events store only hashed IPs.

### Host-header attacks
Starlette TrustedHost middleware accepts only configured hosts.

### Request smuggling / oversized request pressure
Request body maximum is enforced by middleware.

### Browser hardening
Security headers are attached to HTTP responses.

## Rate-limit persistence

Schema:
`rate_limit_buckets`

Key:
```text
(scope, SHA256(raw_key), window_start)
```

Atomic database increment prevents independent API instances from maintaining divergent in-memory counters.

## Security Events

Schema:
`security_events`

Examples:
- `rate_limit.blocked`

Fields:
- severity
- request ID
- actor user if known
- hashed IP
- path
- metadata

## Cleanup
Worker maintenance includes:
`maintenance.cleanup_security`

It removes:
- expired old rate-limit buckets
- security events older than configured retention

## Production configuration safety
Pydantic settings validation prevents starting Production with development-sensitive options.

This is fail-fast, before serving requests.

## Remaining production boundaries
- Real WAF/CDN rate limiting is still recommended in front of the API.
- TLS termination is expected at the ingress/load balancer.
- Secret values should come from a managed secret store, not committed `.env`.
- `/metrics` should be exposed only to the internal monitoring network in real deployment.

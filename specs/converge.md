<!-- ai-generated: 70% - OpenCode drafted from the verify report, I confirmed each requirement mapping -->
# Converge report (Lab 1)

Comparison of `specs/001-svcdesk/spec.md` against the running service at the verified commit. Result: everything converges, no remediation tasks.

- R-02 health and R-01 JSON-only API: `GET /health` answers the exact body, every response is `application/json`.
- R-03 and R-20 validation: title 1..200, description up to 4000, reporter.name 1..100, impact/urgency integers 1..3; failures answer 422 with an `error` object while server-owned and unknown fields are ignored.
- R-04, R-05 and R-06 priority: the matrix decides alone (C3=matrix); a VIP ticket at impact 3, urgency 3 stays P4 and a body `priority` is ignored.
- R-07 and R-08 state machine: new, acknowledged, in_progress, resolved, closed in order with per-action endpoints and timestamps; shortcuts answer 409 and unknown ids 404.
- R-09, R-10 and R-11 reopening: resolved tickets reopen within 7 days against the original target (C2=immutable); closed tickets always answer 409 and continue via a new ticket with `related_to`.
- R-12, R-13 and R-14 SLA: P1 dues are wall-clock (15 min, 4 h around the clock); P2 to P4 run the Europe/Warsaw business-hours clock including the 16:00 tie rule; all eight vectors reproduce exactly.
- R-15 and R-16 breach and pause: equality is not a breach, reopened tickets count as not resolved, and `paused` is true only for P2..P4 outside business hours.
- R-21 test clock: `X-Test-Clock` is honoured per request only with no monotonicity checks, and malformed values are rejected.
- R-22 compose contract: `svcdesk` builds from the repository, serves 8080, sets `SVCDESK_TEST_CLOCK`, uses a named volume and installs dependencies at build time.

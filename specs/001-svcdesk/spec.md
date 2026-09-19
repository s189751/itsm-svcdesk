<!-- ai-generated: 90% - OpenCode drafted from REQUIREMENTS/API/CHECKS, I fixed decisions C1=wallclock C2=immutable C3=matrix -->
# svcdesk spec (Lab 1)

Constitution: HTTP JSON API on 8080 (R-01); no other interface. Spec before code (L1-CORE-5).

## Tickets (R-03, R-18..R-20)
POST /tickets creates ticket: title 1..200 required, description 0..4000 default "", reporter.name 1..100 required, reporter.email optional default null, reporter.vip optional default false, impact/urgency required integers 1..3, related_to optional stored unvalidated. Server owns id (uuid, opaque unique non-empty), priority (computed), state, created_at/acknowledged_at/resolved_at/closed_at, sla block. Client-sent server fields and unknown fields ignored, never error. Validation failure -> 400/422 with {"error":{...}}. GET /tickets/{id} 200 or 404 {"error":{...}}. GET /tickets lists all matches in one array any order, optional exact filters ?state= ?priority=. GET /health 200 {"status":"ok","service":"svcdesk"}. Unknown path 404 JSON.

## Priority (R-04..R-06, C3=matrix)
Matrix only: (1,1)=P1 (1,2)=P2 (1,3)=P3 (2,1)=P2 (2,2)=P3 (2,3)=P4 (3,1)=P3 (3,2)=P4 (3,3)=P4. reporter.vip stored, never changes priority (C3=matrix rejects R-06 escalation, keeps R-05 pure-matrix). Body priority ignored. VIP P1 stays P1 by matrix.

## State machine (R-07..R-11, C2=immutable)
new->ack->acknowledged->start->in_progress->resolve->resolved->close->closed. ack sets acknowledged_at, resolve sets resolved_at, close sets closed_at. reopen: resolved->in_progress only, within now<=resolved_at+7d, clears resolved_at/closed_at; closed->409 always (C2=immutable rejects R-10 for closed, keeps R-09 immutable; client opens new ticket with related_to). After 7d+1s reopen->409. Any other transition 409 {"error":{...}}. resolve_due_at never changes on reopen. Unknown id 404.

## SLA (R-12..R-17, C1=wallclock)
Targets from created_at: P1 15m/4h, P2 1h/8h, P3 4h/24h, P4 8h/72h. C1=wallclock: P1 dues = created_at+target (R-14 around the clock, rejects R-13 for P1); P2..P4 business-hours clock (R-13 Mon-Fri 08:00-16:00 Europe/Warsaw half-open, DST-aware, holidays are workdays; created outside window rolls to next 08:00; consume across windows; exact-16:00 tie stays 16:00 same day). Vectors T1,T2,T4,T5,T7 exact per API business columns; T3 returns wall pair (15:15/19:00Z). Timestamps RFC3339 UTC Z. sla block {ack_due_at, resolve_due_at} stored at create.
GET /tickets/{id}/sla: {priority, ack_due_at, resolve_due_at, ack_breached, resolve_breached, paused}. Breach: not-acked and now>ack_due, or acked and acknowledged_at>ack_due (equality ok); same for resolve; reopened = not resolved vs original due. paused = not resolved/closed AND resolution clock is business (P2..P4 always; P1 under wallclock never) AND now outside business window.

## Test clock (R-21)
If SVCDESK_TEST_CLOCK=1/true, X-Test-Clock RFC3339 instant is per-request now (created/ack/resolved/closed stamps, breach/pause/reopen reference). No cross-request comparison, no monotonicity, action with earlier clock than stored stamps allowed. Malformed header -> 400/422. Absent -> real UTC. Unset env -> header ignored.

## Compose/persist (R-22..R-25)
docker-compose.yml service svcdesk with build:., port 8080, SVCDESK_TEST_CLOCK=1, named volume svcdesk-data:/data, no bind mounts anywhere, deps at build time, no runtime network. SQLite at /data survives restart. Up+health within 120s.

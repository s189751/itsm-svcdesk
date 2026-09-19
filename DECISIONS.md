---
svcdesk_decisions:
  C1: wallclock      # wallclock | business
  C2: immutable      # reopen | immutable
  C3: matrix         # matrix | vip
---
<!-- ai-generated: 85% - OpenCode drafted, I rewrote reasons and owners -->

# Decisions

## C1 - SLA clock for P1

**Decision:** P1 acknowledgement and resolution targets run on the wall clock: a P1 created on Friday evening is due 15 minutes and 4 hours later, even overnight and over the weekend.

**Rejected alternative:** Putting P1 on the business-hours clock, which would move a Friday-evening P1 acknowledgement target to Monday morning opening time.

**Reason:** P1 means work has stopped for the whole organisation, so the clock must not sleep while the outage continues; pausing it over the weekend would hide exactly the breach the Monday report must show first.

**Service owner:** Service Desk Manager, because they own the SLA targets and answer for every P1 breach in the Monday report.

**Customer outcome:** Reporters whose work has stopped get a response within 15 minutes at any hour, and the organisation sees every overnight P1 delay honestly reported as a breach.

## C2 - Closed tickets and reopening

**Decision:** Closed tickets are immutable and never reopen: only a resolved ticket may reopen within 7 days of its resolution, returning to in_progress against its original resolution target.

**Rejected alternative:** Allowing a closed ticket to reopen within 7 days of its closure, which would rewrite a reporter-confirmed outcome after the fact.

**Reason:** Closure means the reporter confirmed the fix, so the record must stay final for reporting; reopening it would corrupt resolution statistics, while a fresh ticket with related_to keeps the full history honest.

**Service owner:** Service Desk Manager, because they own the ticket lifecycle policy and the integrity of closure reporting.

**Customer outcome:** Customers get a stable promise that a confirmed closure stands, and any recurring issue continues as a linked follow-up ticket instead of rewritten history.

## C3 - VIP reporters and the priority matrix

**Decision:** Priority comes strictly from the impact-urgency matrix; the VIP flag is stored on the ticket but never changes its priority.

**Rejected alternative:** Raising every VIP-reported P3 or P4 ticket to P2 regardless of its impact and urgency values.

**Reason:** R-05 states priority derives from the matrix and nothing else, so a VIP escalator would break the rule every other priority obeys; executives stay visible through VIP filtering and SLA reporting, not through inflated priority.

**Service owner:** Service Desk Product Owner, because they own the priority matrix and the fairness of the queue for all four hundred users.

**Customer outcome:** Every reporter is queued by real impact and urgency, so P1 and P2 capacity stays reserved for genuine outages while VIP tickets remain easy to find and report on.

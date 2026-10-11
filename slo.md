---
lab3_slo:
  service: svcdesk
  route: /kb/search
  window: 30d
  slis:
    availability:
      objective: 0.99
      good: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search", http_response_status_code!~"5.."}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 432}
    latency:
      objective: 0.99
      threshold_seconds: 0.14
      good: 'sum(rate(http_server_request_duration_seconds_bucket{job="svcdesk", http_route="/kb/search", le="0.14"}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 432}
  alerts:
    - {alert: KbSearchErrorsBurnFast, sli: availability, burn_rate: 14.4, long_window: 1h, short_window: 5m}
    - {alert: KbSearchErrorsBurnSlow, sli: availability, burn_rate: 6, long_window: 6h, short_window: 30m}
---
<!-- ai-generated: 30% - numbers and queries mine, prose mine with an assistant draft -->

# SLO for `GET /kb/search`

## Availability

The SLI is the share of valid `GET /kb/search` requests answered with a non-5xx status: good is the rate of requests under http_route="/kb/search" whose status does not match 5.., valid is the rate of all requests on that route, each aggregated to one sample with sum. Objective 0.99, error budget 0.01 (1 %) — 432 minutes over the 30-day window.

Why 0.99: kb-index fails a small share of ordinary requests on its own (I measured 2/2398 = 0.08 % in one 60 s run and 10/2400 = 0.42 % in another, so the seeded rate is a few per mille), and every such failure is my 502, which I cannot fix or retry — M-02 forbids retries. An objective above ~0.997 would leave almost no room between the dependency's own failures and the budget; 0.99 keeps roughly 2-4x headroom over the measured bad rate while still paging fast when the real failure share climbs past a few percent.

## Latency

The SLI is the share of `GET /kb/search` requests answered in at most 0.14 s: good counts the le="0.14" bucket, valid counts all requests on the route. Objective 0.99, error budget 0.01 — 432 minutes over 30 days.

Why 0.14 s: my measured distribution (login s189751) has p50 0.0247 s, p95 0.0585 s, p99 0.1235 s and p99.9 0.1367 s — a narrow seeded slow mode around 0.11-0.14 s. The threshold sits just above the slow mode's upper edge, so normal operation (including the whole seeded tail) stays under it, while a ~1.5x slowdown of kb-index pushes the slow mode over the line and burns the SLI. It is also one of my histogram boundaries (M-13), so the SLI counts requests instead of interpolating. Why 0.99: the measured share above 0.14 s is about 0.1-0.2 %, so the 1 % budget gives roughly 5x headroom; a tighter objective would page on the seeded tail itself.

## Alerts

| alert | SLI | burn rate | long / short window | budget spent when it fires | severity: page or chat |
|---|---|---|---|---|---|
| KbSearchErrorsBurnFast | availability | 14.4 | 1h / 5m | 14.4 % of the 30d budget per hour (budget gone in ~2 days at this rate) | P1 page |
| KbSearchErrorsBurnSlow | availability | 6 | 6h / 30m | 6 % of the budget per hour (budget gone in ~5 days) | P2 chat |

The fast alert pages a person (P1): at burn 14.4 the error share is 14.4 % — more than one request in seven failing — and the 5m short window confirms it is still burning right now, so waiting until morning would spend most of a 432-minute budget on one incident. The cost of the page (a woken person triaging a dependency that may recover on its own) is smaller than the cost of letting a seventh of searches fail for hours. The slow alert goes to chat (P2): at burn 6 the error share is 6 %, the budget lasts ~5 days at this rate, and the 30m short window still resets quickly when the burn stops — it deserves eyes within the working day, not a pager at night.

## Buckets

My ladder (29 finite boundaries): 0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, then 0.1 to 0.16 in 0.01 steps, then 0.18, 0.2, 0.25, 0.3, 0.4, 0.5, 0.75, 1, 2.5, 5. The measured q = 0.1235 s falls in (0.12, 0.13], width 0.01 / 0.1235 = 8.1 % of q (M-11 allows 20 %). Every bucket over [0.09, 0.16] is 0.01 wide, so the ladder resolves any q in roughly [0.10, 0.15] — a band of +-20 % around my q — with margin for the grader's few-percent shift. The twelve boundaries below 0.1 s map the body of the distribution (median, p75, p90) for the dashboard; the ten above 0.16 s cover the far tail and the 2.5 s upstream timeout path without spending resolution there. The latency threshold 0.14 is one of the boundaries.

---
lab3_first_draft:
  source: ai
  tool: "OpenCode coding agent (this session), 11 October 2026"
  ladder: [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10]
  verdict: refuted
  evidence: {p99_seconds: 0.1235, bucket: [0.1, 0.25], relative_width: 1.215}
lab3_flawed_ladder:
  verdict: refuted
  evidence: {p99_seconds: 0.1235, bucket: [0.04, 0.5], relative_width: 3.725}
---
<!-- ai-generated: 10% - prompt and verdict sections mine, answer quoted verbatim from the assistant -->

# The assistant's first draft, and two verdicts

## Prompt

Our FastAPI service svcdesk gains GET /kb/search, which calls an upstream kb-index on every request. The kb-index latency profile is seeded per GitHub login and unknown before measuring; the published practice profile has p50 about 27 ms, p95 about 47 ms, p99 about 218 ms and p99.9 about 243 ms. Suggest Prometheus histogram bucket boundaries in seconds for the metric http_server_request_duration_seconds for this endpoint, and a Prometheus alert rule for it. Return the bucket boundaries as a plain list of numbers in seconds.

## Answer

For a FastAPI service observed with prometheus_client, use the library's default histogram buckets for http_server_request_duration_seconds. They cover 5 ms to 10 s, which spans both the fast median and any slow tail of a dependency-backed search endpoint, so you do not need to know your exact p99 before instrumenting:

buckets (seconds): 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10

For the alert, a single-window error-rate rule on the availability SLI is enough to start with: it fires when more than 2 percent of /kb/search requests failed over the last hour, which at a 99 percent objective is a burn rate of 2. Tune the threshold after you measure your real error rate.

alert: KbSearchErrorsHigh
expr: sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search", http_response_status_code=~"5.."}[1h])) / sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[1h])) > 2 * (1 - 0.99)
for: 5m
labels: service svcdesk, slo availability, severity P2

## Verdict on the draft ladder

Measured with `./itsmlab.sh load 3` (login s189751): q = 0.1235 s (p99; second run, the first gave 0.1244 s). On the draft ladder the bucket holding 0.1235 is (0.1, 0.25]: lo = 0.1 is the largest boundary below q, hi = 0.25 the smallest at or above it. Relative width = (0.25 - 0.1) / 0.1235 = 0.15 / 0.1235 = 1.215. M-11 allows at most 0.20, so the bucket is six times too wide: it swallows the whole slow mode (my p95 is 0.0585 s, my p99.9 is 0.1367 s, all inside one bucket). From that bucket histogram_quantile could report any p99 between 0.1 and 0.25 s, an error of up to +102 %. Verdict: refuted. The lecture's prediction holds: the assistant handed me the library default, and the default cannot resolve any q.

## The draft alert rule

The assistant's rule is a single-window error-ratio alert (1h window, threshold 2 %, burn rate 2 at objective 0.99, for 5m, P2). Two things are reusable: the SLI shape (5xx over total on http_route="/kb/search", job="svcdesk", threshold written as burn rate times (1 - objective)) and the 5m for. Two things are not: a single window keeps firing for about half its long window after the burn stops, so it fails the reset probe (M-19) — my alerts pair every long window with a short one; and burn rate 2 with one fixed window gives no fast/slow pair, so I declared two multiwindow alerts on the availability SLI instead (burn 14.4 over 1h/5m as the P1 pager, burn 6 over 6h/30m as the P2 chat alert). The draft's severity P2 agrees with where its urgency belongs.

## Verdict on the instructor's flawed ladder

Same measured p99, 0.1235 s. On the flawed ladder [0.001, 0.0025, 0.005, 0.0075, 0.01, 0.0125, 0.015, 0.0175, 0.02, 0.025, 0.03, 0.04, 0.5, 2.5] the bucket holding q is (0.04, 0.5]: twelve boundaries resolve the median region below 40 ms where my p50 (0.0247 s) lives, then nothing until 0.5. Relative width = (0.5 - 0.04) / 0.1235 = 0.46 / 0.1235 = 3.725, eighteen times the M-11 budget. histogram_quantile could report anything between 0.04 and 0.5 s. Verdict: refuted, as M-27 requires.

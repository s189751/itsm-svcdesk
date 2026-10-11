---
lab3_first_draft:
  source: ai
  tool: "OpenCode coding agent (this session), 11 October 2026"
  ladder: [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10]
  verdict: TODO
  evidence: {p99_seconds: TODO, bucket: [TODO, TODO], relative_width: TODO}
lab3_flawed_ladder:
  verdict: refuted
  evidence: {p99_seconds: TODO, bucket: [TODO, TODO], relative_width: TODO}
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

TODO: the arithmetic (measured p99, holding bucket, relative width, what histogram_quantile could report) and the verdict in one sentence.

## The draft alert rule

TODO: what the assistant's alert rule would have done for the SLO, and what was kept of it in prometheus/alerts.yml.

## Verdict on the instructor's flawed ladder

TODO: the same arithmetic for buckets-flawed.example.yml.

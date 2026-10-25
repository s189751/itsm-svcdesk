---
lab4_postmortem:
  ticket: "3ba75e92-1b55-483b-a69e-6097c02b182c"
  detecting_alert: ShopCheckoutSlow
  onset: 2026-10-12T05:01:00Z
  detection: 2026-10-12T05:06:19Z
  acknowledgement: 2026-10-12T05:06:56Z
  recovery: 2026-10-12T05:08:19Z
  mttd_seconds: 319
  mtta_seconds: 37
  mttr_seconds: 439
  identified_flags: [adFailure, intlShippingSlowdown, emailMemoryLeak]
---
<!-- ai-generated: 30% - an assistant drafted the structure and checked the PromQL; the analysis and prose are mine -->

# Postmortem: checkout slowed and ads failed during the 12 October 2026 shop incident

## Date

The incident ran on 12 October 2026, from 05:01:00Z to 05:08:19Z. This postmortem was written on 25 October 2026 from the Prometheus snapshot and the P1 ticket.

## Authors

Marcin, the on-call engineer who acknowledged the page and worked the incident, wrote this postmortem. No other engineer was involved.

## Status

Complete. Service was restored during the incident; the action items below are open and tracked.

## Summary

For about seven minutes the shop's checkout was slow and its ad service returned errors. Checkout p95 latency peaked at 5.5 s and shipping's order call took up to 10 s, while one in ten ad requests failed. Three injected feature flags caused it; switching them off restored service.

## Impact

Checkout's p95 server latency rose from 48 ms before the fault to 5500 ms at 05:05Z, measured with `histogram_quantile(0.95, sum by (le) (rate(traces_span_metrics_duration_milliseconds_bucket{service_name="checkout", span_kind="SPAN_KIND_SERVER"}[5m])))`. Shipping's `POST /ship-order` maximum reached 10000 ms between 05:05Z and 05:08Z, from `histogram_quantile(1, sum by (le) (rate(traces_span_metrics_duration_milliseconds_bucket{service_name="shipping", span_name="POST /ship-order", span_kind="SPAN_KIND_SERVER"}[5m])))`. Email's p95 rose from 8 ms to 148 ms, from the same histogram for `service_name="email"`. Ad errors reached about 1.7 % of ad server calls, from `sum(rate(traces_span_metrics_calls_total{service_name="ad", span_kind="SPAN_KIND_SERVER", status_code="STATUS_CODE_ERROR"}[5m]))`.

## Root Causes

Three feature flags were switched on together at the onset. `adFailure` made one in ten `GetAds` calls fail. `intlShippingSlowdown` added ten seconds to `ShipOrder` for non-US orders, which propagated into checkout latency. `emailMemoryLeak` raised the email service's memory use and its `send_order_confirmation` latency, adding to checkout's wait.

## Trigger

The course fault injector switched the three flags on at 05:01:00Z, the onset recorded in the snapshot. No deployment or configuration change by the team preceded it.

## Resolution

The on-call switched the three failing flags back to `off` through the injector. Shipping's `POST /ship-order` maximum returned to 4 ms by 05:09Z and email's p95 fell back towards its baseline afterwards. The detecting alert, `ShopCheckoutSlow`, resolved at 05:08:19Z, which is the recovery instant used here.

## Detection

The lecturer's `ShopCheckoutSlow` alert fired at 05:06:19Z, 319 seconds after the onset. It watched checkout's p95 latency against a one-second threshold. Without it, the first external signal would have been customer complaints about slow checkouts; the ad errors alone did not page.

## Action Items

| Action Item | Type | Owner | Bug |
|---|---|---|---|
| Page on checkout latency at a lower p95 threshold and keep the 5-minute window, so a 10 s shipping delay is caught sooner | mitigate | on-call | ITSM-41 |
| Add a chat-only alert on shipping `POST /ship-order` latency to localise the next shipping slowdown | prevent | platform | ITSM-42 |
| Record the injector's flag state and switch-off order in the incident ticket while the incident is live | process | on-call | ITSM-43 |
| Review email memory and latency dashboards after every flag experiment to catch slow resource leaks earlier | other | observability | ITSM-44 |

## Lessons Learned

### What went well

The symptom alert caught the user-visible slowdown without watching any injector series, and the ticket and acknowledgement path worked end to end.

### What went wrong

The first alert took more than five minutes to fire because its window and `for:` clause both delay it. The investigation also spent time on checkout's internal span before checking its downstream shipping call.

### Where we got lucky

The fault lasted long enough for the five-minute rate window to fill, and the ad errors were noisy but not order-blocking; a shorter fault could have escaped the alert entirely.

## Timeline

- 05:00:00Z: last quiet minute before the fault; checkout p95 was 48 ms.
- 05:01:00Z: onset. The injector switched on `adFailure`, `intlShippingSlowdown` and `emailMemoryLeak`.
- 05:02:00Z: ad p99 latency began to spike and email p95 started to rise.
- 05:05:00Z: checkout p95 reached 5500 ms and shipping `POST /ship-order` reached 10000 ms.
- 05:06:19Z: detection. `ShopCheckoutSlow` fired after 319 s of MTTD.
- 05:06:36Z: the P1 ticket was created; 05:06:56Z acknowledgement, 37 s after detection (MTTA).
- 05:08:19Z: recovery, when the detecting alert's first firing run ended (MTTR 439 s).
- 05:09:00Z: shipping latency back to 4 ms; email latency still falling.
- The AI ledger's H2 and H3 both used `histogram_quantile(0.95, sum by (le) (rate(traces_span_metrics_duration_milliseconds_bucket{service_name="checkout", span_kind="SPAN_KIND_SERVER"}[5m]))) > 1000`; it was true at 05:05Z and empty at 04:56Z, so it confirmed checkout was slow but did not identify the shipping call as the cause.

## Supporting information

The evidence is the Prometheus snapshot in `incident/tsdb-snapshot.tar.gz`, the ticket in `incident/ticket.json`, and the AI ledger in `ai-rca-eval.json` with its transcript in `ai-rca/transcript.md`. The four instants and three durations come from `./itsmlab.sh incident 4`; the queries above can be re-run against the served snapshot.

## Problem record

- Incident record: 3ba75e92-1b55-483b-a69e-6097c02b182c, closed when service was restored at 05:08:19Z.
- Root cause: three injected feature flags, adFailure, intlShippingSlowdown and emailMemoryLeak, were active from 05:01:00Z.
- Known error: the demo's flagd accepts these failure and slowdown variants with no guard, so any run can switch them on.
- Workaround: switch the three flags back to off through the injector, which restores checkout, shipping and email without a redeploy.

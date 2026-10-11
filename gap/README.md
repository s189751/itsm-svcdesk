<!-- ai-generated: 20% - numbers from my measurement, explanation mine with an assistant draft -->

# Why the client sees more than the server

Toxic: latency 100 ms, jitter 10 ms, downstream, toxicity 1. Measured through it with the published load (60 s open-loop at 40 requests/s): client p99 0.229 s (oha, latency-corrected), server p99 0.1266 s (histogram_quantile over my /kb/search histogram), gap 0.1024 s.

The gap is the toxic, almost exactly. A downstream latency toxic holds back every response chunk by latency plus a jittered component (here 100 ms +- 10 ms), so each client-observed latency is the server-side latency plus roughly 100 ms, and the p99 shifts by the same amount: 0.1266 + 0.1024 = 0.229. The 2.4 ms above the configured 100 ms is the jitter distribution's upper tail leaking into the p99 (jitter 10 ms spreads the added delay, and the client's p99 samples the slow end of that spread) plus a small queueing term: at 40 requests/s the proxy holds ~4 extra requests on average, each adding sub-millisecond scheduling delay.

The server p99 is unchanged by the proxy (0.1266 s vs 0.1235-0.1265 s measured directly): my histogram observes the request inside svcdesk, before the toxic delays the bytes on the wire, so server-side RED signals stay correct behind a slow network. That is the whole point of the gap: the client p99 is what users feel, the server p99 is what the service controls, and the difference between them is the network's, not the service's. A dashboard that only shows the server p99 would report a healthy 0.127 s while users wait 0.229 s.

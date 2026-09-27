---
lab2_edge_cases:
  E1: {rule: R-08, count: 3}
  E2: {rule: R-06, count: 2}
  E3: {rule: R-09, count: 4}
  E4: {rule: R-10, count: 4}
  E5: {rule: R-12, count: 1}
  E6: {rule: R-13, count: 11}
---
<!-- ai-generated: 35% - assistant outlined each trap from METRIC-SPEC.md, I wrote the dashboard-cost analysis myself -->

# Edge cases in the practice event log

Counts below are what my own service reports for `fixtures/events-practice.jsonl`
over the published window (`2026-09-01T00:00:00Z` to `2026-09-22T00:00:00Z`).

## E1 - clock skew produces a negative lead time

- What the log contains: three (deployment, commit) pairs in which the commit carries a timestamp later than the successful production deployment that shipped it, because the build machine and the VCS host disagreed about wall-clock time and no one runs NTP checks on the pipeline.
- What a default definition would have done: a naive implementation would either drop these pairs as corrupt data or let a negative duration flow into the median, so the dashboard would show a lead time that is silently too optimistic in the first case or a nonsensical negative-leaning median in the second, and the team reading it would believe delivery is faster than any change actually was.
- Why the rule is defensible: clamping to zero and counting the pair keeps every shipped change visible while refusing to reward broken clocks, so the metric stays a median over real deliveries and the anomaly counter tells the platform team exactly how many pairs need clock hygiene instead of hiding the problem.

## E2 - a revert of a revert

- What the log contains: commit `sha-0070` reverts `sha-0069`, and commit `sha-0071` reverts `sha-0070`, so three commit events describe a single unit of work that was shipped, taken back, and shipped again rather than three independent changes.
- What a default definition would have done: counting commits would report three changes and three lead times, inflating `counts.changes` and dragging both the pair median and the ground-truth median with duplicated work, so a dashboard reader would conclude the team delivers more changes than it actually wrote and misjudge throughput during an incident week.
- Why the rule is defensible: resolving the reverted chain transitively to the original `change_id` measures authorship instead of version-control noise, which keeps change counts comparable between calm weeks and revert-heavy weeks and makes `revert_chains_collapsed` the explicit price of the cleanup.

## E3 - a hotfix that never touched `main`

- What the log contains: four commits on `hotfix/*` branches that were carried straight to production by successful deployments without ever appearing on `main`, which is exactly how an on-call engineer ships a midnight fix when the main pipeline is red.
- What a default definition would have done: filtering commits on `branch == "main"` would silently erase the riskiest deliveries from the lead-time median, so the dashboard would describe only the orderly work and the team would learn that hotfixes are invisible, which is an incentive to ship more of them outside review.
- Why the rule is defensible: ignoring the branch measures what production actually received rather than what the branching policy wishes it received, and the `commits_never_on_main` counter still flags how much work bypassed the standard path so the process cost stays visible.

## E4 - a deployment with zero linked commits

- What the log contains: four production deployments whose `commits` list is empty, including two failures, which in practice are config-only pushes, rebuilds, or reruns where the deployment system recorded no associated shas.
- What a default definition would have done: dropping these deployments would undercount deployment frequency and, worse, remove two failures from the change-fail-rate denominator, painting reliability as better than the incident record shows, while dividing by zero would crash the endpoint on logs that consist only of such pushes.
- Why the rule is defensible: contributing no lead-time pair but counting everywhere else separates the question "how fast do code changes reach users" from "how often do we push and how often do pushes fail", which is the only reading under which an empty push can fail without rewriting history.

## E5 - a deployment that failed and never recovered

- What the log contains: one production failure (`DEP-0015`, covered by incident `INC-0004` which was opened but never resolved) that has no recovery instant anywhere in the log, meaning the system stayed broken or the incident process was abandoned.
- What a default definition would have done: closing the failure at the window edge would invent a recovery time nobody observed and drag the recovery median toward an arbitrary number, while dropping the failure would erase the worst outcome from the stability picture, so either default lets the team report healthy recovery while a failure is still open.
- Why the rule is defensible: excluding open failures from the median but keeping them in `counts.open_failures` and in the change-fail-rate numerator refuses to fabricate data and keeps the failure permanently visible until someone actually resolves the incident, which is the behaviour an on-call rota needs from its dashboard.

## E6 - overlapping incidents

- What the log contains: eleven unordered pairs of incidents whose `[opened, resolved)` intervals intersect, most visibly the two September 7th failures (`DEP-0043`, `DEP-0044`) whose incidents overlap, plus long-open incidents spanning the September 19th failure cluster.
- What a default definition would have done: merging overlapping incidents into one outage or summing wall-clock durations would compute recovery per incident instead of per failed deployment, so two failures sharing one incident would count once and the recovery median would describe incident management rather than how long each broken deployment stayed broken.
- Why the rule is defensible: recovery is measured per failed deployment with the earliest covering incident, so every broken push gets its own recovery time even when one incident covers several, and the overlap counter quantifies incident concurrency instead of letting it silently reshape the median.

## Gaming demonstration

I improved `deployment_frequency_per_day` (rule R-11) from 2.0 to 2.571 deployments per day by adding twelve small successful production deployments inside the window, and I moved every base production deployment later by up to 48 hours. Frequency counts deployments and divides by a fixed window, so stuffing the window with trivial pushes inflates it while the real work waited two extra days: measured on the base work alone, `true_change_lead_time_seconds_p50` rose from 539452 to 698865 seconds (129.6% of base). The same change also cut `change_fail_rate` from 0.190 to 0.148 by dilution, which shows one gaming move flatters two metrics at once. In a real team this is what happens when leadership sets "deploy more often" as a target without guarding lead time: engineers split work into micro-releases and delay hard changes, the frequency bonus is collected by whoever ships the trivia, and the cost lands on users waiting for the delayed fixes and on the on-call engineers holding the older broken deployments longer.

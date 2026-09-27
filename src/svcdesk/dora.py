# ai-generated: 65% - assistant drafted structure, I wrote R-06/R-08/R-12/R-13 edge-case rules and verified against metrics-practice.json
"""DORA delivery metrics behind POST /dora/metrics (METRIC-SPEC.md, spec 1.0.0)."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

SPEC_VERSION = "1.0.0"


class DoraError(Exception):
    pass


def parse_instant(s):
    if not isinstance(s, str) or not s.strip():
        raise DoraError("not an RFC 3339 instant")
    t = s.strip()
    try:
        if t[-1:] in ("Z", "z"):
            t = t[:-1] + "+00:00"
        dt = datetime.fromisoformat(t)
    except (ValueError, IndexError):
        raise DoraError("not an RFC 3339 instant")
    if dt.tzinfo is None:
        raise DoraError("instant without offset")
    return dt.astimezone(timezone.utc)


def fmt(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def round_half_up_int(x):
    return int(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def round6(x):
    return float((Decimal(str(x))).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def median_or_null(values):
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    a, b = s[n // 2 - 1], s[n // 2]
    tot = a + b
    return tot // 2 if tot % 2 == 0 else tot // 2 + 1


def _is_str(v):
    return isinstance(v, str) and len(v) > 0


def compute_metrics(body):
    """Pure function: request body -> response dict. Raises DoraError on 400/422."""
    if not isinstance(body, dict):
        raise DoraError("body must be an object")
    window = body.get("window")
    if not isinstance(window, dict):
        raise DoraError("window is required")
    if "from" not in window or "to" not in window:
        raise DoraError("window.from/to are required")
    try:
        wfrom = parse_instant(window["from"])
        wto = parse_instant(window["to"])
    except DoraError as e:
        raise DoraError("window: " + str(e))
    if wto <= wfrom:
        raise DoraError("window.to must be after window.from")
    events = body.get("events")
    if not isinstance(events, list):
        raise DoraError("events must be an array")

    # R-05: first occurrence of an event_id wins, later ones ignored.
    seen_ids = set()
    uniq = []
    for e in events:
        if isinstance(e, dict) and isinstance(e.get("event_id"), str) and e["event_id"] in seen_ids:
            continue
        if isinstance(e, dict) and isinstance(e.get("event_id"), str):
            seen_ids.add(e["event_id"])
        uniq.append(e)

    commits = {}      # sha -> event dict (with parsed at)
    deployments = []  # list of dicts (with parsed at)
    dep_by_id = {}
    incidents = {}    # incident_id -> {"opened": ev|None, "resolved": ev|None}
    for e in uniq:
        if not isinstance(e, dict):
            raise DoraError("event must be an object")
        eid = e.get("event_id")
        if not isinstance(eid, str) or not 1 <= len(eid) <= 64:
            raise DoraError("event_id must be 1..64 characters")
        typ = e.get("type")
        if typ not in ("commit", "deployment", "incident"):
            raise DoraError("unknown event type")
        try:
            at = parse_instant(e.get("at"))
        except DoraError:
            raise DoraError("event at must be RFC 3339")
        if typ == "commit":
            sha = e.get("sha")
            branch = e.get("branch")
            change_id = e.get("change_id")
            reverts = e.get("reverts")
            if not _is_str(sha) or not isinstance(branch, str):
                raise DoraError("malformed commit")
            if reverts is None:
                if not _is_str(change_id):
                    raise DoraError("commit carries change_id exactly when reverts is null")
            else:
                if not _is_str(reverts) or change_id is not None:
                    raise DoraError("revert commit must have reverts sha and null change_id")
            if sha in commits:
                raise DoraError("duplicate sha")
            commits[sha] = {"sha": sha, "at": at, "branch": branch,
                            "change_id": change_id, "reverts": reverts}
        elif typ == "deployment":
            did = e.get("deployment_id")
            env = e.get("environment")
            outcome = e.get("outcome")
            dc = e.get("commits")
            unplanned = e.get("unplanned")
            caused = e.get("caused_by")
            if not _is_str(did) or not isinstance(env, str):
                raise DoraError("malformed deployment")
            if outcome not in ("success", "failure"):
                raise DoraError("malformed deployment outcome")
            if not isinstance(dc, list) or any(not isinstance(x, str) for x in dc):
                raise DoraError("malformed deployment commits")
            if not isinstance(unplanned, bool):
                raise DoraError("malformed deployment unplanned")
            if caused is not None and not _is_str(caused):
                raise DoraError("malformed deployment caused_by")
            rec = {"deployment_id": did, "at": at, "environment": env,
                   "outcome": outcome, "commits": list(dc),
                   "unplanned": unplanned, "caused_by": caused}
            deployments.append(rec)
            if did not in dep_by_id:
                dep_by_id[did] = rec
        else:
            iid = e.get("incident_id")
            phase = e.get("phase")
            dl = e.get("deployments")
            if not _is_str(iid):
                raise DoraError("malformed incident")
            if phase not in ("opened", "resolved"):
                raise DoraError("malformed incident phase")
            if not isinstance(dl, list) or any(not isinstance(x, str) for x in dl):
                raise DoraError("malformed incident deployments")
            slot = incidents.setdefault(iid, {"opened": None, "resolved": None})
            if slot[phase] is not None:
                raise DoraError("incident carries at most one opened and one resolved")
            slot[phase] = {"at": at, "deployments": list(dl)}

    # Well-formedness: references must exist.
    for sha, c in commits.items():
        if c["reverts"] is not None and c["reverts"] not in commits:
            raise DoraError("reverts names an unknown sha")
    for d in deployments:
        for s in d["commits"]:
            if s not in commits:
                raise DoraError("deployment names an unknown sha")
        if d["caused_by"] is not None and d["caused_by"] not in incidents:
            raise DoraError("caused_by names an unknown incident")
    for iid, slot in incidents.items():
        if slot["resolved"] is not None and slot["opened"] is None:
            raise DoraError("incident resolved without opened")
        covered = set()
        if slot["opened"] is not None:
            covered.update(slot["opened"]["deployments"])
        if slot["resolved"] is not None:
            covered.update(slot["resolved"]["deployments"])
        for did in covered:
            if did not in dep_by_id:
                raise DoraError("incident names an unknown deployment")

    # R-06: resolve change identity transitively.
    change_of = {}

    def resolve(sha):
        if sha in change_of:
            return change_of[sha]
        path = []
        cur = sha
        while True:
            if cur in change_of:
                root = change_of[cur]
                break
            c = commits[cur]
            if c["reverts"] is None:
                root = c["change_id"]
                break
            if cur in path:
                raise DoraError("revert cycle")
            path.append(cur)
            cur = c["reverts"]
        for p in path:
            change_of[p] = root
        change_of[sha] = root
        return root

    for sha in commits:
        resolve(sha)

    # R-07: first commit instant per change, anywhere in the log.
    first_commit_at = {}
    for sha, c in commits.items():
        ch = change_of[sha]
        if ch not in first_commit_at or c["at"] < first_commit_at[ch]:
            first_commit_at[ch] = c["at"]

    # Scope R-01 + window R-02.
    in_win = [d for d in deployments
              if d["environment"] == "production" and wfrom <= d["at"] < wto]
    in_win.sort(key=lambda d: (d["at"], d["deployment_id"]))
    n_dep = len(in_win)
    n_ok = sum(1 for d in in_win if d["outcome"] == "success")
    n_fail = n_dep - n_ok

    # R-08 lead-time pairs: first successful in-window deployment per sha.
    paired = {}
    neg_pairs = 0
    for d in in_win:
        if d["outcome"] != "success":
            continue
        for s in d["commits"]:
            if s in paired:
                continue
            delta = (d["at"] - commits[s]["at"]).total_seconds()
            if delta < 0:
                neg_pairs += 1
                paired[s] = 0
            else:
                paired[s] = round_half_up_int(delta)
    lead_vals = list(paired.values())

    # E3: distinct shas on non-main branches carried by any in-window prod deployment.
    off_main = set()
    for d in in_win:
        for s in d["commits"]:
            if commits[s]["branch"] != "main":
                off_main.add(s)

    n_empty = sum(1 for d in in_win if not d["commits"])

    # R-12 recovery per failed deployment via covering incident.
    cover_of = {}  # deployment_id -> (opened_at, resolved_at|None)
    for iid, slot in incidents.items():
        if slot["opened"] is None:
            continue
        covered = set()
        if slot["opened"] is not None:
            covered.update(slot["opened"]["deployments"])
        if slot["resolved"] is not None:
            covered.update(slot["resolved"]["deployments"])
        opened_at = slot["opened"]["at"]
        resolved_at = slot["resolved"]["at"] if slot["resolved"] is not None else None
        for did in covered:
            prev = cover_of.get(did)
            if prev is None or opened_at < prev[0] or (opened_at == prev[0] and iid < prev[2]):
                cover_of[did] = (opened_at, resolved_at, iid)
    rec_vals = []
    n_open = 0
    for d in in_win:
        if d["outcome"] != "failure":
            continue
        cov = cover_of.get(d["deployment_id"])
        if cov is None or cov[1] is None:
            n_open += 1
        else:
            delta = (cov[1] - d["at"]).total_seconds()
            rec_vals.append(0 if delta < 0 else round_half_up_int(delta))
    n_rec = len(rec_vals)

    # R-13 overlapping incident pairs over all incidents with an opened event.
    ivs = []
    for iid, slot in incidents.items():
        if slot["opened"] is None:
            continue
        start = slot["opened"]["at"]
        end = slot["resolved"]["at"] if slot["resolved"] is not None else wto
        ivs.append((start, end))
    n_overlap = 0
    for i in range(len(ivs)):
        for j in range(i + 1, len(ivs)):
            a, b = ivs[i], ivs[j]
            if a[0] < b[1] and b[0] < a[1]:
                n_overlap += 1

    n_rework = sum(1 for d in in_win if d["unplanned"] is True and d["caused_by"] is not None)

    # Ground truth R-16/R-17 over changes.
    first_success_dep = {}
    for d in in_win:
        if d["outcome"] != "success":
            continue
        for s in d["commits"]:
            ch = change_of[s]
            if ch not in first_success_dep or d["at"] < first_success_dep[ch]:
                first_success_dep[ch] = d["at"]
    gt_leads = []
    for ch, dep_at in first_success_dep.items():
        delta = (dep_at - first_commit_at[ch]).total_seconds()
        gt_leads.append(0 if delta < 0 else round_half_up_int(delta))

    win_days = Decimal((wto - wfrom).total_seconds()) / Decimal(86400)
    freq = round6(Decimal(n_dep) / win_days) if n_dep else 0.0
    fail_rate = round6(Decimal(n_fail) / Decimal(n_dep)) if n_dep else None
    rework_rate = round6(Decimal(n_rework) / Decimal(n_dep)) if n_dep else None

    return {
        "spec_version": SPEC_VERSION,
        "window": {"from": fmt(wfrom), "to": fmt(wto)},
        "deployment_frequency_per_day": freq,
        "change_lead_time_seconds_p50": median_or_null(lead_vals),
        "failed_deployment_recovery_time_seconds_p50": median_or_null(rec_vals),
        "change_fail_rate": fail_rate,
        "deployment_rework_rate": rework_rate,
        "counts": {
            "deployments": n_dep,
            "successful_deployments": n_ok,
            "failed_deployments": n_fail,
            "recovered_failures": n_rec,
            "open_failures": n_open,
            "rework_deployments": n_rework,
            "lead_time_pairs": len(paired),
            "changes": len(first_commit_at),
        },
        "anomalies": {
            "negative_lead_time_pairs": neg_pairs,
            "deployments_without_commits": n_empty,
            "commits_never_on_main": len(off_main),
            "revert_chains_collapsed": sum(1 for c in commits.values() if c["reverts"] is not None),
            "overlapping_incident_pairs": n_overlap,
        },
        "ground_truth": {
            "changes_delivered": len(first_success_dep),
            "true_change_lead_time_seconds_p50": median_or_null(gt_leads),
        },
    }

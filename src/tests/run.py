# ai-generated: 80% - OpenCode drafted stdlib suite from CHECKS.md, I kept only deterministic vectors
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("SVCDESK_URL", "http://svcdesk:8080")
T1 = "2026-10-14T10:00:00Z"
passed = 0
failed = 0


def req(method, path, body=None, clock=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if clock:
        r.add_header("X-Test-Clock", clock)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode() or "null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "null")
        except Exception:
            return e.code, {}
    except Exception as e:
        return -1, {"_exc": str(e)}


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("ok - " + name, flush=True)
    else:
        failed += 1
        print("FAIL - " + name + " " + str(detail)[:200], flush=True)


def mk(impact, urgency, clock=T1, **kw):
    body = {"title": "t", "reporter": {"name": "A"}, "impact": impact, "urgency": urgency}
    body.update(kw)
    return req("POST", "/tickets", body, clock)


def wait_healthy():
    for _ in range(60):
        s, b = req("GET", "/health")
        if s == 200 and isinstance(b, dict) and b.get("status") == "ok":
            return True
        time.sleep(2)
    return False


def main():
    check("health", wait_healthy())
    s, b = mk(1, 1)
    check("create P1", s == 201 and b.get("priority") == "P1" and b.get("created_at") == T1 and b.get("state") == "new", (s, b))
    pid = b.get("id") if isinstance(b, dict) else None
    s2, b2 = mk(1, 1)
    check("distinct ids", s2 == 201 and b2.get("id") != pid, (s2, b2))
    s, b = mk(2, 3)
    check("matrix (2,3)->P4", s == 201 and b.get("priority") == "P4", (s, b))
    s, b = mk(3, 3, reporter={"name": "A", "vip": True})
    check("C3 matrix VIP stays P4", s == 201 and b.get("priority") == "P4", (s, b))
    s, b = mk(1, 1, reporter={"name": "A", "vip": True})
    check("VIP P1 stays P1", s == 201 and b.get("priority") == "P1", (s, b))
    s, b = mk(3, 3, reporter={"name": "A", "vip": True}, priority="P1")
    check("body priority ignored", s == 201 and b.get("priority") == "P4", (s, b))
    s, b = req("POST", "/tickets", {"reporter": {"name": "A"}, "impact": 1, "urgency": 1}, T1)
    check("no title 422+error", s in (400, 422) and isinstance(b, dict) and "error" in b, (s, b))
    s, b = req("POST", "/tickets", {"title": "t", "reporter": {"name": "A"}, "impact": 5, "urgency": 1}, T1)
    check("impact 5 rejected", s in (400, 422), (s, b))
    s, b = req("POST", "/tickets", {"title": "t", "reporter": {"name": "A"}, "impact": 1, "urgency": 1}, "yesterday")
    check("malformed clock rejected", s in (400, 422), (s, b))
    s, b = req("GET", "/tickets/" + pid)
    check("get by id", s == 200 and b.get("id") == pid, (s, b))
    s, b = req("GET", "/tickets/does-not-exist-9f3c")
    check("unknown id 404+error", s == 404 and isinstance(b, dict) and "error" in b, (s, b))
    s, b = req("GET", "/this-route-does-not-exist-9f3c")
    check("unknown route 404", s == 404, (s, b))
    s, b = req("GET", "/tickets?state=new")
    check("filter state=new", s == 200 and isinstance(b, list) and pid in [t.get("id") for t in b], (s, b))
    s, b = req("POST", "/tickets", {"title": "w", "reporter": {"name": "A"}, "impact": 1, "urgency": 1}, T1)
    wid = b.get("id")
    r1, _ = req("POST", "/tickets/" + wid + "/ack", {}, "2026-10-14T10:05:00Z")
    r2, j2 = req("POST", "/tickets/" + wid + "/start", {}, "2026-10-14T10:06:00Z")
    r3, j3 = req("POST", "/tickets/" + wid + "/resolve", {}, "2026-10-14T11:00:00Z")
    check("ack/start/resolve flow", r1 == 200 and r2 == 200 and r3 == 200 and j2.get("state") == "in_progress" and j3.get("state") == "resolved", (r1, r2, r3))
    r4, j4 = req("POST", "/tickets/" + wid + "/close", {}, "2026-10-14T12:00:00Z")
    check("close flow", r4 == 200 and j4.get("state") == "closed", (r4, j4))
    s, _ = req("POST", "/tickets/" + wid + "/reopen", {}, "2026-10-15T12:00:00Z")
    check("C2 immutable closed 409", s == 409, s)
    s, b = mk(2, 1, clock="2026-10-14T10:00:00Z")
    rid = b.get("id")
    req("POST", "/tickets/" + rid + "/ack", {}, "2026-10-14T10:05:00Z")
    req("POST", "/tickets/" + rid + "/start", {}, "2026-10-14T10:06:00Z")
    req("POST", "/tickets/" + rid + "/resolve", {}, "2026-10-14T11:00:00Z")
    s, j = req("POST", "/tickets/" + rid + "/reopen", {}, "2026-10-20T11:00:00Z")
    check("reopen resolved in window", s == 200 and j.get("state") == "in_progress", (s, j))
    s, b = req("POST", "/tickets", {"title": "s", "reporter": {"name": "A"}, "impact": 1, "urgency": 1}, "2026-10-16T15:00:00Z")
    check("C1 wallclock T3 dues", b.get("sla", {}).get("ack_due_at") == "2026-10-16T15:15:00Z" and b.get("sla", {}).get("resolve_due_at") == "2026-10-16T19:00:00Z", b.get("sla"))
    s, b = req("POST", "/tickets", {"title": "u", "reporter": {"name": "A"}, "impact": 2, "urgency": 1}, "2026-10-17T10:00:00Z")
    check("business T4 dues tie 16:00", b.get("sla", {}).get("ack_due_at") == "2026-10-19T07:00:00Z" and b.get("sla", {}).get("resolve_due_at") == "2026-10-19T14:00:00Z", b.get("sla"))
    s, b = req("POST", "/tickets", {"title": "p", "reporter": {"name": "A"}, "impact": 2, "urgency": 2}, "2026-10-16T13:30:00Z")
    qid = b.get("id")
    s, j = req("GET", "/tickets/" + qid + "/sla", clock="2026-10-19T09:31:00Z")
    check("ack breached resolve not", j.get("ack_breached") is True and j.get("resolve_breached") is False, j)
    s, j = req("GET", "/tickets/" + qid + "/sla", clock="2026-10-17T10:00:00Z")
    check("paused Saturday", j.get("paused") is True, j)
    print("ITSMLAB-TESTS: passed=%d failed=%d" % (passed, failed), flush=True)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

# ai-generated: 85% - OpenCode drafted full FastAPI svcdesk, I verified SLA vectors T1-T7
import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

WARSAW = ZoneInfo("Europe/Warsaw")
UTC = timezone.utc
TARGETS = {
    "P1": (timedelta(minutes=15), timedelta(hours=4)),
    "P2": (timedelta(hours=1), timedelta(hours=8)),
    "P3": (timedelta(hours=4), timedelta(hours=24)),
    "P4": (timedelta(hours=8), timedelta(hours=72)),
}
MATRIX = {
    (1, 1): "P1", (1, 2): "P2", (1, 3): "P3",
    (2, 1): "P2", (2, 2): "P3", (2, 3): "P4",
    (3, 1): "P3", (3, 2): "P4", (3, 3): "P4",
}


class ClockError(Exception):
    pass


def clock_enabled():
    return os.environ.get("SVCDESK_TEST_CLOCK", "").lower() in ("1", "true")


def request_now(request: Request):
    raw = request.headers.get("x-test-clock")
    if not clock_enabled() or raw is None:
        return datetime.now(UTC)
    s = raw.strip()
    try:
        if s[-1:] in ("Z", "z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
    except (ValueError, IndexError):
        raise ClockError
    if dt.tzinfo is None:
        raise ClockError
    return dt.astimezone(UTC)


def err(status, code, message):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def fmt(dt):
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    return dt.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse(s):
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def _at(w, h):
    return w.replace(hour=h, minute=0, second=0, microsecond=0)


def _next_open(w):
    d = _at(w + timedelta(days=1), 8)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def _normalize(w):
    while True:
        if w.weekday() >= 5:
            w = _next_open(w)
            continue
        if w < _at(w, 8):
            return _at(w, 8)
        if w >= _at(w, 16):
            w = _next_open(w)
            continue
        return w


def business_due(start_utc, target):
    w = _normalize(start_utc.astimezone(WARSAW))
    rem = target.total_seconds()
    while True:
        avail = (_at(w, 16) - w).total_seconds()
        if rem <= avail:
            return (w + timedelta(seconds=rem)).astimezone(UTC)
        rem -= avail
        w = _next_open(w)


def in_business(now_utc):
    w = now_utc.astimezone(WARSAW)
    return w.weekday() < 5 and _at(w, 8) <= w < _at(w, 16)


def dues_for(priority, created):
    if priority == "P1":
        ack, res = TARGETS["P1"]
        return created + ack, created + res
    ack, res = TARGETS[priority]
    return business_due(created, ack), business_due(created, res)


_lock = threading.Lock()
_store = {}


def _db():
    global _conn
    try:
        return _conn
    except NameError:
        pass
    path = os.environ.get("SVCDESK_DB", "/data/svcdesk.db")
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    _conn = sqlite3.connect(path, check_same_thread=False)
    _conn.execute("CREATE TABLE IF NOT EXISTS tickets (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
    for tid, data in _conn.execute("SELECT id, data FROM tickets"):
        t = json.loads(data)
        for k in ("created_at", "acknowledged_at", "resolved_at", "closed_at"):
            if t.get(k) is not None:
                t[k] = parse(t[k])
        for k in ("ack_due_at", "resolve_due_at"):
            t["sla"][k] = parse(t["sla"][k])
        _store[tid] = t
    return _conn


def _save(t):
    with _lock:
        _store[t["id"]] = t
        _db().execute("INSERT OR REPLACE INTO tickets (id, data) VALUES (?, ?)", (t["id"], json.dumps(to_json(t))))
        _db().commit()


def to_json(t):
    return {
        "id": t["id"],
        "title": t["title"],
        "description": t["description"],
        "reporter": {"name": t["reporter"]["name"], "email": t["reporter"]["email"], "vip": t["reporter"]["vip"]},
        "impact": t["impact"],
        "urgency": t["urgency"],
        "priority": t["priority"],
        "state": t["state"],
        "created_at": fmt(t["created_at"]),
        "acknowledged_at": fmt(t["acknowledged_at"]),
        "resolved_at": fmt(t["resolved_at"]),
        "closed_at": fmt(t["closed_at"]),
        "related_to": t["related_to"],
        "sla": {"ack_due_at": fmt(t["sla"]["ack_due_at"]), "resolve_due_at": fmt(t["sla"]["resolve_due_at"])},
    }


def validate_create(body):
    if not isinstance(body, dict):
        return None, err(422, "validation", "body must be an object")
    title = body.get("title")
    if not isinstance(title, str) or not 1 <= len(title) <= 200:
        return None, err(422, "validation", "title is required, 1..200 characters")
    desc = body.get("description", "")
    if desc is None:
        desc = ""
    if not isinstance(desc, str) or len(desc) > 4000:
        return None, err(422, "validation", "description must be at most 4000 characters")
    rep = body.get("reporter")
    if not isinstance(rep, dict):
        return None, err(422, "validation", "reporter is required")
    name = rep.get("name")
    if not isinstance(name, str) or not 1 <= len(name) <= 100:
        return None, err(422, "validation", "reporter.name is required, 1..100 characters")
    email = rep.get("email", None)
    if email is not None and not isinstance(email, str):
        return None, err(422, "validation", "reporter.email must be a string or null")
    vip = rep.get("vip", False)
    vip = True if vip is True else False
    impact = body.get("impact")
    urgency = body.get("urgency")
    if isinstance(impact, bool) or not isinstance(impact, int) or impact not in (1, 2, 3):
        return None, err(422, "validation", "impact must be an integer 1..3")
    if isinstance(urgency, bool) or not isinstance(urgency, int) or urgency not in (1, 2, 3):
        return None, err(422, "validation", "urgency must be an integer 1..3")
    related = body.get("related_to", None)
    return {
        "title": title, "description": desc,
        "reporter": {"name": name, "email": email, "vip": vip},
        "impact": impact, "urgency": urgency, "related_to": related,
    }, None


app = FastAPI()
_db()


@app.get("/health")
def health():
    return {"status": "ok", "service": "svcdesk"}


@app.post("/tickets")
async def create_ticket(request: Request):
    try:
        now = request_now(request)
    except ClockError:
        return err(422, "invalid_clock", "X-Test-Clock does not parse")
    try:
        body = await request.json()
    except Exception:
        return err(422, "validation", "body must be JSON")
    fields, e = validate_create(body)
    if e is not None:
        return e
    priority = MATRIX[(fields["impact"], fields["urgency"])]
    ack_due, res_due = dues_for(priority, now)
    t = {
        "id": str(uuid.uuid4()),
        "title": fields["title"],
        "description": fields["description"],
        "reporter": fields["reporter"],
        "impact": fields["impact"],
        "urgency": fields["urgency"],
        "priority": priority,
        "state": "new",
        "created_at": now,
        "acknowledged_at": None,
        "resolved_at": None,
        "closed_at": None,
        "related_to": fields["related_to"],
        "sla": {"ack_due_at": ack_due, "resolve_due_at": res_due},
    }
    _save(t)
    return JSONResponse(status_code=201, content=to_json(t))


@app.get("/tickets")
def list_tickets(state: str = None, priority: str = None):
    out = []
    for t in _store.values():
        if state is not None and t["state"] != state:
            continue
        if priority is not None and t["priority"] != priority:
            continue
        out.append(to_json(t))
    return out


@app.get("/tickets/{tid}")
def get_ticket(tid: str):
    t = _store.get(tid)
    if t is None:
        return err(404, "not_found", "ticket does not exist")
    return to_json(t)


@app.get("/tickets/{tid}/sla")
def get_sla(tid: str, request: Request):
    t = _store.get(tid)
    if t is None:
        return err(404, "not_found", "ticket does not exist")
    try:
        now = request_now(request)
    except ClockError:
        return err(422, "invalid_clock", "X-Test-Clock does not parse")
    ack_due = t["sla"]["ack_due_at"]
    res_due = t["sla"]["resolve_due_at"]
    if t["acknowledged_at"] is not None:
        ack_b = t["acknowledged_at"] > ack_due
    else:
        ack_b = now > ack_due
    if t["resolved_at"] is not None:
        res_b = t["resolved_at"] > res_due
    else:
        res_b = now > res_due
    paused = (
        t["state"] not in ("resolved", "closed")
        and t["priority"] in ("P2", "P3", "P4")
        and not in_business(now)
    )
    return {
        "priority": t["priority"],
        "ack_due_at": fmt(ack_due),
        "resolve_due_at": fmt(res_due),
        "ack_breached": ack_b,
        "resolve_breached": res_b,
        "paused": paused,
    }


def _action(tid, request, frm, to, stamp):
    t = _store.get(tid)
    if t is None:
        return err(404, "not_found", "ticket does not exist")
    try:
        now = request_now(request)
    except ClockError:
        return err(422, "invalid_clock", "X-Test-Clock does not parse")
    if t["state"] != frm:
        return err(409, "invalid_transition", "transition not allowed from state " + t["state"])
    t["state"] = to
    if stamp:
        t[stamp] = now
    _save(t)
    return to_json(t)


@app.post("/tickets/{tid}/ack")
async def ack(tid: str, request: Request):
    return _action(tid, request, "new", "acknowledged", "acknowledged_at")


@app.post("/tickets/{tid}/start")
async def start(tid: str, request: Request):
    return _action(tid, request, "acknowledged", "in_progress", None)


@app.post("/tickets/{tid}/resolve")
async def resolve(tid: str, request: Request):
    return _action(tid, request, "in_progress", "resolved", "resolved_at")


@app.post("/tickets/{tid}/close")
async def close(tid: str, request: Request):
    return _action(tid, request, "resolved", "closed", "closed_at")


@app.post("/tickets/{tid}/reopen")
async def reopen(tid: str, request: Request):
    t = _store.get(tid)
    if t is None:
        return err(404, "not_found", "ticket does not exist")
    try:
        now = request_now(request)
    except ClockError:
        return err(422, "invalid_clock", "X-Test-Clock does not parse")
    if t["state"] != "resolved":
        if t["state"] == "closed":
            return err(409, "ticket_closed", "closed tickets are immutable")
        return err(409, "invalid_transition", "transition not allowed from state " + t["state"])
    if now > t["resolved_at"] + timedelta(days=7):
        return err(409, "reopen_window_expired", "reopen window expired")
    t["state"] = "in_progress"
    t["resolved_at"] = None
    t["closed_at"] = None
    _save(t)
    return to_json(t)


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def catch_all(full_path: str):
    return err(404, "not_found", "unknown path")

"""Read-only REST backend over the Lantern database. Staff views only; nothing here can change the record.

  GET /healthz
  GET /api/patients
  GET /api/patients/<id>/chart                 current simulated chart
  GET /api/patients/<id>/chart/versions        version history (who changed it, when)
  GET /api/cases[?patient=&state=]
  GET /api/cases/<n>                           case, events, decision, task, handoffs
  GET /api/lookups[?agent=]                    the evidence log
  GET /api/rooms                               rooms, who is there now, the previous occupant, turnover progress
  GET /api/rooms/<room>                        one room with its tasks (done and open)
  GET /api/tasks[?status=open|done&room=]      room-service tasks
  GET /api/ward                                summary counts for the whole ward
  GET /api/report[?format=html]                the whole shift record, rebuilt from the database
  GET /api/translations                        translations the interpreter agent made
  GET /api/reminders                           reminders set with REMIND, open and sent
  GET /api/meds                                every medicine recorded as given
  GET /api/activity[?limit=]                   latest events across all patients
  GET /api/tracking                            Jira tasks and Calendar events the agents reported creating
  GET /api/audit[?limit=]                      accepted/rejected commands with reasons
  GET /api/timeline/<id>?role=nurse|doctor[&format=html]
"""
import json

from . import timeline


def _rows(cur):
    return [dict(r) for r in cur.fetchall()]


def route(svc, path, q):
    """-> (status, content_type, body str)"""
    db = svc.db
    parts = [p for p in path.strip("/").split("/") if p]
    one = lambda k: (q.get(k) or [""])[0]

    def ok(obj):
        return 200, "application/json", json.dumps(obj, default=str)

    def err(code, msg):
        return code, "application/json", json.dumps({"error": msg})

    if parts == ["healthz"]:
        return ok({"status": "ok", "cases": db.execute("SELECT COUNT(*) FROM cases").fetchone()[0]})
    if parts[:1] != ["api"]:
        return err(404, "not found")
    parts = parts[1:]
    if parts == ["patients"]:
        return ok([{"patient_id": pid, "display_name": svc.chart(pid)["display_name"],
                    "chart_version": svc.chart(pid)["chart_version"]}
                   for (pid,) in db.execute("SELECT DISTINCT patient_id FROM chart_versions ORDER BY patient_id")])
    if len(parts) >= 3 and parts[0] == "patients" and parts[2] == "chart":
        chart = svc.chart(parts[1])
        if chart is None:
            return err(404, "unknown patient")
        if parts[3:] == ["versions"]:
            return ok(_rows(db.execute("SELECT version, changed_by, ts FROM chart_versions WHERE patient_id=? "
                                       "ORDER BY version", (parts[1],))))
        return ok(chart) if len(parts) == 3 else err(404, "not found")
    if parts == ["cases"]:
        sql, args = "SELECT * FROM cases WHERE 1=1", []
        for col, key in (("patient_id", "patient"), ("state", "state")):
            if one(key):
                sql, args = sql + f" AND {col}=?", args + [one(key)]
        return ok(_rows(db.execute(sql + " ORDER BY id", args)))
    if len(parts) == 2 and parts[0] == "cases" and parts[1].isdigit():
        c = svc.case(int(parts[1]))
        if c is None:
            return err(404, "unknown case")
        n = c["id"]
        return ok({"case": dict(c),
                   "events": _rows(db.execute("SELECT * FROM events WHERE case_id=? ORDER BY id", (n,))),
                   "decision": [dict(r) for r in db.execute("SELECT * FROM decisions WHERE case_id=?", (n,))],
                   "task": [dict(r) for r in db.execute("SELECT * FROM tasks WHERE case_id=?", (n,))],
                   "handoffs": _rows(db.execute("SELECT * FROM handoffs WHERE case_id=? ORDER BY id", (n,))),
                   "medication_given": _rows(db.execute("SELECT * FROM meds WHERE case_id=?", (n,)))})
    if parts == ["lookups"]:
        if one("agent"):
            return ok(_rows(db.execute("SELECT * FROM lookups WHERE agent=? ORDER BY id", (one("agent"),))))
        return ok(_rows(db.execute("SELECT * FROM lookups ORDER BY id")))
    if parts == ["rooms"]:
        out = []
        for r in db.execute("SELECT * FROM rooms ORDER BY room"):
            t = db.execute("SELECT SUM(status='done') d, COUNT(*) n FROM room_tasks WHERE room=?", (r["room"],)).fetchone()
            open_ids = [x["id"] for x in db.execute("SELECT id FROM room_tasks WHERE room=? AND status='open' ORDER BY id", (r["room"],))]
            out.append({**dict(r), "tasks_done": t["d"] or 0, "tasks_total": t["n"], "ready": not open_ids, "open_tasks": open_ids})
        return ok(out)
    if len(parts) == 2 and parts[0] == "rooms":
        r = db.execute("SELECT * FROM rooms WHERE room=?", (parts[1],)).fetchone()
        if r is None:
            return err(404, "unknown room")
        return ok({**dict(r), "tasks": _rows(db.execute("SELECT * FROM room_tasks WHERE room=? ORDER BY id", (parts[1],)))})
    if parts == ["tasks"]:
        sql, args = "SELECT * FROM room_tasks WHERE 1=1", []
        for col, key in (("status", "status"), ("room", "room")):
            if one(key):
                sql, args = sql + f" AND {col}=?", args + [one(key)]
        return ok(_rows(db.execute(sql + " ORDER BY id", args)))
    if parts == ["report"]:
        from . import shiftreport
        if one("format") == "html":
            return 200, "text/html; charset=utf-8", shiftreport.render_html(svc)
        return 200, "text/markdown; charset=utf-8", shiftreport.render(svc)
    if parts == ["translations"]:
        return ok(_rows(db.execute("SELECT * FROM translations ORDER BY id")))
    if parts == ["reminders"]:
        return ok(_rows(db.execute("SELECT * FROM reminders ORDER BY due_ts")))
    if parts == ["meds"]:
        return ok(_rows(db.execute("SELECT patient_id, case_id, what, given_at, recorded_by, ts FROM meds ORDER BY ts")))
    if parts == ["activity"]:
        limit = int(one("limit") or 40)
        return ok(_rows(db.execute("SELECT id, patient_id, case_id, kind, actor, text, ts FROM events ORDER BY id DESC LIMIT ?", (limit,))))
    if parts == ["ward"]:
        n = lambda sql, *a: db.execute(sql, a).fetchone()[0]
        return ok({"patients": n("SELECT COUNT(DISTINCT patient_id) FROM chart_versions"),
                   "cases": n("SELECT COUNT(*) FROM cases"),
                   "awaiting_doctor": n("SELECT COUNT(*) FROM cases WHERE state='CONFIRMED_CONFLICT'"),
                   "unconfirmed": n("SELECT COUNT(*) FROM cases WHERE state='POSSIBLE_DISCREPANCY'"),
                   "resolved": n("SELECT COUNT(*) FROM cases WHERE state IN ('RESOLVED','HANDED_OFF')"),
                   "rejected": n("SELECT COUNT(*) FROM cases WHERE state='REJECTED'"),
                   "meds_given": n("SELECT COUNT(*) FROM meds"),
                   "tasks_open": n("SELECT COUNT(*) FROM room_tasks WHERE status='open'"),
                   "tasks_done": n("SELECT COUNT(*) FROM room_tasks WHERE status='done'"),
                   "refused": n("SELECT COUNT(*) FROM audit WHERE outcome='rejected'"),
                   "lookups": n("SELECT COUNT(*) FROM lookups"),
                   "tracked": n("SELECT COUNT(*) FROM tracking"),
                   "decisions": n("SELECT COUNT(*) FROM decisions")})
    if parts == ["tracking"]:
        return ok(_rows(db.execute("SELECT * FROM tracking ORDER BY id")))
    if parts == ["audit"]:
        limit = int(one("limit") or 50)
        return ok(_rows(db.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,))))
    if len(parts) == 2 and parts[0] == "timeline":
        role = one("role") or "nurse"
        if role not in ("nurse", "doctor") or svc.chart(parts[1]) is None:
            return err(403 if role not in ("nurse", "doctor") else 404, "staff roles only / unknown patient")
        if one("format") == "html":
            return 200, "text/html; charset=utf-8", timeline.render_html(db, svc, parts[1], role)
        return 200, "text/markdown; charset=utf-8", timeline.render(db, svc, parts[1], role)
    return err(404, "not found")

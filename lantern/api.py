"""Read-only REST backend over the Lantern database. Staff views only; nothing here can change the record.

  GET /healthz
  GET /api/patients
  GET /api/patients/<id>/chart                 current simulated chart
  GET /api/patients/<id>/chart/versions        version history (who changed it, when)
  GET /api/cases[?patient=&state=]
  GET /api/cases/<n>                           case, events, decision, task, handoffs
  GET /api/lookups[?agent=]                    the evidence log
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

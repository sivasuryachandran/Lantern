"""The shift record: everything that happened on the ward, in order, rebuilt from the database. Read-only.

  python -m lantern shiftreport [--html]      GET /api/report[?format=html]

Patient rooms are never read by an agent; this report is built from the record service's own tables, so it holds
the patient's words exactly as posted, every decision and refusal, the medicines given, tasks, reminders, translations
and tracked items. Staff only."""
import html as _html
from datetime import datetime

from . import timeline

STATES = {"POSSIBLE_DISCREPANCY": "possible discrepancy", "CONFIRMED_CONFLICT": "confirmed, awaiting the doctor",
          "RESOLVED": "resolved", "HANDED_OFF": "handed off", "REJECTED": "rejected"}


def _t(ts):
    return datetime.fromtimestamp(ts).strftime("%H:%M")


def render(svc):
    db = svc.db
    q = lambda sql, *a: [dict(r) for r in db.execute(sql, a).fetchall()]
    out = ["# Lantern shift record", "", "> **Fictional data, not for clinical use.** Rebuilt from the record service; nothing here can change the record.", ""]
    n = lambda sql: db.execute(sql).fetchone()[0]
    out += [f"**{n('SELECT COUNT(DISTINCT patient_id) FROM chart_versions')} patients · {n('SELECT COUNT(*) FROM cases')} cases · "
            f"{n('SELECT COUNT(*) FROM decisions')} doctor decisions · {n('SELECT COUNT(*) FROM meds')} medicines recorded · "
            f"{n('SELECT COUNT(*) FROM room_tasks WHERE status=\"open\"')} room tasks open · {n('SELECT COUNT(*) FROM audit WHERE outcome=\"rejected\"')} refused by code**", ""]
    for p in q("SELECT DISTINCT patient_id FROM chart_versions ORDER BY patient_id"):
        pid = p["patient_id"]
        chart = svc.chart(pid)
        room = db.execute("SELECT * FROM rooms WHERE patient_id=?", (pid,)).fetchone()
        out += [f"## {chart['display_name']} · simulated chart v{chart['chart_version']}", ""]
        out.append("Active orders: " + ", ".join(f"{o['type']}={o['value']}" for o in chart["orders"] if o["status"] == "active"))
        if room:
            left = [t["id"] for t in q("SELECT id FROM room_tasks WHERE room=? AND status='open'", room["room"])]
            out.append(f"Room {room['room']} (before: {room['prev_ref']}" + (f", {room['prev_precautions']}" if room['prev_precautions'] != 'none' else "") +
                       f"): {'ready' if not left else 'not ready, open: ' + ', '.join(left)}")
        out.append("")
        for c in q("SELECT * FROM cases WHERE patient_id=? ORDER BY id", pid):
            out += [f"### Case {c['id']} · {STATES.get(c['state'], c['state'])} · owner {c['owner']}",
                    f"> \"{c['quote']}\" (conflicts with {c['order_id']} at chart v{c['chart_version']})", ""]
            for e in q("SELECT * FROM events WHERE case_id=? ORDER BY id", c["id"]):
                out.append(f"- {_t(e['ts'])} **{timeline.LABELS.get(e['kind'], e['kind'])}** ({e['actor']}): {e['text']}")
            out.append("")
        others = q("SELECT * FROM events WHERE patient_id=? AND case_id IS NULL AND kind IN ('said','translation') ORDER BY id", pid)
        if others:
            out += ["Outside any case:"] + [f"- {_t(e['ts'])} **{timeline.LABELS.get(e['kind'], e['kind'])}** ({e['actor']}): {e['text']}" for e in others] + [""]
    out += ["## Medicines recorded as given (kept apart from orders)", ""]
    out += [f"- Patient {m['patient_id']}: {m['what']} at {m['given_at']} by {m['recorded_by']} (Case {m['case_id']})" for m in q("SELECT * FROM meds ORDER BY ts")] or ["- none"]
    out += ["", "## Room tasks", ""]
    out += [f"- {t['id']} ({t['room']}): {t['text']} — {'done by ' + t['done_by'] if t['status'] == 'done' else 'OPEN'}" for t in q("SELECT * FROM room_tasks ORDER BY id")]
    out += ["", "## Reminders", ""]
    out += [f"- Case {r['case_id']} at {_t(r['due_ts'])}: {r['text']} ({r['status']}, set by {r['created_by']})" for r in q("SELECT * FROM reminders ORDER BY due_ts")] or ["- none"]
    out += ["", "## Tracked in Jira and Calendar", ""]
    out += [f"- {t['system']} {t['ref']} for Case {t['case_id']}: {t['summary']}" for t in q("SELECT * FROM tracking ORDER BY id")] or ["- none"]
    out += ["", "## Commands refused or ignored by the code", ""]
    out += [f"- {a['action']} in {a['room']}: {a['outcome']}" + (f" ({a['reason']})" if a['reason'] else "") for a in q("SELECT * FROM audit WHERE outcome!='accepted' ORDER BY id")] or ["- none"]
    return "\n".join(out) + "\n"


def render_html(svc):
    body = _html.escape(render(svc))
    return ("<!doctype html><meta charset=utf-8><title>Lantern shift record</title>"
            "<style>body{font:15px/1.5 system-ui;max-width:900px;margin:2rem auto;padding:0 1rem;background:#0A101C;color:#E8EDF5}"
            "pre{white-space:pre-wrap;font:inherit}</style><pre>" + body + "</pre>")

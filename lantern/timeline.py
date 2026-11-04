"""Shared timeline, read by role. Five kinds of entry are never merged."""
from datetime import datetime

LABELS = {"said": "SAID", "draft": "DRAFT (unverified)", "nurse": "NURSE CONFIRMED", "chart": "SIMULATED CHART",
          "decision": "CLINICIAN CONFIRMED", "given": "GIVEN", "task": "OWNER", "handoff": "HANDOFF", "agent": "AGENT CLAIM CHECK", "fetch": "LOOKUP"}
# What each role may read: patients see their own words, confirmed answers and who owns the follow-up.
VISIBLE = {"patient": {"said", "decision", "task"},
           "nurse": set(LABELS), "doctor": set(LABELS)}


def render(db, svc, patient_id, role):
    chart = svc.chart(patient_id)
    out = [f"# Lantern timeline: {chart['display_name']} ({role} view)",
           "", "> **Fictional data, not for clinical use.** The chart below is a *simulated chart*.", "",
           f"Simulated chart v{chart['chart_version']}: " +
           ", ".join(f"{o['type']}={o['value']}" for o in chart["orders"] if o["status"] == "active"), ""]
    rows = db.execute("SELECT * FROM events WHERE patient_id=? ORDER BY id", (patient_id,)).fetchall()
    out += ["| Time | Case | Kind | By | What | Source |", "| --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        if r["kind"] in VISIBLE[role]:
            note = ""
            if r["kind"] == "fetch" and r["source"].startswith("lookup:"):
                lk = db.execute("SELECT version FROM lookups WHERE id=?", (int(r["source"][7:]),)).fetchone()
                if lk and lk["version"] < chart["chart_version"]:
                    note = f" **STALE** (chart is now v{chart['chart_version']})"
            t = datetime.fromtimestamp(r["ts"]).strftime("%H:%M:%S")
            out.append(f"| {t} | {r['case_id'] or ''} | {LABELS[r['kind']]} | {r['actor']} | "
                       f"{r['text'].replace('|', '/')}{note} | {r['source']} |")
    return "\n".join(out) + "\n"


def render_html(db, svc, patient_id, role):
    """A standalone page for the last demo scene: the same rows as the Markdown, in a table."""
    import html
    md = render(db, svc, patient_id, role).splitlines()
    rows = [[c.strip() for c in ln.strip("|").split("|")] for ln in md if ln.startswith("|") and "---" not in ln]
    th = "".join(f"<th>{html.escape(c)}</th>" for c in rows[0]) if rows else ""
    body = "".join("<tr>" + "".join(f"<td>{html.escape(c).replace('**STALE**', '<b>STALE</b>')}</td>" for c in r) + "</tr>"
                   for r in rows[1:])
    head = html.escape(md[0].lstrip("# "))
    return (f"<!doctype html><meta charset=utf-8><title>{head}</title>"
            "<style>body{font:15px system-ui;margin:2rem;max-width:1100px}table{border-collapse:collapse;width:100%}"
            "td,th{border:1px solid #ccc;padding:6px 8px;text-align:left;vertical-align:top}th{background:#f3f3f3}"
            ".b{background:#fff3cd;padding:8px;margin:12px 0}</style>"
            f"<h1>{head}</h1><div class=b><b>Fictional data, not for clinical use.</b> The chart is a simulated chart.</div>"
            f"<table><tr>{th}</tr>{body}</table>")

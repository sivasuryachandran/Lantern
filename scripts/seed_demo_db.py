"""Seed lantern.db with the synthetic charts plus a short history of earlier fictional cases (14 to 16),
so the first live case is still Case 17 and the timeline and API have something to show.
Idempotent. Usage: python scripts/seed_demo_db.py [path-to-db]"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lantern.service import connect, seed  # noqa: E402

# (case id, patient, topic, quote, order id, base version, change, explanation, owner, final state)
HISTORY = [
    (14, "103", "activity", "The nurse said I can walk to the window now", "ord-activity-3", 4,
     "activity: bed rest -> assisted walking", "You can walk with a nurse beside you for now.", "nurse-ana", "HANDED_OFF"),
    (15, "104", "diet", "I think the salt limit is over", "ord-diet-4", 1,
     "diet: low sodium -> low sodium", "Your salt limit stays the same.", "nurse-ben", "REJECTED"),
    (16, "103", "diet", "Can I have tea with breakfast", "ord-diet-3", 4,
     "diet: clear liquids -> clear liquids", "Tea is a clear liquid, so it is fine.", "nurse-ana", "RESOLVED"),
]


def main(path):
    db = connect(path)
    seed(db, ROOT / "data", 17)
    now = time.time() - 86400
    with db:
        for cid, pid, topic, quote, oid, ver, change, expl, owner, state in HISTORY:
            if db.execute("SELECT 1 FROM cases WHERE id=?", (cid,)).fetchone():
                continue
            db.execute("INSERT INTO cases(id,patient_id,state,topic,quote,patient_says,original_post_id,forwarded_post_id,"
                       "order_id,chart_version,owner,ts) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                       (cid, pid, state, topic, quote, "history (seeded)", f"hist-{cid}", f"hist-fwd-{cid}", oid, ver, owner, now))
            ev = [("said", f"patient-{pid}", quote), ("draft", "intake", f'possible discrepancy vs {oid}, unverified')]
            if state != "REJECTED":
                ev += [("nurse", owner, "confirmed the patient's belief differs from the order")]
            if state in ("RESOLVED", "HANDED_OFF"):
                ev += [("decision", "dr-lee", f"{change}; explanation sent to patient"), ("task", "record-service", f"follow-up owner: {owner}")]
            else:
                ev += [("nurse", owner, "rejected, no real conflict: matches the current order")]
            for kind, actor, text in ev:
                db.execute("INSERT INTO events(patient_id,case_id,kind,actor,text,source,ts) VALUES(?,?,?,?,?,?,?)",
                           (pid, cid, kind, actor, text, "seeded history", now))
            if state in ("RESOLVED", "HANDED_OFF"):
                db.execute("INSERT OR IGNORE INTO tasks VALUES(?,?,?,?)", (cid, "confirm the patient received the explanation",
                                                                         owner, int(state == "HANDED_OFF")))
                db.execute("INSERT OR IGNORE INTO decisions VALUES(?,?,?,?,?,?,?,?,?)",
                           (f"hist-dec-{cid}", cid, "seed", "dr-lee", ver, ver, change, expl, now))
    n = lambda t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"{path}: {n('chart_versions')} chart versions, {n('cases')} cases, {n('events')} events")


main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "lantern.db"))

"""Lantern record service.

Agents extract and route. This service is the only thing that changes the (simulated) chart,
announces a resolution, or posts to a patient room. Everything it does is idempotent so a
restart never duplicates a case, a thread root or a patient message.
"""
import copy
import hashlib
import json
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path

NURSE, DOCTOR, PATIENT_ROOM = "nurse-station", "doctor-review", "patient-{}"

POSSIBLE, CONFIRMED, REJECTED, RESOLVED, HANDED_OFF = (
    "POSSIBLE_DISCREPANCY", "CONFIRMED_CONFLICT", "REJECTED", "RESOLVED", "HANDED_OFF")

# Every message a patient can ever see from the service: these templates, or a doctor's own words.
PATIENT_TEMPLATES = {
    "checking": "Your care team is checking this (Case {n}). They'll answer here.",
    "own_pending": "Your care team is checking this (Case {n}). They'll answer here.",
    "own_answered": "Case {n} has an answer from your clinician above.",
    "refused": "I can only share updates about your own care. Your care team will answer questions here.",
    "owner": "Following up: {owner}",
}

RE_CONFIRM = re.compile(r"^CONFIRM Case (\d+)\s*$")
RE_REJECT = re.compile(r"^REJECT Case (\d+)\s+(\S.*)$", re.S)
RE_GIVEN = re.compile(r"^GIVEN Case (\d+)\s+(.+?)\s+(\d{1,2}:\d{2})\s*$")
RE_HANDOFF = re.compile(r"^HANDOFF Case (\d+)\s+open:\s*(\S.*)$", re.S)
RE_ACCEPT = re.compile(r"^ACCEPT Case (\d+)\s*$")
RE_DECIDE = re.compile(r"^DECIDE Case (\d+) v(\d+) (\w+)=(\w+)\s*\n\s*EXPLAIN:\s*(\S.*)$", re.S)
RE_CITE = re.compile(r"\[([\w-]+)\s+v(\d+)\s*[·|]\s*lookup\s*#(\d+)(?:\s*=\s*([^\]]+))?\]")
RE_CASE_MENTION = re.compile(r"\bcase\s+#?(\d+)", re.I)

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS posts_seen(post_id TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS outbox(key TEXT PRIMARY KEY, post_id TEXT);
CREATE TABLE IF NOT EXISTS said(
  post_id TEXT PRIMARY KEY, patient_id TEXT, room TEXT, user_id TEXT, text TEXT,
  forwarded_post_id TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS chart_versions(
  patient_id TEXT, version INTEGER, body TEXT, changed_by TEXT, ts REAL,
  PRIMARY KEY(patient_id, version));
CREATE TABLE IF NOT EXISTS cases(
  id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT, state TEXT, topic TEXT, quote TEXT,
  patient_says TEXT, original_post_id TEXT UNIQUE, forwarded_post_id TEXT, order_id TEXT,
  chart_version INTEGER, nurse_root TEXT, doctor_root TEXT, owner TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS decisions(
  post_id TEXT PRIMARY KEY, case_id INTEGER, doctor_user_id TEXT, doctor TEXT,
  from_version INTEGER, to_version INTEGER, change TEXT, explanation TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS meds(
  post_id TEXT PRIMARY KEY, patient_id TEXT, case_id INTEGER, what TEXT, given_at TEXT,
  recorded_by TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS handoffs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, case_id INTEGER, from_nurse TEXT, open_text TEXT,
  post_id TEXT UNIQUE, accepted_by TEXT, accept_post_id TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS tasks(
  case_id INTEGER PRIMARY KEY, text TEXT, owner TEXT, accepted INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT, case_id INTEGER, kind TEXT,
  actor TEXT, text TEXT, source TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS external(case_id INTEGER, kind TEXT, ref TEXT, PRIMARY KEY(case_id, kind));
CREATE TABLE IF NOT EXISTS lookups(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, agent TEXT, patient_id TEXT, entry TEXT,
  version INTEGER, label TEXT, value TEXT);
CREATE TABLE IF NOT EXISTS audit(
  id INTEGER PRIMARY KEY AUTOINCREMENT, post_id TEXT, user_id TEXT, room TEXT,
  action TEXT, outcome TEXT, reason TEXT, ts REAL);
"""


def connect(path):
    db = sqlite3.connect(path, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def seed(db, data_dir, first_case_number=1):
    """Load synthetic charts (only if absent) and set the first case number."""
    with db:
        for f in sorted(Path(data_dir).glob("patient-*.json")):
            chart = json.loads(f.read_text())
            db.execute("INSERT OR IGNORE INTO chart_versions VALUES(?,?,?,?,?)",
                       (chart["patient_id"], chart["chart_version"], json.dumps(chart), "seed", time.time()))
        if not db.execute("SELECT 1 FROM cases").fetchone() and \
           not db.execute("SELECT 1 FROM sqlite_sequence WHERE name='cases'").fetchone():
            db.execute("INSERT INTO sqlite_sequence(name, seq) VALUES('cases', ?)", (first_case_number - 1,))


def day_time(iso):
    d = datetime.fromisoformat(iso)
    return f"{d:%a} {d.hour}:{d.minute:02d}"


def entry_fact(chart, entry):
    """(label, canonical value) for a chart entry, as the service itself would state it."""
    for o in chart["orders"]:
        if o["id"] == entry:
            return f"{o['type'].capitalize()} order", o["value"]
    for e in chart["schedule"]:
        if e["id"] == entry:
            return e["name"], day_time(e["scheduled_for"])
    return None


def _norm(v):
    return re.sub(r"\b0(\d:)", r"\1", re.sub(r"\s+", " ", v.strip().lower()))


class Service:
    def __init__(self, db, chat, roles, clock=time.time, integrations=(), action_url=""):
        self.db, self.chat, self.roles, self.now = db, chat, roles, clock
        self.integrations = list(integrations)
        self.action_url = action_url             # set to enable Mattermost interactive buttons

    # ---------------------------------------------------------------- helpers
    def chart(self, patient_id):
        row = self.db.execute(
            "SELECT body FROM chart_versions WHERE patient_id=? ORDER BY version DESC LIMIT 1",
            (patient_id,)).fetchone()
        return json.loads(row["body"]) if row else None

    def case(self, number):
        return self.db.execute("SELECT * FROM cases WHERE id=?", (number,)).fetchone()

    def _audit(self, post, action, outcome, reason=""):
        self.db.execute("INSERT INTO audit(post_id,user_id,room,action,outcome,reason,ts) VALUES(?,?,?,?,?,?,?)",
                        (post.id, post.user_id, post.room, action, outcome, reason, self.now()))
        self.db.commit()

    def _event(self, patient_id, case_id, kind, actor, text, source=""):
        self.db.execute("INSERT INTO events(patient_id,case_id,kind,actor,text,source,ts) VALUES(?,?,?,?,?,?,?)",
                        (patient_id, case_id, kind, actor, text, source, self.now()))

    def _say(self, key, room, text, root_id="", buttons=None):
        """Post once per key, ever (restart-safe). Returns the Mattermost post id."""
        row = self.db.execute("SELECT post_id FROM outbox WHERE key=?", (key,)).fetchone()
        if row:
            return row["post_id"]
        pid = self.chat.post(room, text, root_id, self._props(buttons))
        self.db.execute("INSERT INTO outbox VALUES(?,?)", (key, pid))
        self.db.commit()
        return pid

    def _say_patient(self, key, patient_id, template, **kw):
        return self._say(key, PATIENT_ROOM.format(patient_id),
                         PATIENT_TEMPLATES[template].format(**kw))

    def _props(self, buttons):
        """Mattermost interactive-message props. buttons: [(label, command_word, case_number)]."""
        if not buttons or not self.action_url:
            return None
        return {"attachments": [{"actions": [
            {"id": f"{word.lower()}{n}", "name": label, "type": "button",
             "integration": {"url": self.action_url, "context": {"command": word, "case": n}}}
            for label, word, n in buttons]}]}

    def handle_action(self, user_id, context):
        """A button click. Mattermost supplies and verifies user_id; we turn it into the typed command,
        so every check (role, shift, thread, state) is the same as for a typed reply."""
        from .chat import Post
        c = self.case(int(context.get("case", 0)))
        word = context.get("command")
        if c is None or word not in ("CONFIRM", "REJECT", "ACCEPT") or not c["nurse_root"]:
            return "Unknown action."
        text = f"{word} Case {c['id']}" + (" rejected via button" if word == "REJECT" else "")
        self.handle(Post(f"btn:{word}:{c['id']}:{user_id}", NURSE, user_id, text, c["nurse_root"]))
        return "Done." if self.db.execute(
            "SELECT 1 FROM audit WHERE post_id=? AND outcome='accepted'",
            (f"btn:{word}:{c['id']}:{user_id}",)).fetchone() else "Not allowed for you right now."

    def _notify(self, hook, case_number, owner):
        for integ in self.integrations:
            try:
                note = getattr(integ, hook)(self.case(case_number), owner, self.db)
            except Exception as e:                       # an integration failing never blocks the loop
                note = f"{type(integ).__name__} failed: {e}"
            if note:
                c = self.case(case_number)
                self._event(c["patient_id"], case_number, "task", "integration", note)
                self.db.commit()

    def lookup(self, agent, patient_id, entry):
        """The chart lookup tool. Code, not an LLM: every call is logged with a lookup number, the entry,
        the chart version and the asking agent. Returns None for an unknown entry (nothing is logged)."""
        c = self.chart(patient_id)
        fact = entry_fact(c, entry) if c else None
        if fact is None:
            return None
        label, value = fact
        with self.db:
            cur = self.db.execute("INSERT INTO lookups(ts,agent,patient_id,entry,version,label,value) "
                                  "VALUES(?,?,?,?,?,?,?)", (self.now(), agent, patient_id, entry,
                                                            c["chart_version"], label, value))
            self._event(patient_id, None, "fetch", agent,
                        f"{entry} v{c['chart_version']} ({label}: {value}), lookup #{cur.lastrowid}",
                        f"lookup:{cur.lastrowid}")
        n = cur.lastrowid
        return {"lookup": n, "patient": patient_id, "entry": entry, "version": c["chart_version"],
                "label": label, "value": value, "agent": agent,
                "citation": f"[{entry} v{c['chart_version']} · lookup #{n} = {value}]"}

    def forwarded_id(self, original_post_id):
        """Mattermost id of record-bot's forwarded message for a patient post (read-only; claim validation unchanged)."""
        row = self.db.execute("SELECT forwarded_post_id FROM said WHERE post_id=?", (original_post_id,)).fetchone()
        return row["forwarded_post_id"] if row else None

    def verify_citation(self, agent, patient_id, entry, version, lookup_id, claimed):
        """-> (status, detail, row) with status verified | stale | unverified. Pure code; no model involved."""
        row = self.db.execute("SELECT * FROM lookups WHERE id=?", (lookup_id,)).fetchone()
        if row is None:
            return "unverified", f"no matching lookup #{lookup_id}", None
        if row["agent"] != agent:
            return "unverified", f"lookup #{lookup_id} was made by {row['agent']}, not {agent}", row
        if row["patient_id"] != patient_id:
            return "unverified", f"lookup #{lookup_id} is for patient {row['patient_id']}, not this case's patient", row
        if row["entry"] != entry or row["version"] != int(version):
            return "unverified", f"lookup #{lookup_id} is {row['entry']} v{row['version']}, not {entry} v{version}", row
        if claimed and _norm(claimed) != _norm(row["value"]):
            return "unverified", f"wrong value: written \"{claimed.strip()}\", source says \"{row['value']}\"", row
        current = self.chart(patient_id)["chart_version"]
        if row["version"] < current:
            return "stale", f"cited v{row['version']} but the chart is now v{current}; look it up again", row
        return "verified", "source value and version match", row

    def chart_excerpt(self, patient_id, ids=None):
        c = self.chart(patient_id)
        v = c["chart_version"]
        lines = [f"CHART EXCERPT (simulated chart, v{v}, fictional data)"]
        for o in [o for o in c["orders"] if ids is None or o["id"] in ids]:
            lines.append(f"- {o['id']}: {o['type']} = {o['value']}, {o['status']}, reason: {o['reason']} [{o['id']}, v{v}]")
        for s in [s for s in c["schedule"] if ids is None or s["id"] in ids]:
            lines.append(f"- {s['id']}: {s['name']} now {day_time(s['scheduled_for'])}, was {day_time(s['previously'])}; "
                         f"changed {day_time(s['changed_at'])} by {s['changed_by']} [{s['id']}, v{v}]")
        return "\n".join(lines)

    # --------------------------------------------------------------- dispatch
    def handle(self, post):
        if self.db.execute("SELECT 1 FROM posts_seen WHERE post_id=?", (post.id,)).fetchone():
            return
        user = self.roles.by_id(post.user_id)
        replayed = self.db.execute("SELECT 1 FROM audit WHERE post_id=? AND outcome='accepted'",
                                   (post.id,)).fetchone()
        if replayed and post.room != DOCTOR:             # already applied; DECIDE has its own resume path
            user = None
        if user is not None and user.role != "bot":      # record-bot's own posts never trigger anything
            if post.edited:
                self._audit(post, "any", "ignored", "edited posts never count")
            elif post.room.startswith("patient-"):
                self._patient_post(post, user)
            elif post.room == NURSE:
                self._nurse_room_post(post, user)
            elif post.room == DOCTOR:
                self._doctor_room_post(post, user)
        self.db.execute("INSERT OR IGNORE INTO posts_seen VALUES(?)", (post.id,))
        self.db.commit()

    # ---------------------------------------------------------------- patients
    def _patient_post(self, post, user):
        pid = post.room.split("-", 1)[1]
        if user.role != "patient" or user.patient_id != pid:
            self._audit(post, "patient_message", "ignored", "not this room's patient")
            return
        self._record_said(post.id, pid, post.room, post.user_id, user.username, post.message, f"post {post.id}")

        m = RE_CASE_MENTION.search(post.message)
        if m:
            c = self.case(int(m.group(1)))
            if c is None or c["patient_id"] != pid:
                self._say_patient(f"refuse:{post.id}", pid, "refused")
            elif c["state"] in (RESOLVED, HANDED_OFF):
                self._say_patient(f"ask:{post.id}", pid, "own_answered", n=c["id"])
            else:
                self._say_patient(f"ask:{post.id}", pid, "own_pending", n=c["id"])
            return

        self._forward(post.id, pid, user.display, post.room, post.message)

    def _record_said(self, post_id, pid, room, user_id, actor, text, source):
        self.db.execute("INSERT OR IGNORE INTO said VALUES(?,?,?,?,?,?,?)",
                        (post_id, pid, room, user_id, text, None, self.now()))
        self._event(pid, None, "said", actor, text, source)
        self.db.commit()

    def _forward(self, post_id, pid, display, room, text_):
        c = self.chart(pid)
        orders = "; ".join(f"{o['id']} {o['type']}={o['value']}" for o in c["orders"] if o["status"] == "active")
        text = (f"@intake New message from {display} (room {room}). "
                f"original_post_id: {post_id}\n"
                f"Active orders (simulated chart v{c['chart_version']}): {orders}\n> {text_}")
        fwd = self._say(f"fwd:{post_id}", NURSE, text)
        self.db.execute("UPDATE said SET forwarded_post_id=? WHERE post_id=?", (fwd, post_id))
        self.db.commit()

    def ingest_clip(self, patient_id, clip_id, segments):
        """Tier 2: a recorded, transcribed fictional bedside clip. Each segment is {"t": seconds, "text": ...}
        and becomes a 'said' entry whose id and source carry the timestamp, so a claim cites clip@time."""
        c = self.chart(patient_id)
        for seg in segments:
            sid = f"clip:{clip_id}@{seg['t']}"
            self._record_said(sid, patient_id, f"patient-{patient_id}", "clip", f"clip:{clip_id}",
                              seg["text"], f"clip {clip_id} @ {seg['t']}s")
            self._forward(sid, patient_id, c["display_name"], f"patient-{patient_id} (recorded clip @ {seg['t']}s)",
                          seg["text"])

    # ------------------------------------------------------------ nurse-station
    def _timeline_cmd(self, post, user):
        """TIMELINE <patient>: a nurse or doctor asks record-bot to post the role-scoped shared timeline."""
        from . import timeline
        m = re.match(r"^TIMELINE (\d+)\s*$", post.message.strip())
        if not m or user.role not in ("nurse", "doctor") or self.chart(m.group(1)) is None:
            return False
        self._reply(post, "tl", timeline.render(self.db, self, m.group(1), user.role))
        return True

    def _nurse_room_post(self, post, user):
        msg = post.message.strip()
        if self._timeline_cmd(post, user):
            return
        if user.role == "agent":
            if user.username == "intake" and msg.lstrip("`json \n").startswith("{"):
                self._claim_card(post, user)
            else:
                self._check_agent_claims(post, user)
            return
        if user.role != "nurse":
            return
        for rx, fn in ((RE_CONFIRM, self._confirm), (RE_REJECT, self._reject), (RE_GIVEN, self._given),
                       (RE_HANDOFF, self._handoff), (RE_ACCEPT, self._accept)):
            m = rx.match(msg)
            if m:
                fn(post, user, m)
                return

    def _reply(self, post, key, text):
        return self._say(f"{key}:{post.id}", post.room, text, post.root_id or "")

    def _claim_card(self, post, user):
        def reject(reason):
            self._audit(post, "claim_card", "rejected", reason)
            self._reply(post, "claimrej", f"Card rejected: {reason}. No case opened; the patient was not notified.")

        raw = post.message.strip().strip("`")
        raw = raw[4:] if raw.startswith("json") else raw
        try:
            card = json.loads(raw)
            src = card["source"]
            orig = self.db.execute("SELECT * FROM said WHERE post_id=?", (src["original_post_id"],)).fetchone()
        except (ValueError, KeyError, TypeError):
            return reject("not a valid claim card")
        if orig is None:
            return reject("original_post_id is not a recorded patient post")
        existing = self.db.execute("SELECT * FROM cases WHERE original_post_id=?", (orig["post_id"],)).fetchone()
        if existing is not None:                         # replay or duplicate card: finish opening, never reopen
            return self._open_nurse_thread(existing)
        if card.get("status") != "possible_discrepancy":
            return reject("status must be possible_discrepancy")
        if str(card.get("patient_id")) != orig["patient_id"] or src.get("room") != orig["room"]:
            return reject("card patient/room does not match the original post")
        if src.get("forwarded_post_id") != orig["forwarded_post_id"]:
            return reject("forwarded_post_id does not match the forwarded message")
        quote = card.get("quote") or ""
        if not quote or quote not in orig["text"]:
            return reject("quote is not an exact substring of the original patient post")
        chart = self.chart(orig["patient_id"])
        active = [o for o in chart["orders"] if o["type"] == card.get("topic") and o["status"] == "active"]
        conflicts = card.get("conflicts_with") or {}
        if not active or conflicts.get("order_id") != active[0]["id"]:
            return reject("no matching active order for that topic")
        if conflicts.get("chart_version") != chart["chart_version"]:
            return reject("card cites a stale chart version")

        with self.db:
            cur = self.db.execute(
                "INSERT INTO cases(patient_id,state,topic,quote,patient_says,original_post_id,forwarded_post_id,"
                "order_id,chart_version,owner,ts) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (orig["patient_id"], POSSIBLE, card["topic"], quote, card.get("patient_says", ""),
                 orig["post_id"], orig["forwarded_post_id"], active[0]["id"], chart["chart_version"],
                 chart["care_team"]["nurse"], self.now()))
            self._event(orig["patient_id"], cur.lastrowid, "draft", "intake",
                        f'possible discrepancy, unverified: "{quote}" vs {active[0]["id"]} ({active[0]["value"]})',
                        f"post {orig['post_id']}")
        self._open_nurse_thread(self.case(cur.lastrowid))

    def _open_nurse_thread(self, c):
        n = c["id"]
        root = self._say(f"case:{n}:nurse_root", NURSE,
                         f'Case {n} · possible discrepancy (unconfirmed)\n> "{c["quote"]}"\n'
                         f"Active order {c['order_id']} (v{c['chart_version']}). @intake",
                         buttons=[("Confirm", "CONFIRM", n), ("Reject", "REJECT", n)])
        self.db.execute("UPDATE cases SET nurse_root=? WHERE id=?", (root, n))
        self.db.commit()
        self._say(f"case:{n}:nurse_excerpt", NURSE,
                  self.chart_excerpt(c["patient_id"]) + f"\nNurse: CONFIRM Case {n} | REJECT Case {n} <reason>", root)
        self._say_patient(f"case:{n}:ack", c["patient_id"], "checking", n=n)

    def _case_in_thread(self, post, number, action):
        c = self.case(int(number))
        if c is None or not c["nurse_root"] or post.root_id != c["nurse_root"]:
            self._audit(post, action, "rejected", "not a reply in that case's nurse thread")
            self._reply(post, "rej", f"{action} ignored: it must be a reply inside the Case {number} thread.")
            return None
        return c

    def _confirm(self, post, user, m):
        c = self._case_in_thread(post, m.group(1), "CONFIRM")
        if c is None:
            return
        if c["state"] != POSSIBLE:
            self._audit(post, "CONFIRM", "ignored", f"case is {c['state']}")
            return
        with self.db:
            self.db.execute("UPDATE cases SET state=? WHERE id=?", (CONFIRMED, c["id"]))
            self._event(c["patient_id"], c["id"], "nurse", user.username,
                        f"confirmed the patient believes the order allows it: \"{c['quote']}\"", f"post {post.id}")
        self._audit(post, "CONFIRM", "accepted")
        n = c["id"]
        root = self._say(f"case:{n}:doctor_root", DOCTOR,
                         f'Case {n} · nurse-confirmed conflict\n> "{c["quote"]}"\n'
                         f"Active order {c['order_id']} (v{c['chart_version']}). @care-coordinator")
        self.db.execute("UPDATE cases SET doctor_root=? WHERE id=?", (root, n))
        self.db.commit()
        self._say(f"case:{n}:doctor_excerpt", DOCTOR,
                  self.chart_excerpt(c["patient_id"]) +
                  f"\nDoctor: DECIDE Case {n} v{c['chart_version']} <order>=<value>\nEXPLAIN: <words for the patient>", root)
        self._reply(post, "esc", f"Case {n} confirmed and escalated to {DOCTOR}.")

    def _reject(self, post, user, m):
        c = self._case_in_thread(post, m.group(1), "REJECT")
        if c is None:
            return
        if c["state"] != POSSIBLE:
            self._audit(post, "REJECT", "ignored", f"case is {c['state']}")
            return
        with self.db:
            self.db.execute("UPDATE cases SET state=? WHERE id=?", (REJECTED, c["id"]))
            self._event(c["patient_id"], c["id"], "nurse", user.username,
                        f"rejected, no real conflict: {m.group(2).strip()}", f"post {post.id}")
        self._audit(post, "REJECT", "accepted", m.group(2).strip())
        self._reply(post, "rejack", f"Case {c['id']} closed. Reason logged: {m.group(2).strip()}")

    def _given(self, post, user, m):
        if user.shift != "outgoing":
            self._audit(post, "GIVEN", "rejected", "only the outgoing on-shift nurse can record GIVEN")
            return
        c = self._case_in_thread(post, m.group(1), "GIVEN")
        if c is None:
            return
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO meds VALUES(?,?,?,?,?,?,?)",
                            (post.id, c["patient_id"], c["id"], m.group(2), m.group(3), user.username, self.now()))
            self._event(c["patient_id"], c["id"], "given", user.username,
                        f"{m.group(2)} given at {m.group(3)} (recorded by {user.username}; order unchanged)",
                        f"post {post.id}")
        self._audit(post, "GIVEN", "accepted")
        self._reply(post, "givenack", f"Recorded: {m.group(2)} given {m.group(3)} by {user.username}. No order was changed.")

    def _handoff(self, post, user, m):
        if user.shift != "outgoing":
            self._audit(post, "HANDOFF", "rejected", "only the outgoing on-shift nurse can hand off")
            return
        c = self._case_in_thread(post, m.group(1), "HANDOFF")
        if c is None:
            return
        if c["state"] != RESOLVED:
            self._audit(post, "HANDOFF", "rejected", f"case is {c['state']}, not RESOLVED")
            self._reply(post, "rej", f"HANDOFF ignored: Case {c['id']} is {c['state']}.")
            return
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO handoffs(case_id,from_nurse,open_text,post_id,ts) VALUES(?,?,?,?,?)",
                            (c["id"], user.username, m.group(2).strip(), post.id, self.now()))
            self.db.execute("UPDATE tasks SET text=? WHERE case_id=?", (m.group(2).strip(), c["id"]))
            self._event(c["patient_id"], c["id"], "handoff", user.username,
                        f"handed off, still open: {m.group(2).strip()}", f"post {post.id}")
        self._audit(post, "HANDOFF", "accepted")
        meds = self.db.execute("SELECT what, given_at FROM meds WHERE case_id=?", (c["id"],)).fetchall()
        given = "; ".join(f"{r['what']} at {r['given_at']}" for r in meds) or "none recorded"
        self._reply(post, "handoffack",
                    f"HANDOFF pending for Case {c['id']} from {user.username}. Open: {m.group(2).strip()}. "
                    f"Given: {given}. @care-coordinator please show the incoming nurse everything open. "
                    f"Incoming nurse: reply ACCEPT Case {c['id']}.")
        self._say(f"acceptbtn:{post.id}", NURSE, f"Case {c['id']}: accept the follow-up?", post.root_id,
                  buttons=[("Accept", "ACCEPT", c["id"])])

    def _accept(self, post, user, m):
        c = self._case_in_thread(post, m.group(1), "ACCEPT")
        if c is None:
            return
        pending = self.db.execute(
            "SELECT * FROM handoffs WHERE case_id=? AND accepted_by IS NULL ORDER BY id DESC LIMIT 1",
            (c["id"],)).fetchone()
        if user.shift != "incoming" or pending is None:
            self._audit(post, "ACCEPT", "rejected",
                        "only the incoming nurse can accept" if user.shift != "incoming" else "no pending HANDOFF")
            return
        with self.db:
            self.db.execute("UPDATE handoffs SET accepted_by=?, accept_post_id=? WHERE id=?",
                            (user.username, post.id, pending["id"]))
            self.db.execute("UPDATE tasks SET owner=?, accepted=1 WHERE case_id=?", (user.username, c["id"]))
            self.db.execute("UPDATE cases SET state=?, owner=? WHERE id=?", (HANDED_OFF, user.username, c["id"]))
            self._event(c["patient_id"], c["id"], "task", user.username,
                        f"accepted the follow-up; owner is now {user.username}", f"post {post.id}")
        self._audit(post, "ACCEPT", "accepted")
        self._reply(post, "acceptack", f"Case {c['id']} follow-up accepted by {user.username}.")
        self._say_patient(f"owner:{c['id']}:{user.username}", c["patient_id"], "owner", owner=user.username)
        self._notify("on_accept", c["id"], user.username)

    # ------------------------------------------------------------ doctor-review
    def _check_agent_claims(self, post, user):
        """Under care-coordinator's post in a case thread, record-bot posts a card per cited fact (value taken
        from the lookup log, not from the agent's words) with a check mark or warning. Everything else the
        agent wrote stays unverified interpretation."""
        if user.username != "care-coordinator" or not post.root_id:
            return
        c = self.db.execute("SELECT * FROM cases WHERE doctor_root=? OR nurse_root=?",
                            (post.root_id, post.root_id)).fetchone()
        if c is None or post.message.lstrip().startswith("NO DATA"):
            return
        cites = RE_CITE.findall(post.message)
        if not cites:
            if post.root_id == c["doctor_root"]:
                self._audit(post, "claim_check", "rejected", "no lookup receipt")
                self._reply(post, "chk", "⚠ unverified: no lookup receipt cited. Nothing in that message is "
                            "backed by a checked source. Cite like [proc-1 v3 · lookup #31] or say NO DATA.")
            return
        lines, bad = [], 0
        for entry, v, lid, claimed in cites:
            status, detail, row = self.verify_citation(user.username, c["patient_id"], entry, v, int(lid), claimed)
            if status == "verified":
                lines.append(f"**{row['label']}: {row['value']}**\nSource: `{entry} v{v}` · lookup `#{lid}` · fetched by "
                             f"{row['agent']}\n✓ Verified: {detail}")
            else:
                bad += 1
                lines.append(f"⚠ {status}: `{entry} v{v}` · lookup `#{lid}`: {detail}")
        lines.append("Only the cited source facts are checked. Everything else in the message above is "
                     "unverified interpretation, not a clinical answer.")
        self._audit(post, "claim_check", "rejected" if bad else "ok", f"{len(cites) - bad}/{len(cites)} verified")
        self._event(c["patient_id"], c["id"], "agent", user.username,
                    f"claim check: {len(cites) - bad} of {len(cites)} cited facts verified", f"post {post.id}")
        self._reply(post, "chk", "\n\n".join(lines))

    def _doctor_room_post(self, post, user):
        if self._timeline_cmd(post, user):
            return
        if user.role == "agent":
            return self._check_agent_claims(post, user)
        m = RE_DECIDE.match(post.message.strip())
        if not m:
            return
        self._decide(post, user, m)

    def _decide(self, post, user, m):
        number, version, otype, value, explanation = int(m.group(1)), int(m.group(2)), m.group(3), m.group(4), m.group(5)
        c = self.case(number)
        done = self.db.execute("SELECT 1 FROM decisions WHERE post_id=?", (post.id,)).fetchone()

        def refuse(reason, tell=True):
            self._audit(post, "DECIDE", "rejected", reason)
            if tell and c is not None and c["doctor_root"]:
                self._say(f"decrej:{post.id}", DOCTOR, f"DECIDE ignored: {reason}.", c["doctor_root"])

        if not done:
            if user.role != "doctor":
                return refuse("only a verified doctor can decide", tell=False)
            if c is None or not c["doctor_root"] or post.root_id != c["doctor_root"]:
                return refuse("must be a reply in that case's doctor thread")
            if c["state"] != CONFIRMED:
                return refuse(f"case is {c['state']}, not CONFIRMED_CONFLICT")
            chart = self.chart(c["patient_id"])
            if version != chart["chart_version"]:
                return refuse(f"stale chart version v{version}; current is v{chart['chart_version']}. Re-review and resubmit")
            active = [o for o in chart["orders"] if o["type"] == otype and o["status"] == "active"]
            if not active:
                return refuse(f"no active {otype} order to change")
            new = copy.deepcopy(chart)
            new["chart_version"] = version + 1
            for o in new["orders"]:
                if o["id"] == active[0]["id"]:
                    o["status"] = "superseded"
            new["orders"].append({"id": f"ord-{otype}-{version + 1}", "type": otype, "value": value,
                                  "reason": f"{user.username} decision, Case {number}", "status": "active"})
            with self.db:
                self.db.execute("INSERT INTO decisions VALUES(?,?,?,?,?,?,?,?,?)",
                                (post.id, number, user.user_id, user.username, version, version + 1,
                                 f"{otype}: {active[0]['value']} -> {value}", explanation, self.now()))
                self.db.execute("INSERT INTO chart_versions VALUES(?,?,?,?,?)",
                                (c["patient_id"], version + 1, json.dumps(new), user.username, self.now()))
                self.db.execute("UPDATE cases SET state=?, owner=? WHERE id=?",
                                (RESOLVED, chart["care_team"]["nurse"], number))
                self.db.execute("INSERT OR IGNORE INTO tasks VALUES(?,?,?,0)",
                                (number, "confirm the patient received the doctor's explanation",
                                 chart["care_team"]["nurse"]))
                self._event(c["patient_id"], number, "decision", user.username,
                            f"{otype} {active[0]['value']} -> {value}; explanation sent to patient",
                            f"post {post.id}")
                self._event(c["patient_id"], number, "chart", "record-service",
                            f"simulated chart v{version} -> v{version + 1}", f"post {post.id}")
                self._event(c["patient_id"], number, "task", "record-service",
                            f"follow-up owner: {chart['care_team']['nurse']}", f"post {post.id}")
            self._audit(post, "DECIDE", "accepted")
            c = self.case(number)
        else:
            c = self.case(number)

        d = self.db.execute("SELECT * FROM decisions WHERE post_id=?", (post.id,)).fetchone()
        doctor = self.roles.by_name(d["doctor"])
        self._say(f"case:{number}:doctor_words", PATIENT_ROOM.format(c["patient_id"]),
                  f"{d['explanation']}\n- {doctor.display}, confirmed on Case {number}")
        first = self._first_owner(number)
        self._say_patient(f"owner:{number}:{first}", c["patient_id"], "owner", owner=first)
        self._say(f"case:{number}:doctor_ack", DOCTOR,
                  f"Case {number} resolved: simulated chart now v{d['to_version']} ({d['change']}). "
                  f"Explanation sent to the patient word for word.", c["doctor_root"])
        self._notify("on_resolved", number, first)

    def _first_owner(self, number):
        """The nurse the follow-up task was created for (before any handoff)."""
        chart = self.chart(self.case(number)["patient_id"])
        return chart["care_team"]["nurse"]

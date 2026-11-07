"""Scripted stand-ins for the two Switch agents (intake, care-coordinator), written as real agents.

They do what the instructions in docs/agents/ ask, with plain rules instead of a model, so the whole ward can be shown
working when the real agents are not reachable. Each one logs in as its own Mattermost account, reads the rooms,
and replies only to record-bot's @mentions. They get chart facts only through the lookup tool (the same HTTP
endpoint the real care-coordinator uses), so every citation is logged and checked like the real thing.

Say so on screen when you use them: these are not Switch agents.

  python -m lantern simagents            # all three agents, until Ctrl-C (LANTERN_SPEAK=1 reads translations aloud with macOS `say`)
  python -m lantern simagents intake     # just one
"""
import json
import os
import re
import subprocess
import time
import urllib.request
from pathlib import Path

NURSE, DOCTOR = "nurse-station", "doctor-review"
TOPIC_WORDS = {
    "diet": ("breakfast", "lunch", "dinner", "eat", "eating", "food", "tea", "coffee", "drink", "meal", "hungry", "salt",
             "desayun", "almuerzo", "comer", "comida", "cena", "beber"),
    "activity": ("walk", "bathroom", "stand", "chair", "shower", "physio", "get up", "out of bed",
                 "caminar", "baño", "silla", "sentar", "levantar", "ducha", "fisio"),
}
RE_FORWARD = re.compile(r"New message from Patient (\d+)[^\n]*?\(room patient-\d+\)\.\s*original_post_id: (\S+)\s*\nActive orders \(simulated chart v(\d+)\): (.+?)\n> (.+)$", re.S)
RE_ORDER = re.compile(r"(ord-[\w-]+) (\w+)=([^;\n]+)")
RE_CASE = re.compile(r"Case (\d+)")


# ------------------------------------------------------------------ tools
class HttpTools:
    """What an agent may read: the lookup tool, the read-only API, and the tracking ledger."""

    def __init__(self, base="http://127.0.0.1:8099"):
        self.base = base.rstrip("/")

    def _get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=20) as r:
            return json.load(r)

    def chart(self, patient):
        return self._get(f"/api/patients/{patient}/chart")

    def case(self, number):
        return self._get(f"/api/cases/{number}")

    def lookup(self, agent, patient, entry):
        try:
            return self._get(f"/chart/{patient}/{entry}?agent={agent}")
        except Exception:
            return None

    def translate(self, agent, body):
        req = urllib.request.Request(self.base + "/translation", method="POST", data=json.dumps({"agent": agent, **body}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)

    def track(self, agent, body):
        req = urllib.request.Request(self.base + "/tracking", method="POST", data=json.dumps({"agent": agent, **body}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)


class ServiceTools:
    """The same tools, called in-process (used by the tests)."""

    def __init__(self, svc):
        self.svc = svc

    def chart(self, patient):
        return self.svc.chart(patient)

    def case(self, number):
        from . import api
        return json.loads(api.route(self.svc, f"/api/cases/{number}", {})[2])

    def lookup(self, agent, patient, entry):
        return self.svc.lookup(agent, patient, entry)

    def track(self, agent, body):
        return self.svc.record_tracking(agent, body)

    def translate(self, agent, body):
        return self.svc.record_translation(agent, body)


# ------------------------------------------------------------------ agents
class IntakeAgent:
    name = "intake"
    mention = "@intake"

    def __init__(self, chat, tools):
        self.chat, self.tools = chat, tools

    def handle(self, post):
        if post.room != NURSE or self.mention not in post.message:
            return
        m = RE_FORWARD.search(post.message.strip())
        if m and not post.root_id:
            return self._flag(post, *m.groups())
        if post.message.startswith("Case ") and "possible discrepancy (unconfirmed)" in post.message:
            n = RE_CASE.match(post.message).group(1)
            self.chat.post(NURSE, f"Case {n}: what did the patient mean? Reply CONFIRM Case {n} if the patient really believes the "
                                  f"order allows it, or REJECT Case {n} <reason> if not.", post.id)

    def _flag(self, post, patient, original_id, version, orders, quote):
        quote = quote.strip().strip('"')
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", quote) if s.strip()]
        for o in RE_ORDER.finditer(orders):
            order_id, topic = o.group(1), o.group(2)
            words = TOPIC_WORDS.get(topic, ())
            hit = next((s for s in sentences if any(w in s.lower() for w in words)), None)
            if hit is None:
                continue
            hit = hit.rstrip(".")                    # an exact piece of the patient's own words
            card = {"patient_id": patient, "topic": topic, "status": "possible_discrepancy",
                    "patient_says": f"believes the {topic} order allows it", "quote": hit,
                    "source": {"room": f"patient-{patient}", "original_post_id": original_id, "forwarded_post_id": post.id},
                    "conflicts_with": {"order_id": order_id, "chart_version": int(version)}}
            return self.chat.post(NURSE, json.dumps(card))
        # nothing conflicts: say nothing, as the instructions say


class CoordinatorAgent:
    name = "care-coordinator"
    mention = "@care-coordinator"

    def __init__(self, chat, tools, tracking=None):
        self.chat, self.tools = chat, tools
        self.tracking = tracking or {}              # case number -> {"jira": {...}, "calendar": {...}}

    def handle(self, post):
        if self.mention not in post.message:
            return
        if post.message.startswith("Reminder set for"):
            return self._reminder(post)
        if post.root_id and post.room == DOCTOR:
            return
        if post.room == DOCTOR and "nurse-confirmed conflict" in post.message:
            return self._summary(post)
        if post.room == NURSE and "HANDOFF pending for Case" in post.message:
            return self._handoff(post)

    def _reminder(self, post):
        """A reminder was set: add it to the owner's calendar (reported once to the tracking ledger)."""
        n = int(RE_CASE.search(post.message).group(1))
        item = (self.tracking.get(str(n)) or {}).get("calendar")
        if item:
            self.tools.track(self.name, {"case": n, "system": "calendar", "ref": item["ref"], "url": item.get("url", ""),
                                          "summary": item["summary"], "simulated": True})
            self.chat.post(post.room, f"Added to the calendar: {item['summary']}.", post.root_id or post.id)

    def _cite(self, patient, entry):
        r = self.tools.lookup(self.name, patient, entry)
        return r and (r["label"], r["value"], r["citation"])

    def _summary(self, post):
        n = int(RE_CASE.match(post.message).group(1))
        case = self.tools.case(n)["case"]
        quote = re.search(r'> "(.+?)"', post.message)
        parts = [f'Case {n}: the patient said "{quote.group(1) if quote else case["quote"]}". A nurse confirmed the conflict.']
        order = self._cite(case["patient_id"], case["order_id"])
        if order:
            parts.append(f"{order[0]}: {order[1]} {order[2]}.")
        for entry in self.tools.chart(case["patient_id"]).get("schedule", []):
            got = self._cite(case["patient_id"], entry["id"])
            if got:
                parts.append(f"{got[0]}: {got[1]} {got[2]}.")
        parts.append("I am not recommending a decision.")
        self.chat.post(DOCTOR, " ".join(parts), post.id)

    def _handoff(self, post):
        n = int(RE_CASE.search(post.message).group(1))
        detail = self.tools.case(n)
        case = detail["case"]
        given = "; ".join(f"{m['what']} at {m['given_at']}" for m in detail["medication_given"]) or "nothing recorded"
        still = [h["open_text"] for h in detail["handoffs"] if not h.get("accepted_by")] or ["nothing"]
        text = (f"Brief for the incoming nurse, Case {n} (patient {case['patient_id']}, {case['state'].replace('_', ' ').lower()}): "
                f"still open: {still[-1]}. Given: {given}. Owner now: {case['owner']}. Reply ACCEPT Case {n} to take it.")
        track = self.tracking.get(str(n))
        if track:
            for system in ("jira", "calendar"):
                item = track.get(system)
                if item:
                    self.tools.track(self.name, {"case": n, "system": system, "ref": item["ref"], "url": item.get("url", ""),
                                                  "summary": item["summary"], "simulated": True})
            refs = ", ".join(f"{s} {track[s]['ref']}" for s in ("jira", "calendar") if track.get(s))
            text += f" Tracked in {refs}."
        self.chat.post(NURSE, text, post.root_id or post.id)


class InterpreterAgent:
    """Translates between a patient and the staff, in both directions, and reads the result aloud when asked.

    The stand-in works from a small phrase table (no model), so it covers the demo sentences only; the real agent would
    translate anything. It can only report translations to the record service, which shows them beside the original
    words. It never posts to a patient room itself."""
    name = "interpreter"
    mention = "@interpreter"
    VOICES = {"es": "Flo (Spanish (Mexico))", "en": "Samantha"}
    PAIRS = [   # (Spanish, English), sentence by sentence
        ("Buenos días.", "Good morning."),
        ("El fisioterapeuta dijo que puedo sentarme en la silla para el almuerzo.", "The physio said I can sit in the chair for lunch."),
        ("Tengo muchas ganas de desayunar.", "I can't wait for breakfast."),
        ("El doctor Lee dijo que ya puedo comer.", "Dr. Lee said I can eat now."),
        ("Sentarse en la silla para el almuerzo está bien si alguien la acompaña. - Dr. Lee",
         "Sitting in the chair for lunch is fine with someone beside you. - Dr. Lee"),
        ("Su procedimiento se movió al jueves, así que hoy puede comer normalmente. - Dr. Lee",
         "Your procedure moved to Thursday, so you can eat normally today. - Dr. Lee"),
    ]

    def __init__(self, chat, tools, speak=False):
        self.chat, self.tools, self.speak = chat, tools, speak

    def _translate(self, text, to_lang):
        table = {es.lower(): en for es, en in self.PAIRS} if to_lang == "en" else {en.lower(): es for es, en in self.PAIRS}
        whole = table.get(text.strip().lower())
        if whole:
            return whole
        out = []
        for sent in re.split(r"(?<=[.!?])\s+(?!-)", text.strip()):
            hit = table.get(sent.strip().lower())
            if hit is None:
                return None                       # an unknown sentence: do not guess
            out.append(hit)
        return " ".join(out)

    def _say_aloud(self, text, lang):
        if not self.speak:
            return
        voice = os.environ.get(f"LANTERN_VOICE_{lang.upper()}", self.VOICES.get(lang, ""))
        try:
            subprocess.Popen(["say", "-v", voice, text] if voice else ["say", text])
        except OSError:
            pass                                   # no speech on this machine: the text is still shown

    def handle(self, post):
        if self.mention not in post.message:
            return
        m = re.match(r"@interpreter Translate to English \(patient (\d+) wrote in (\w+)\), post (\S+): (.+)$", post.message, re.S)
        if m and post.room == NURSE:
            pid, lang, post_id, text = m.groups()
            en = self._translate(text, "en")
            if en and self.tools.translate(self.name, {"kind": "patient_to_staff", "post_id": post_id, "text": en, "lang": lang}).get("ok"):
                self._say_aloud(en, "en")             # the nurse hears what the patient said
            return
        m = re.match(r"@interpreter Translate to (\w+) for patient (\d+) \(Case (\d+)\);.*?: (.+)$", post.message, re.S)
        if m and post.room == DOCTOR:
            lang, pid, case, text = m.groups()
            out = self._translate(text, lang)
            if out and self.tools.translate(self.name, {"kind": "doctor_to_patient", "case": int(case), "text": out, "lang": lang}).get("ok"):
                self._say_aloud(out, lang)            # the patient hears the doctor's words in their language


# ------------------------------------------------------------------ runner
class Runner:
    """Polls the rooms an agent belongs to and hands record-bot's posts to the agent."""

    def __init__(self, agent, chat, record_bot_id, rooms, interval=1.5):
        self.agent, self.chat, self.bot_id, self.rooms, self.interval = agent, chat, record_bot_id, rooms, interval
        self.cursor = {r: int(time.time() * 1000) for r in rooms}
        self.seen = set()

    def step(self):
        for room in self.rooms:
            posts, self.cursor[room] = self.chat.new_posts(room, self.cursor[room])
            for p in posts:
                if p.id in self.seen or p.user_id != self.bot_id:
                    continue
                self.seen.add(p.id)
                try:
                    self.agent.handle(p)
                except Exception as e:       # an agent hiccup must never stop the others
                    print(f"{self.agent.name}: {type(e).__name__}: {e}")

    def run(self):
        print(f"{self.agent.name}: watching {', '.join(self.rooms)}")
        while True:
            self.step()
            time.sleep(self.interval)


def main(which=("intake", "care-coordinator", "interpreter")):
    import threading

    from .chat import MattermostChat
    url, team, pw = os.environ["MM_URL"], os.environ.get("MM_TEAM", "lantern"), os.environ["LANTERN_TEST_PASSWORD"]
    tracking_file = Path(__file__).resolve().parent.parent / "data" / "tracking-demo.json"
    tracking = json.loads(tracking_file.read_text()) if tracking_file.exists() else {}
    tools = HttpTools(os.environ.get("LANTERN_SERVICE", "http://127.0.0.1:8099"))

    def login(name):
        req = urllib.request.Request(f"{url}/api/v4/users/login", method="POST", headers={"Content-Type": "application/json"},
                                     data=json.dumps({"login_id": name, "password": pw}).encode())
        return urllib.request.urlopen(req).headers["Token"]

    bot_id = MattermostChat(url, login("record-bot"), team).user_id("record-bot")
    threads = []
    for name in which:
        chat = MattermostChat(url, login(name), team)
        if name == "intake":
            agent, rooms = IntakeAgent(chat, tools), [NURSE]
        elif name == "interpreter":
            agent, rooms = InterpreterAgent(chat, tools, speak=os.environ.get("LANTERN_SPEAK") == "1"), [NURSE, DOCTOR]
        else:
            agent, rooms = CoordinatorAgent(chat, tools, tracking), [NURSE, DOCTOR]
        t = threading.Thread(target=Runner(agent, chat, bot_id, rooms).run, daemon=True)
        t.start()
        threads.append(t)
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        pass

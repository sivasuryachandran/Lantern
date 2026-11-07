"""Populate the ward with a day of scenarios through the Mattermost API, so every dashboard has something to show.

Plays the people only (patients, nurses, Dr. Lee, room service). The two agents must be running: the real Switch agents,
or the scripted stand-ins with `python -m lantern simagents` (say so on screen). Needs MM_URL, MM_TEAM,
LANTERN_TEST_PASSWORD and the record service running (scripts/start.sh).

  python scripts/ward_scenarios.py [--service http://127.0.0.1:8099]

Scenarios: 101 diet (full loop, a refused nurse DECIDE, dictated doctor advice with a draft, a dictated note filed by the scribe, a voice-set reminder, tray task closed by room service); 102 activity (confirmed, left open);
103 activity in Spanish (translated both ways, decided, double medicine entry, discharge with part of the turnover done); 104 (nurse rejects); a patient asking
about someone else's case (refused); shift change handing over three cases.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("--real", action="store_true", help="accepted for compatibility; the agents are always external now")
ap.add_argument("--service", default=os.environ.get("LANTERN_SERVICE", "http://127.0.0.1:8099"))
args = ap.parse_args()
URL, TEAM, PW = os.environ["MM_URL"].rstrip("/"), os.environ.get("MM_TEAM", "lantern"), os.environ["LANTERN_TEST_PASSWORD"]
WAIT = 150
PACE = float(os.environ.get("LANTERN_PACE", "0"))   # seconds to pause before each human post, so a screen recording can follow


def call(token, method, path, body=None):
    req = urllib.request.Request(f"{URL}/api/v4{path}", method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read() or b"{}")


def login(name):
    req = urllib.request.Request(f"{URL}/api/v4/users/login", method="POST", headers={"Content-Type": "application/json"},
                                 data=json.dumps({"login_id": name, "password": PW}).encode())
    return urllib.request.urlopen(req).headers["Token"]


people = ["patient-101", "patient-102", "patient-103", "patient-104", "nurse-ana", "nurse-ben", "dr-lee", "service-sam", "service-rita", "record-bot"]
tok = {n: login(n) for n in people}
chan = {r: call(tok["record-bot"], "GET", f"/teams/name/{TEAM}/channels/name/{r}")["id"]
        for r in ("patient-101", "patient-102", "patient-103", "patient-104", "nurse-station", "doctor-review", "room-service")}
T0 = int(time.time() * 1000) - 1000


def api(path):
    with urllib.request.urlopen(f"{args.service}{path}") as r:
        return json.load(r)


def say(user, room, text, root=""):
    if PACE:
        print(f"@@ {room} {user}", flush=True)       # marker for the recorder: which room to show
        time.sleep(PACE)
    return call(tok[user], "POST", "/posts", {"channel_id": chan[room], "message": text, **({"root_id": root} if root else {})})["id"]


def posts(room):
    return sorted(call(tok["record-bot"], "GET", f"/channels/{chan[room]}/posts?per_page=200")["posts"].values(), key=lambda p: p["create_at"])


def wait(room, pred, what, after=None):
    end = time.time() + WAIT
    while time.time() < end:
        for p in posts(room):
            if p["create_at"] >= (after or T0) and pred(p):
                return p
        time.sleep(1)
    sys.exit(f"FAIL: timed out waiting for {what} in {room}")


def lookup(patient, entry):
    with urllib.request.urlopen(f"{args.service}/chart/{patient}/{entry}?agent=care-coordinator") as r:
        return json.load(r)


def concern(patient, text, quote, topic):
    """The patient mentions something; intake flags it; the service opens a case. Returns (case number, nurse thread root)."""
    chart = api(f"/api/patients/{patient}/chart")
    order = next(o for o in chart["orders"] if o["type"] == topic and o["status"] == "active")
    t = int(time.time() * 1000) - 500
    orig = say(f"patient-{patient}", f"patient-{patient}", text)
    fwd = wait("nurse-station", lambda p: orig in p["message"] and "@intake" in p["message"], "forward to intake", t)
    root = wait("nurse-station", lambda p: "possible discrepancy (unconfirmed)" in p["message"] and p["create_at"] > fwd["create_at"], "case root", t)
    n = int(re.match(r"Case (\d+)", root["message"]).group(1))
    print(f"  patient {patient}: Case {n} opened ({topic})")
    return n, root["id"], order["id"], chart["chart_version"]


def confirm(n, root, quote, order, patient):
    say("nurse-ana", "nurse-station", f"CONFIRM Case {n}", root)
    d = wait("doctor-review", lambda p: "nurse-confirmed conflict" in p["message"] and f"Case {n}" in p["message"], "doctor thread")
    return d["id"]


def decide(n, droot, version, topic, value, explain, user="dr-lee"):
    say(user, "doctor-review", f"DECIDE Case {n} v{version} {topic}={value}\nEXPLAIN: {explain}", droot)


print("101: diet, the full loop")
c101, r101, o101, v101 = concern("101", "Can't wait for breakfast. Dr. Lee said it's fine now that my procedure moved.",
                                  "Dr. Lee said it's fine now that my procedure moved", "diet")
d101 = confirm(c101, r101, "Dr. Lee said it's fine now that my procedure moved", o101, "101")
decide(c101, d101, v101, "diet", "regular", "Your procedure moved to Thursday, so you can eat normally today. - Dr. Lee", user="nurse-ana")   # refused
time.sleep(2)
# Dr. Lee speaks (dictated with Wispr Flow in the real thing); record-bot records advice, not a decision, and offers a draft
say("dr-lee", "doctor-review", f"ADVICE Case {c101}: She can have a regular diet today, her procedure moved to Thursday.", d101)
wait("doctor-review", lambda p: "Advice recorded" in p["message"] and f"Case {c101}" in p["message"], "advice recorded")
decide(c101, d101, v101, "diet", "regular", "Your procedure moved to Thursday, so you can eat normally today. - Dr. Lee")   # she sends the decision herself
wait("patient-101", lambda p: "you can eat normally today" in p["message"], "doctor's words")
say("nurse-ana", "nurse-station", f"GIVEN Case {c101} anti-nausea (fictional) 18:10", r101)
say("nurse-ana", "nurse-station", f"NOTE Case {c101}: She ate half of it and said the soup was too salty. Remind me to check again in 20 min.", r101)   # dictated with Wispr
wait("nurse-station", lambda p: p["message"].startswith("Filed on the shift record") and "REMIND Case" in p["message"], "scribe drafts a reminder")
say("nurse-ana", "nurse-station", f"REMIND Case {c101} in 1 min check she ate without nausea", r101)      # dictated with Wispr in the real thing
wait("nurse-station", lambda p: p["message"].startswith(f"Reminder set for") and f"Case {c101}" in p["message"], "reminder set")
tray = f"T-101-D{c101}"
wait("room-service", lambda p: tray in p["message"], "tray task")
say("nurse-ana", "room-service", f"DONE {tray}")      # refused: only room service closes a tray task
time.sleep(2)
say("service-sam", "room-service", f"DONE {tray}")

print("102: activity, confirmed and left open")
q = "The nurse said I can walk to the bathroom on my own now"
c102, r102, o102, v102 = concern("102", f"{q}.", q, "activity")
confirm(c102, r102, q, o102, "102")
say("nurse-ana", "nurse-station", f"GIVEN Case {c102} pain relief (fictional) 06:05", r102)

print("103: activity decided, a double medicine entry, discharge")
q = "El fisioterapeuta dijo que puedo sentarme en la silla para el almuerzo"     # patient 103 writes in Spanish
c103, r103, o103, v103 = concern("103", f"Buenos días. {q}.", q, "activity")
wait("nurse-station", lambda p: p["message"].startswith("Translation (es→en)") and "sit in the chair" in p["message"], "translation for the nurse")
d103 = confirm(c103, r103, q, o103, "103")
decide(c103, d103, v103, "activity", "chair", "Sitting in the chair for lunch is fine with someone beside you. - Dr. Lee")
wait("patient-103", lambda p: "Sitting in the chair" in p["message"], "doctor's words")
wait("patient-103", lambda p: p["message"].startswith("Translation (es)") and "Sentarse en la silla" in p["message"], "translation for the patient")
for t in ("08:00", "12:10"):
    say("nurse-ana", "nurse-station", f"GIVEN Case {c103} acetaminophen (fictional) {t}", r103)
time.sleep(2)
say("nurse-ana", "nurse-station", "DISCHARGE 103")
wait("room-service", lambda p: "Patient 103 discharged" in p["message"], "discharge tasks")
for i, who in ((1, "service-sam"), (2, "service-sam"), (3, "service-rita")):
    say(who, "room-service", f"DONE T-103-X1-{i}")
say("nurse-ana", "nurse-station", "READY 4W-103")
say("nurse-ana", "nurse-station", "READY 4W-102")

print("104: the nurse rejects")
q = "I think the salt limit is over for me today"
c104, r104, o104, v104 = concern("104", f"{q}.", q, "diet")
say("nurse-ben", "nurse-station", f"REJECT Case {c104} the patient was talking about yesterday", r104)

print("A patient asks about someone else's case")
say("patient-102", "patient-102", f"What happened in Case {c101}?")
wait("patient-102", lambda p: "only share updates about your own care" in p["message"], "refusal")

print("Shift change: three cases handed over")
for n, root, text in ((c101, r101, "confirm she ate without nausea"), (c102, r102, "awaiting Dr. Lee; fall risk, assist to bathroom"),
                      (c103, r103, "confirm she was comfortable in the chair")):
    say("nurse-ana", "nurse-station", f"HANDOFF Case {n} open: {text}", root)
    wait("nurse-station", lambda p, n=n: f"HANDOFF pending for Case {n}" in p["message"], f"handoff {n}")
    say("nurse-ben", "nurse-station", f"ACCEPT Case {n}", root)
    wait("nurse-station", lambda p, n=n: f"Case {n} follow-up accepted by nurse-ben" in p["message"], f"accept {n}")

print(f"\nWARD SCENARIOS DONE. Cases {c101} (101), {c102} (102), {c103} (103), {c104} (104). Dashboard: {args.service}/")

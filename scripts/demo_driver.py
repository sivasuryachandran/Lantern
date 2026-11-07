"""Paced Case 17 demo driver for recording. Plays the HUMAN roles (patient, nurses, doctor) in real Mattermost rooms.

  --real       intake and care-coordinator are the real Switch agents: this script only waits for them.
  --standins   (default if --real is absent) scripted accounts play the two agents. Say so in the video.
  --pause      wait for Enter before each step, so you control the timing on camera.
  --preroll    before the take: patient 102 asks about walking alone, intake flags it against ord-activity-1, nurse-ana confirms,
               the case is left open in doctor-review awaiting Dr. Lee, and nurse-ana records GIVEN 06:05. Then it stops.
               Run the normal flow afterwards for patient 101 (that becomes the next case number).

Needs MM_URL, MM_TEAM, LANTERN_TEST_PASSWORD, and the record service running (scripts/start.sh).
The dashboard at http://127.0.0.1:8099/ shows everything live.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("--real", action="store_true")
ap.add_argument("--pause", action="store_true")
ap.add_argument("--also", type=int, default=0, metavar="N", help="at shift change also hand off and accept the still-open case N (the pre-roll case)")
ap.add_argument("--preroll", action="store_true", help="v2 script: leave patient 102's activity case open and awaiting Dr. Lee, with a GIVEN at 06:05, then stop")
ap.add_argument("--delay", type=float, default=2.0, help="seconds between steps when not pausing")
ap.add_argument("--service", default=os.environ.get("LANTERN_SERVICE", "http://127.0.0.1:8099"))
args = ap.parse_args()
URL, TEAM, PW = os.environ["MM_URL"].rstrip("/"), os.environ.get("MM_TEAM", "switch"), os.environ["LANTERN_TEST_PASSWORD"]
WAIT = 120 if args.real else 30


def call(token, method, path, body=None):
    req = urllib.request.Request(f"{URL}/api/v4{path}", method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read() or b"{}")


def login(name):
    req = urllib.request.Request(f"{URL}/api/v4/users/login", method="POST",
                                 data=json.dumps({"login_id": name, "password": PW}).encode(),
                                 headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req).headers["Token"]


names = ["patient-101", "patient-102", "nurse-ana", "nurse-ben", "dr-lee", "record-bot"]
if not args.real:
    names += ["intake", "care-coordinator"]
tokens = {n: login(n) for n in names}
chan = {r: call(tokens["record-bot"], "GET", f"/teams/name/{TEAM}/channels/name/{r}")["id"]
        for r in ("patient-101", "patient-102", "nurse-station", "doctor-review")}


def say(user, room, text, root=""):
    return call(tokens[user], "POST", "/posts", {"channel_id": chan[room], "message": text, **({"root_id": root} if root else {})})["id"]


def posts(room):
    p = call(tokens["record-bot"], "GET", f"/channels/{chan[room]}/posts?per_page=200")
    return sorted(p["posts"].values(), key=lambda x: x["create_at"])


T0 = 0     # only posts created after the patient's message count, so old room history is ignored


def wait(room, pred, what, secs=WAIT):
    end = time.time() + secs
    while time.time() < end:
        for p in posts(room):
            if p["create_at"] >= T0 and pred(p):
                return p
        time.sleep(1)
    sys.exit(f"FAIL: timed out waiting for {what} in {room}")


def lookup(entry, patient="101"):
    with urllib.request.urlopen(f"{args.service}/chart/{patient}/{entry}?agent=care-coordinator") as r:
        return json.load(r)


def step(title):
    print(f"\n== {title}")
    if args.pause:
        input("   [Enter to run this step] ")
    else:
        time.sleep(args.delay)


T0 = int(time.time() * 1000) - 1000
if args.preroll:
    q2 = "The nurse said I can walk to the bathroom on my own now"
    step("Pre-roll 1. Patient 102 asks about walking alone")
    orig2 = say("patient-102", "patient-102", f"{q2}.")
    fwd2 = wait("nurse-station", lambda p: orig2 in p["message"] and "@intake" in p["message"], "forward to intake")
    step("Pre-roll 2. intake flags it" + ("" if args.real else " (STAND-IN)"))
    if not args.real:
        say("intake", "nurse-station", json.dumps({
            "patient_id": "102", "topic": "activity", "status": "possible_discrepancy", "patient_says": "believes walking alone is allowed",
            "quote": q2, "source": {"room": "patient-102", "original_post_id": orig2, "forwarded_post_id": fwd2["id"]},
            "conflicts_with": {"order_id": "ord-activity-1", "chart_version": 1}}))
    root2 = wait("nurse-station", lambda p: "possible discrepancy (unconfirmed)" in p["message"] and p["create_at"] > fwd2["create_at"], "case root")
    case2 = re.match(r"Case (\d+)", root2["message"]).group(1)
    step(f"Pre-roll 3. nurse-ana: CONFIRM Case {case2}")
    say("nurse-ana", "nurse-station", f"CONFIRM Case {case2}", root2["id"])
    droot2 = wait("doctor-review", lambda p: "nurse-confirmed conflict" in p["message"] and f"Case {case2}" in p["message"], "doctor thread")
    if not args.real:
        a = lookup("ord-activity-1", "102")
        say("care-coordinator", "doctor-review", f"Case {case2}: patient quote \"{q2}\". Nurse-ana confirmed. Active activity order: {a['value']} {a['citation']}.", droot2["id"])
    step(f"Pre-roll 4. nurse-ana records GIVEN 06:05 on Case {case2}")
    say("nurse-ana", "nurse-station", f"GIVEN Case {case2} pain relief (fictional) 06:05", root2["id"])
    wait("nurse-station", lambda p: "Recorded: pain relief" in p["message"], "GIVEN recorded")
    print(f"\nPRE-ROLL DONE. Case {case2} (patient 102) is confirmed and left open, awaiting Dr. Lee. Do NOT decide it.")
    sys.exit(0)

quote = "Dr. Lee said it's fine now that my procedure moved"
step("1. Patient 101 tells the bedside tablet what Dr. Lee said")
T0 = int(time.time() * 1000) - 1000
orig = say("patient-101", "patient-101", f"Can't wait for breakfast. {quote}.")
fwd = wait("nurse-station", lambda p: orig in p["message"] and "@intake" in p["message"], "forward to intake")
print("   record-bot forwarded it to nurse-station, mentioning @intake")

step("2. intake posts its claim card" + ("" if args.real else " (STAND-IN)"))
if not args.real:
    say("intake", "nurse-station", json.dumps({
        "patient_id": "101", "topic": "diet", "status": "possible_discrepancy", "patient_says": "believes eating is allowed",
        "quote": quote, "source": {"room": "patient-101", "original_post_id": orig, "forwarded_post_id": fwd["id"]},
        "conflicts_with": {"order_id": "ord-diet-1", "chart_version": 3}}))
root = wait("nurse-station", lambda p: "possible discrepancy (unconfirmed)" in p["message"] and p["create_at"] > fwd["create_at"], "case root")
case = re.match(r"Case (\d+)", root["message"]).group(1)
print(f"   Case {case} opened; patient told their care team is checking")

step(f"3. nurse-ana: CONFIRM Case {case}")
say("nurse-ana", "nurse-station", f"CONFIRM Case {case}", root["id"])
droot = wait("doctor-review", lambda p: "nurse-confirmed conflict" in p["message"] and f"Case {case}" in p["message"], "doctor thread")
print("   escalated to doctor-review")

step("4. care-coordinator summarises with cited lookups" + ("" if args.real else " (STAND-IN calling the real lookup tool)"))
if not args.real:
    a, b = lookup("ord-diet-1"), lookup("proc-1")
    say("care-coordinator", "doctor-review",
        f"Case {case}: patient quote \"{quote}\". Nurse-ana confirmed. Active diet order: {a['value']} {a['citation']}. "
        f"Procedure now: {b['value']} {b['citation']}.", droot["id"])
wait("doctor-review", lambda p: p["root_id"] == droot["id"] and "✓" in p["message"], "evidence card")
print("   record-bot posted the evidence card")

step(f"5. dr-lee: DECIDE Case {case}")
say("dr-lee", "doctor-review", f"DECIDE Case {case} v3 diet=regular\nEXPLAIN: Your procedure moved to Thursday, so you can eat normally today. - Dr. Lee", droot["id"])
wait("patient-101", lambda p: "you can eat normally today" in p["message"], "doctor's words")
wait("patient-101", lambda p: "Following up: nurse-ana" in p["message"], "owner line")
print("   chart v3 -> v4; patient got the doctor's own words and who owns the follow-up")

step("6. Shift change: GIVEN, HANDOFF, ACCEPT")
say("nurse-ana", "nurse-station", f"GIVEN Case {case} anti-nausea (fictional) 18:10", root["id"])
say("nurse-ana", "nurse-station", f"HANDOFF Case {case} open: confirm patient ate without nausea", root["id"])
wait("nurse-station", lambda p: "HANDOFF pending" in p["message"], "handoff")
if args.real:
    print("   (waiting for the care-coordinator brief is optional; continuing)")
say("nurse-ben", "nurse-station", f"ACCEPT Case {case}", root["id"])
wait("patient-101", lambda p: "Following up: nurse-ben" in p["message"], "owner change")
print("   owner is now nurse-ben")

if args.also:
    step(f"6b. The still-open Case {args.also} is handed over too")
    root_also = [p for p in posts("nurse-station") if p["message"].startswith(f"Case {args.also} ") and "possible discrepancy" in p["message"]][-1]
    say("nurse-ana", "nurse-station", f"HANDOFF Case {args.also} open: awaiting Dr. Lee; fall risk, assist to bathroom", root_also["id"])
    wait("nurse-station", lambda p: f"HANDOFF pending for Case {args.also}" in p["message"], "second handoff")
    say("nurse-ben", "nurse-station", f"ACCEPT Case {args.also}", root_also["id"])
    wait("nurse-station", lambda p: f"Case {args.also} follow-up accepted by nurse-ben" in p["message"], "second accept")
    print(f"   Case {args.also} is now owned by nurse-ben and is still awaiting Dr. Lee")

step("7. Isolation: patient-102 asks about 101's case")
say("patient-102", "patient-102", f"What happened in Case {case}?")
wait("patient-102", lambda p: "only share updates about your own care" in p["message"], "refusal")
try:
    call(tokens["patient-102"], "GET", f"/channels/{chan['patient-101']}/posts")
    sys.exit("FAIL: patient-102 could read patient-101's room")
except urllib.error.HTTPError as e:
    print(f"   patient-102 reading patient-101's room -> HTTP {e.code}")

print(f"\nDEMO DRIVER DONE. Case {case}. Run: python -m lantern timeline 101 nurse")

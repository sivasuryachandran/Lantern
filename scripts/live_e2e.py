"""Drive Case 17 through a real Mattermost with scripted accounts, with `python -m lantern run` as record-bot.

The intake account is a SCRIPTED STAND-IN for the Switch agent (it copies the quote with a fixed rule); this
verifies the service, the Mattermost client and the room/thread plumbing, not the LLM or Switch itself.
Needs MM_URL, MM_TEAM and LANTERN_TEST_PASSWORD (the password of the test accounts).
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL, TEAM, PW = os.environ["MM_URL"].rstrip("/"), os.environ.get("MM_TEAM", "lantern"), os.environ["LANTERN_TEST_PASSWORD"]


def call(token, method, path, body=None):
    req = urllib.request.Request(f"{URL}/api/v4{path}", method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read() or b"{}")


def login(name):
    req = urllib.request.Request(f"{URL}/api/v4/users/login", method="POST",
                                 data=json.dumps({"login_id": name, "password": PW}).encode(),
                                 headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req).headers["Token"]


tokens = {n: login(n) for n in ("patient-101", "patient-102", "nurse-ana", "nurse-ben", "dr-lee", "intake", "record-bot")}
chan = {r: call(tokens["record-bot"], "GET", f"/teams/name/{TEAM}/channels/name/{r}")["id"]
        for r in ("patient-101", "patient-102", "nurse-station", "doctor-review")}


def say(user, room, text, root=""):
    return call(tokens[user], "POST", "/posts", {"channel_id": chan[room], "message": text, **({"root_id": root} if root else {})})["id"]


def posts(room):
    p = call(tokens["record-bot"], "GET", f"/channels/{chan[room]}/posts?per_page=200")
    return sorted(p["posts"].values(), key=lambda x: x["create_at"])


def wait(room, pred, what, secs=30):
    end = time.time() + secs
    while time.time() < end:
        for p in posts(room):
            if pred(p):
                return p
        time.sleep(1)
    sys.exit(f"FAIL: timed out waiting for {what} in {room}")


def bot_said(room, text):
    return lambda p: text in p["message"]


db = str(Path(tempfile.mkdtemp()) / "live.db")
env = {**os.environ, "MM_TOKEN": tokens["record-bot"], "MM_TEAM": TEAM, "LANTERN_DB": db}
bot = subprocess.Popen([sys.executable, "-m", "lantern", "run"], cwd=ROOT, env=env)
try:
    time.sleep(3)
    quote = "Dr. Lee said it's fine now that my procedure moved"
    orig = say("patient-101", "patient-101", f"Can't wait for breakfast. {quote}.")
    fwd = wait("nurse-station", lambda p: orig in p["message"] and "@intake" in p["message"], "forward to intake")
    print("forwarded to nurse-station")
    say("intake", "nurse-station", json.dumps({
        "patient_id": "101", "topic": "diet", "status": "possible_discrepancy", "patient_says": "believes eating is allowed",
        "quote": quote, "source": {"room": "patient-101", "original_post_id": orig, "forwarded_post_id": fwd["id"]},
        "conflicts_with": {"order_id": "ord-diet-1", "chart_version": 3}}))
    root = wait("nurse-station", bot_said("nurse-station", "possible discrepancy (unconfirmed)"), "case root")
    wait("patient-101", bot_said("", "Your care team is checking this"), "patient ack")
    print("case opened and patient acknowledged")
    case = root["message"].split(":")[0].split()[-1]
    say("nurse-ana", "nurse-station", f"CONFIRM Case {case}", root["id"])
    droot = wait("doctor-review", bot_said("", "nurse-confirmed conflict"), "doctor thread")
    print("escalated to doctor-review")
    say("dr-lee", "doctor-review", f"DECIDE Case {case} v3 diet=regular\nEXPLAIN: Your procedure moved to Thursday, so you can eat normally today. - Dr. Lee", droot["id"])
    wait("patient-101", bot_said("", "you can eat normally today"), "doctor's words")
    wait("patient-101", bot_said("", "Following up: nurse-ana"), "owner line")
    print("decision applied, doctor's words and owner delivered")
    say("nurse-ana", "nurse-station", f"GIVEN Case {case} anti-nausea (fictional) 18:10", root["id"])
    say("nurse-ana", "nurse-station", f"HANDOFF Case {case} open: confirm patient ate without nausea", root["id"])
    wait("nurse-station", bot_said("", "HANDOFF pending"), "handoff")
    say("nurse-ben", "nurse-station", f"ACCEPT Case {case}", root["id"])
    wait("patient-101", bot_said("", "Following up: nurse-ben"), "owner change")
    print("handoff accepted, owner is nurse-ben")
    say("patient-102", "patient-102", f"What happened in Case {case}?")
    wait("patient-102", bot_said("", "only share updates about your own care"), "refusal")
    leaked = [p for p in posts("patient-102") if "Dr. Lee" in p["message"]]
    assert not leaked, "patient 102 saw clinician content"
    print("patient 102 refused")
    try:
        call(tokens["patient-102"], "GET", f"/channels/{chan['patient-101']}/posts")
        sys.exit("FAIL: patient-102 could read patient-101's room")
    except urllib.error.HTTPError as e:
        print(f"patient-102 reading patient-101's room -> HTTP {e.code} (blocked by room membership)")
    print("\nLIVE E2E PASSED")
finally:
    bot.terminate()

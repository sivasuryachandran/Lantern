"""Create the Lantern users and the four private rooms in the bundled Mattermost, per config/roles.yaml.

Needs an admin token:  MM_URL=http://localhost:8065 MM_ADMIN_TOKEN=... MM_TEAM=switch \
                       python scripts/setup_mattermost.py
Prints a personal access token for record-bot (put it in MM_TOKEN).
Agents (intake, care-coordinator) are created in the Switch console, not here: see docs/SWITCH_SETUP.md.
Test accounts only; every password is a throwaway for fictional users.
"""
import json
import os
import secrets
import urllib.error
import urllib.request
from pathlib import Path

import yaml

URL, TOKEN, TEAM = os.environ["MM_URL"].rstrip("/"), os.environ["MM_ADMIN_TOKEN"], os.environ.get("MM_TEAM", "switch")
PASSWORD = os.environ.get("LANTERN_TEST_PASSWORD") or "Lantern-" + secrets.token_urlsafe(9)
cfg = yaml.safe_load((Path(__file__).resolve().parent.parent / "config" / "roles.yaml").read_text())


def api(method, path, body=None, ok=(200, 201)):
    req = urllib.request.Request(f"{URL}/api/v4{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        if e.code in (400, 404, 409) and method == "GET":
            return None
        raise SystemExit(f"{method} {path} -> {e.code} {e.read().decode()[:200]}")


team = api("GET", f"/teams/name/{TEAM}") or api("POST", "/teams", {"name": TEAM, "display_name": TEAM, "type": "I"})
agents = {n for n, s in cfg["users"].items() if s["role"] == "agent"}
ids = {}
for name in cfg["users"]:
    if name in agents:
        u = api("GET", f"/users/username/{name}")
        if u is None:
            print(f"! agent '{name}' not found: create it in the Switch console first (docs/SWITCH_SETUP.md)")
            continue
    else:
        u = api("GET", f"/users/username/{name}") or api(
            "POST", "/users", {"username": name, "email": f"{name}@example.test",
                               "password": PASSWORD})
    ids[name] = u["id"]
    api("POST", f"/teams/{team['id']}/members", {"team_id": team["id"], "user_id": u["id"]})

for room, members in cfg["rooms"].items():
    ch = api("GET", f"/teams/name/{TEAM}/channels/name/{room}") or api(
        "POST", "/channels", {"team_id": team["id"], "name": room, "display_name": room, "type": "P"})
    for m in members:
        if m in ids:
            api("POST", f"/channels/{ch['id']}/members", {"user_id": ids[m]})
    print(f"room {room}: {', '.join(m for m in members if m in ids)}")

print(f"\nTest password for the accounts created now: {PASSWORD}  (throwaway, fictional users)")
try:
    tok = api("POST", f"/users/{ids['record-bot']}/tokens", {"description": "lantern record-bot"})
    print(f"export MM_URL={URL} MM_TEAM={TEAM} MM_TOKEN={tok['token']}")
except SystemExit as e:
    print(f"\nCould not create a record-bot token ({str(e)[:120]}).\n"
          "Enable System Console > Integrations > Enable Personal Access Tokens, then re-run,\n"
          "or use a login session token for record-bot as a stopgap (see README).")

"""record-bot runner: polls the four Mattermost rooms and feeds posts to the record service."""
import json
import os
import time
from pathlib import Path

from . import actions, integrations
from .chat import MattermostChat
from .roles import Roles
from .service import Service, connect, seed

ROOT = Path(__file__).resolve().parent.parent


def readonly(db_path=None):
    db = connect(db_path or os.environ.get("LANTERN_DB", str(ROOT / "lantern.db")))
    seed(db, ROOT / "data", 17)
    return Service(db, None, None)


def build(db_path=None):
    chat = MattermostChat(os.environ["MM_URL"], os.environ["MM_TOKEN"], os.environ.get("MM_TEAM", "switch"))
    roles = Roles(ROOT / "config" / "roles.yaml", chat)
    db = connect(db_path or os.environ.get("LANTERN_DB", str(ROOT / "lantern.db")))
    seed(db, ROOT / "data", roles.first_case_number)
    bad = roles.agents_in_patient_rooms()
    if bad:
        raise SystemExit(f"refusing to start: agents listed in patient rooms: {bad}")
    accounts = json.loads(os.environ.get("JIRA_ACCOUNTS", "{}"))      # {"nurse-ben": "<jira accountId>"}
    svc = Service(db, chat, roles, integrations=integrations.from_env(accounts),
                  action_url=os.environ.get("LANTERN_ACTION_URL", ""))
    return chat, svc


def run(interval=1.5):
    chat, svc = build()
    _, lock = actions.serve(svc, host=os.environ.get("LANTERN_BIND", "127.0.0.1"),
                            port=int(os.environ.get("LANTERN_ACTION_PORT", "8099")))
    rooms = [r for r in svc.roles.rooms if r.startswith("patient-")] + ["nurse-station", "doctor-review"]   # feed rooms are write-only
    print("record-bot running; rooms:", ", ".join(rooms), "| lookup tool: /chart/<patient>/<entry>",
          "| buttons:", bool(svc.action_url),
          "| integrations:", [type(i).__name__ for i in svc.integrations])
    while True:
        for room in rooms:
            key = f"cursor:{room}"
            row = svc.db.execute("SELECT v FROM meta WHERE k=?", (key,)).fetchone()
            since = int(row["v"]) if row else int(time.time() * 1000) - 60_000
            try:
                posts, cursor = chat.new_posts(room, since)
            except RuntimeError as e:
                print("poll error:", e)
                continue
            with lock:
                for p in posts:
                    svc.handle(p)
                svc.db.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (key, str(cursor)))
                svc.db.commit()
        time.sleep(interval)

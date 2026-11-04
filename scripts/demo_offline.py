"""Run Case 17 end to end against an in-memory chat (no Mattermost, no Switch) and print the transcript."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lantern import timeline  # noqa: E402
from lantern.scenario import full_run, make_env  # noqa: E402

chat, roles, db, svc = make_env()
full_run(chat, svc)
for p in chat.posts:
    thread = "  (thread)" if p["root_id"] else ""
    print(f"[{p['room']}] {p['user']}{thread}: {p['message']}\n")
print("=" * 70)
for role in ("patient", "nurse"):
    print(timeline.render(db, svc, "101", role))

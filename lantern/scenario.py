"""Case 17 against the in-memory chat. Shared by the tests and scripts/demo_offline.py."""
import json
import tempfile
from pathlib import Path

from .fake import FakeChat
from .roles import Roles
from .service import Service, connect, seed

ROOT = Path(__file__).resolve().parent.parent
QUOTE = "Dr. Lee said it's fine now that my procedure moved"
PATIENT_TEXT = f"Can't wait for breakfast. {QUOTE}."


def make_env(db_path=None):
    chat = FakeChat()
    roles = Roles(ROOT / "config" / "roles.yaml", chat)
    db = connect(db_path or str(Path(tempfile.mkdtemp()) / "lantern.db"))
    seed(db, ROOT / "data", roles.first_case_number)
    return chat, roles, db, Service(db, chat, roles)


def claim_card(svc, original_post_id, quote=QUOTE, topic="diet", version=3, order="ord-diet-1"):
    orig = svc.db.execute("SELECT * FROM said WHERE post_id=?", (original_post_id,)).fetchone()
    return json.dumps({"patient_id": orig["patient_id"], "topic": topic, "status": "possible_discrepancy",
                       "patient_says": "believes eating is allowed", "quote": quote,
                       "source": {"room": orig["room"], "original_post_id": original_post_id,
                                  "forwarded_post_id": orig["forwarded_post_id"]},
                       "conflicts_with": {"order_id": order, "chart_version": version}})


def open_case(chat, svc, text=PATIENT_TEXT, quote=QUOTE):
    """Patient speaks, intake posts a card. Returns (original post, case row)."""
    p = chat.say("patient-101", "patient-101", text)
    svc.handle(p)
    svc.handle(chat.say("intake", "nurse-station", claim_card(svc, p.id, quote)))
    case = svc.db.execute("SELECT * FROM cases WHERE original_post_id=?", (p.id,)).fetchone()
    return p, case


def confirm(chat, svc, case):
    svc.handle(chat.say("nurse-ana", "nurse-station", f"CONFIRM Case {case['id']}", case["nurse_root"]))
    return svc.case(case["id"])


def decide(chat, svc, case, version=3, user="dr-lee", root=None, room="doctor-review",
           text="Your procedure moved to Thursday, so you can eat normally today. - Dr. Lee"):
    msg = f"DECIDE Case {case['id']} v{version} diet=regular\nEXPLAIN: {text}"
    svc.handle(chat.say(user, room, msg, root if root is not None else case["doctor_root"]))
    return svc.case(case["id"])


def full_run(chat, svc):
    """Everything up to and including the incoming nurse's ACCEPT."""
    _, case = open_case(chat, svc)
    case = confirm(chat, svc, case)
    decide(chat, svc, case)
    n, root = case["id"], case["nurse_root"]
    svc.handle(chat.say("nurse-ana", "nurse-station", f"GIVEN Case {n} anti-nausea (fictional) 18:10", root))
    svc.handle(chat.say("nurse-ana", "nurse-station",
                        f"HANDOFF Case {n} open: confirm patient ate without nausea", root))
    svc.handle(chat.say("nurse-ben", "nurse-station", f"ACCEPT Case {n}", root))
    return svc.case(n)

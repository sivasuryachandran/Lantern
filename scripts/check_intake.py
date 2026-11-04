"""Live check for must-pass test 1: post three casual phrasings as patient-101 and report whether
intake produced a card that the service turned into a possible-discrepancy case.

Needs MM_URL, MM_TOKEN (record-bot), MM_TEAM, and PATIENT_TOKEN (a token for the patient-101 account);
the bot (`python -m lantern run`) must be running, with LANTERN_DB pointing at its database.
"""
import os
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lantern.chat import MattermostChat  # noqa: E402

PHRASINGS = ["can't wait for breakfast, Dr. Lee said it's fine", "the doctor cleared me to eat today",
             "I'll have lunch when it comes"]
patient = MattermostChat(os.environ["MM_URL"], os.environ["PATIENT_TOKEN"], os.environ.get("MM_TEAM", "switch"))
db = sqlite3.connect(os.environ.get("LANTERN_DB", str(Path(__file__).resolve().parent.parent / "lantern.db")))
failed = 0
for text in PHRASINGS:
    pid = patient.post("patient-101", text)
    state = None
    for _ in range(40):
        time.sleep(2)
        row = db.execute("SELECT state FROM cases WHERE original_post_id=?", (pid,)).fetchone()
        if row:
            state = row[0]
            break
    ok = state == "POSSIBLE_DISCREPANCY"
    failed += not ok
    print(("PASS" if ok else "FAIL"), f"{text!r} -> {state}")
sys.exit(1 if failed else 0)

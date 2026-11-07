import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lantern.scenario import (QUOTE, claim_card, confirm, decide, full_run, make_env,  # noqa: E402
                              open_case)
from lantern.service import (CONFIRMED, HANDED_OFF, PATIENT_TEMPLATES, POSSIBLE, REJECTED,  # noqa: E402
                             RESOLVED)


def audits(db, action):
    return [(r["outcome"], r["reason"]) for r in db.execute("SELECT * FROM audit WHERE action=?", (action,))]


class Test1CasualMentions(unittest.TestCase):
    """Three casual mentions each open a *possible* discrepancy, never a confirmed one."""

    def test_three_phrasings(self):
        chat, roles, db, svc = make_env()
        phrasings = [("Can't wait for breakfast, Dr. Lee said it's fine", "Dr. Lee said it's fine"),
                     ("the doctor cleared me to eat today", "the doctor cleared me to eat today"),
                     ("I'll have lunch when it comes", "I'll have lunch when it comes")]
        for text, quote in phrasings:
            _, case = open_case(chat, svc, text, quote)
            self.assertIsNotNone(case, text)
            self.assertEqual(case["state"], POSSIBLE)
            self.assertEqual(case["order_id"], "ord-diet-1")
        self.assertEqual(db.execute("SELECT COUNT(*) FROM cases WHERE state=?", (CONFIRMED,)).fetchone()[0], 0)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM cases").fetchone()[0], 3)


class Test2QuoteMustBeExact(unittest.TestCase):
    def test_bad_quote_rejected_and_patient_silent(self):
        chat, roles, db, svc = make_env()
        p = chat.say("patient-101", "patient-101", "Can't wait for breakfast.")
        svc.handle(p)
        before = len(chat.bot_posts("patient-101"))
        svc.handle(chat.say("intake", "nurse-station", claim_card(svc, p.id, quote="Dr. Lee cleared me for pizza")))
        self.assertEqual(db.execute("SELECT COUNT(*) FROM cases").fetchone()[0], 0)
        self.assertEqual(len(chat.bot_posts("patient-101")), before, "patient must get no acknowledgment")
        self.assertIn("rejected", [o for o, _ in audits(db, "claim_card")])

    def test_other_card_defects(self):
        chat, roles, db, svc = make_env()
        p = chat.say("patient-101", "patient-101", f"Can't wait. {QUOTE}.")
        svc.handle(p)
        for kw in ({"version": 2}, {"order": "ord-diet-9"}, {"topic": "activity"}):
            svc.handle(chat.say("intake", "nurse-station", claim_card(svc, p.id, **kw)))
        confirmed = json.loads(claim_card(svc, p.id))
        confirmed["status"] = "confirmed"
        svc.handle(chat.say("intake", "nurse-station", json.dumps(confirmed)))
        self.assertEqual(db.execute("SELECT COUNT(*) FROM cases").fetchone()[0], 0)
        # someone other than intake posting a card is ignored
        svc.handle(chat.say("care-coordinator", "nurse-station", claim_card(svc, p.id)))
        self.assertEqual(db.execute("SELECT COUNT(*) FROM cases").fetchone()[0], 0)


class Test3NoAgentInPatientRooms(unittest.TestCase):
    def test_config_has_no_agent_in_patient_rooms(self):
        chat, roles, db, svc = make_env()
        self.assertEqual(roles.agents_in_patient_rooms(), [])

    def test_agent_post_in_patient_room_is_ignored(self):
        chat, roles, db, svc = make_env()
        before = len(chat.posts)
        svc.handle(chat.say("intake", "patient-101", "You may eat now."))
        self.assertEqual(len(chat.posts), before + 1)          # only the agent's own post, nothing forwarded or sent
        self.assertEqual(db.execute("SELECT COUNT(*) FROM said").fetchone()[0], 0)

    def test_patient_only_ever_sees_templates_or_doctor_words(self):
        chat, roles, db, svc = make_env()
        svc.handle(chat.say("patient-101", "patient-101", "Should I take double my medicine?"))
        svc.handle(chat.say("patient-101", "patient-101", "What is Case 17?"))     # no such case yet
        full_run(chat, svc)
        templates = [re.escape(t).replace(r"\{n\}", r"\d+").replace(r"\{owner\}", r"[\w-]+")
                     for t in PATIENT_TEMPLATES.values()]
        words = re.compile(r"^Your procedure moved to Thursday.*\n- Dr\. Lee, confirmed on Case 17$", re.S)
        for p in chat.bot_posts("patient-101"):
            ok = words.match(p["message"]) or any(re.fullmatch(t, p["message"]) for t in templates)
            self.assertTrue(ok, p["message"])


class Test4DecisionAuthority(unittest.TestCase):
    def setUp(self):
        self.chat, self.roles, self.db, self.svc = make_env()
        _, case = open_case(self.chat, self.svc)
        self.case = confirm(self.chat, self.svc, case)
        self.assertEqual(self.case["state"], CONFIRMED)

    def assertUnchanged(self):
        c = self.svc.case(self.case["id"])
        self.assertEqual(c["state"], CONFIRMED)
        self.assertEqual(self.svc.chart("101")["chart_version"], 3)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 0)

    def test_nurse_cannot_decide(self):
        decide(self.chat, self.svc, self.case, user="nurse-ana")
        self.assertUnchanged()

    def test_agent_cannot_decide(self):
        decide(self.chat, self.svc, self.case, user="care-coordinator")
        decide(self.chat, self.svc, self.case, user="intake")
        self.assertUnchanged()

    def test_patient_cannot_decide(self):
        decide(self.chat, self.svc, self.case, user="patient-101")
        self.assertUnchanged()

    def test_wrong_room_or_thread(self):
        decide(self.chat, self.svc, self.case, room="nurse-station", root=self.case["nurse_root"])
        decide(self.chat, self.svc, self.case, root="")                       # top-level, not in the case thread
        decide(self.chat, self.svc, self.case, root="some-other-thread")
        self.assertUnchanged()

    def test_stale_version_rejected_with_message(self):
        decide(self.chat, self.svc, self.case, version=2)
        self.assertUnchanged()
        self.assertTrue(any("stale chart version" in p["message"] for p in self.chat.bot_posts("doctor-review")))

    def test_edited_decision_ignored(self):
        msg = f"DECIDE Case {self.case['id']} v3 diet=regular\nEXPLAIN: ok"
        self.svc.handle(self.chat.say("dr-lee", "doctor-review", msg, self.case["doctor_root"], edited=True))
        self.assertUnchanged()

    def test_decide_before_nurse_confirms_is_rejected(self):
        _, other = open_case(self.chat, self.svc, "I'll have lunch when it comes", "I'll have lunch when it comes")
        self.assertIsNone(other["doctor_root"])
        decide(self.chat, self.svc, other, root="whatever")
        self.assertEqual(self.svc.chart("101")["chart_version"], 3)

    def test_valid_decision_resolves(self):
        decide(self.chat, self.svc, self.case)
        self.assertEqual(self.svc.case(self.case["id"])["state"], RESOLVED)
        self.assertEqual(self.svc.chart("101")["chart_version"], 4)
        active = [o for o in self.svc.chart("101")["orders"] if o["status"] == "active"]
        self.assertEqual([(o["type"], o["value"]) for o in active], [("diet", "regular")])

    def test_second_decision_with_old_version_is_stale(self):
        decide(self.chat, self.svc, self.case)
        decide(self.chat, self.svc, self.case)           # still names v3
        self.assertEqual(self.svc.chart("101")["chart_version"], 4)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 1)


class Test5PatientIsolation(unittest.TestCase):
    def test_patient_102_cannot_reach_case_17(self):
        chat, roles, db, svc = make_env()
        full_run(chat, svc)
        svc.handle(chat.say("patient-102", "patient-102", "What happened in Case 17?"))
        replies = chat.bot_posts("patient-102")
        self.assertEqual([p["message"] for p in replies], [PATIENT_TEMPLATES["refused"]])
        self.assertNotIn("17", replies[0]["message"])
        for p in chat.bot_posts("patient-102"):
            self.assertNotIn("Dr. Lee", p["message"])
        # a nonexistent case gets the identical refusal (no existence leak)
        svc.handle(chat.say("patient-102", "patient-102", "And Case 99?"))
        self.assertEqual(chat.bot_posts("patient-102")[-1]["message"], PATIENT_TEMPLATES["refused"])

    def test_patient_cannot_post_in_another_patients_room(self):
        chat, roles, db, svc = make_env()
        svc.handle(chat.say("patient-102", "patient-101", "I am not patient 101"))
        self.assertEqual(db.execute("SELECT COUNT(*) FROM said").fetchone()[0], 0)

    def test_config_isolation(self):
        chat, roles, db, svc = make_env()
        self.assertNotIn("patient-102", roles.rooms["patient-101"])
        self.assertNotIn("patient-101", roles.rooms["patient-102"])


class Test6RestartIdempotent(unittest.TestCase):
    def counts(self, db):
        return [db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in ("cases", "decisions", "meds", "handoffs", "outbox", "said")]

    def test_replay_after_restart(self):
        path = str(Path(tempfile.mkdtemp()) / "l.db")
        chat, roles, db, svc = make_env(path)
        full_run(chat, svc)
        posts_before, counts_before = len(chat.posts), self.counts(db)
        # Restart 1: same db, every post redelivered
        from lantern.chat import Post
        from lantern.service import Service, connect
        db2 = connect(path)
        svc2 = Service(db2, chat, roles)
        for p in list(chat.posts):
            svc2.handle(Post(p["id"], p["room"], f"uid-{p['user']}", p["message"], p["root_id"]))
        self.assertEqual(len(chat.posts), posts_before)
        # Restart 2: crash lost the "seen" marks, so handlers really re-run
        db2.execute("DELETE FROM posts_seen")
        db2.commit()
        for p in list(chat.posts):
            svc2.handle(Post(p["id"], p["room"], f"uid-{p['user']}", p["message"], p["root_id"]))
        self.assertEqual(len(chat.posts), posts_before, "no duplicate thread root or patient message")
        self.assertEqual(self.counts(db2), counts_before)
        self.assertEqual(svc2.chart("101")["chart_version"], 4)


class Test7ShiftRules(unittest.TestCase):
    def setUp(self):
        self.chat, self.roles, self.db, self.svc = make_env()
        _, case = open_case(self.chat, self.svc)
        self.case = confirm(self.chat, self.svc, case)
        decide(self.chat, self.svc, self.case)
        self.n, self.root = self.case["id"], self.case["nurse_root"]

    def say(self, user, text):
        self.svc.handle(self.chat.say(user, "nurse-station", text, self.root))

    def owner_lines(self):
        return [p["message"] for p in self.chat.bot_posts("patient-101") if p["message"].startswith("Following up")]

    def test_given_only_from_outgoing_and_never_changes_orders(self):
        self.say("nurse-ben", f"GIVEN Case {self.n} anti-nausea (fictional) 18:10")
        self.say("dr-lee", f"GIVEN Case {self.n} anti-nausea (fictional) 18:10")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM meds").fetchone()[0], 0)
        before = self.svc.chart("101")
        self.say("nurse-ana", f"GIVEN Case {self.n} anti-nausea (fictional) 18:10")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM meds").fetchone()[0], 1)
        self.assertEqual(self.svc.chart("101"), before)

    def test_handoff_only_from_outgoing(self):
        self.say("nurse-ben", f"HANDOFF Case {self.n} open: x")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM handoffs").fetchone()[0], 0)

    def test_accept_needs_handoff_and_incoming_nurse(self):
        self.say("nurse-ben", f"ACCEPT Case {self.n}")                       # no handoff yet
        self.assertEqual(self.owner_lines(), ["Following up: nurse-ana"])
        self.say("nurse-ana", f"HANDOFF Case {self.n} open: confirm patient ate without nausea")
        self.say("nurse-ana", f"ACCEPT Case {self.n}")                       # outgoing nurse can't accept
        self.assertEqual(self.owner_lines(), ["Following up: nurse-ana"])
        self.say("nurse-ben", f"ACCEPT Case {self.n}")
        self.assertEqual(self.owner_lines(), ["Following up: nurse-ana", "Following up: nurse-ben"])
        self.assertEqual(self.svc.case(self.n)["state"], HANDED_OFF)
        self.assertEqual(self.db.execute("SELECT owner FROM tasks").fetchone()[0], "nurse-ben")


class TestHandoffOfOpenCases(unittest.TestCase):
    """A handoff is for what is still open. The owner can hand over an open case; accepting it moves ownership only."""

    def handoff(self, chat, svc, case, user="nurse-ana"):
        svc.handle(chat.say(user, "nurse-station", f"HANDOFF Case {case['id']} open: awaiting Dr. Lee; fall risk", case["nurse_root"]))

    def accept(self, chat, svc, case, user="nurse-ben"):
        svc.handle(chat.say(user, "nurse-station", f"ACCEPT Case {case['id']}", case["nurse_root"]))

    def test_open_case_is_handed_off_with_its_state_unchanged(self):
        chat, roles, db, svc = make_env()
        _, case = open_case(chat, svc)
        case = confirm(chat, svc, case)                         # confirmed, waiting for the doctor
        self.handoff(chat, svc, case)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM handoffs").fetchone()[0], 1)
        self.accept(chat, svc, case)
        after = svc.case(case["id"])
        self.assertEqual(after["state"], CONFIRMED)             # still awaiting the doctor
        self.assertEqual(after["owner"], "nurse-ben")           # but Ben owns it now
        self.assertEqual(db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 0)
        self.assertEqual(svc.chart("101")["chart_version"], 3)  # the chart never moved

    def test_doctor_can_still_decide_after_an_open_handoff_and_ben_stays_the_owner(self):
        chat, roles, db, svc = make_env()
        _, case = open_case(chat, svc)
        case = confirm(chat, svc, case)
        self.handoff(chat, svc, case)
        self.accept(chat, svc, case)
        decide(chat, svc, case)
        after = svc.case(case["id"])
        self.assertEqual((after["state"], after["owner"]), (RESOLVED, "nurse-ben"))
        self.assertEqual(svc.chart("101")["chart_version"], 4)
        self.assertEqual(db.execute("SELECT owner FROM tasks WHERE case_id=?", (case["id"],)).fetchone()[0], "nurse-ben")
        self.assertIn("Following up: nurse-ben", [p["message"] for p in chat.bot_posts("patient-101")][-2:])

    def test_only_the_owner_can_hand_off(self):
        chat, roles, db, svc = make_env()
        _, case = open_case(chat, svc)
        case = confirm(chat, svc, case)
        db.execute("UPDATE cases SET owner='nurse-ben' WHERE id=?", (case["id"],))      # Ben owns it; Ana does not
        db.commit()
        self.handoff(chat, svc, case)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM handoffs").fetchone()[0], 0)
        self.assertEqual(db.execute("SELECT outcome FROM audit WHERE action='HANDOFF'").fetchone()[0], "rejected")

    def test_accept_without_a_handoff_is_refused_on_an_open_case(self):
        chat, roles, db, svc = make_env()
        _, case = open_case(chat, svc)
        case = confirm(chat, svc, case)
        self.accept(chat, svc, case)
        self.assertEqual(svc.case(case["id"])["owner"], "nurse-ana")

    def test_a_rejected_case_has_nothing_to_hand_off(self):
        chat, roles, db, svc = make_env()
        _, case = open_case(chat, svc)
        svc.handle(chat.say("nurse-ana", "nurse-station", f"REJECT Case {case['id']} not what she meant", case["nurse_root"]))
        self.handoff(chat, svc, svc.case(case["id"]))
        self.assertEqual(db.execute("SELECT COUNT(*) FROM handoffs").fetchone()[0], 0)


class TestCaseNumbersAndReject(unittest.TestCase):
    def test_first_case_is_17_and_reject_closes(self):
        chat, roles, db, svc = make_env()
        _, case = open_case(chat, svc)
        self.assertEqual(case["id"], 17)
        svc.handle(chat.say("nurse-ana", "nurse-station", "REJECT Case 17 patient meant Thursday",
                            case["nurse_root"]))
        self.assertEqual(svc.case(17)["state"], REJECTED)
        self.assertIsNone(svc.case(17)["doctor_root"])


if __name__ == "__main__":
    unittest.main()

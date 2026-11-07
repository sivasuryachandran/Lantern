import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lantern.chat import Post  # noqa: E402
from lantern.scenario import confirm, decide, make_env, open_case  # noqa: E402
from lantern.simagents import CoordinatorAgent, IntakeAgent, Runner, ServiceTools  # noqa: E402
from lantern.service import CONFIRMED  # noqa: E402

BOT = "uid-record-bot"


class AgentChat:
    """What an agent's own Mattermost account can do: post as itself. The test feeds the post back to the service."""

    def __init__(self, chat, user):
        self.chat, self.user, self.sent = chat, user, []

    def post(self, room, message, root_id="", props=None):
        p = self.chat.say(self.user, room, message, root_id)
        self.sent.append(p)
        return p.id


def as_post(d):
    return Post(d["id"], d["room"], BOT, d["message"], d["root_id"])


class TestSimulatedAgents(unittest.TestCase):
    def setUp(self):
        self.chat, self.roles, self.db, self.svc = make_env()
        self.tools = ServiceTools(self.svc)
        self.intake_chat, self.coord_chat = AgentChat(self.chat, "intake"), AgentChat(self.chat, "care-coordinator")
        self.intake = IntakeAgent(self.intake_chat, self.tools)

    def patient_says(self, patient, text):
        p = self.chat.say(f"patient-{patient}", f"patient-{patient}", text)
        self.svc.handle(p)
        return p

    def forwarded(self):
        return as_post(next(x for x in reversed(self.chat.bot_posts("nurse-station")) if "@intake New message" in x["message"]))

    def open_case(self, text="Can't wait for breakfast. Dr. Lee said it's fine now that my procedure moved."):
        self.patient_says("101", text)
        self.intake.handle(self.forwarded())
        card = self.intake_chat.sent[-1]
        self.svc.handle(card)
        return self.db.execute("SELECT * FROM cases ORDER BY id DESC LIMIT 1").fetchone(), card

    def test_intake_flags_the_conflict_with_an_exact_quote_the_service_accepts(self):
        case, card = self.open_case()
        data = json.loads(card.message)
        self.assertEqual((data["topic"], data["status"], data["conflicts_with"]["order_id"]), ("diet", "possible_discrepancy", "ord-diet-1"))
        self.assertIn(data["quote"], "Can't wait for breakfast. Dr. Lee said it's fine now that my procedure moved.")
        self.assertEqual(case["state"], "POSSIBLE_DISCREPANCY")        # accepted by the real checks

    def test_intake_asks_the_nurse_in_the_case_thread_and_says_nothing_without_a_conflict(self):
        case, _ = self.open_case()
        root = as_post(next(x for x in self.chat.bot_posts("nurse-station") if x["message"].startswith(f"Case {case['id']} ")))
        self.intake.handle(root)
        self.assertEqual(self.intake_chat.sent[-1].root_id, root.id)
        self.assertIn("CONFIRM", self.intake_chat.sent[-1].message)
        before = len(self.intake_chat.sent)
        self.patient_says("102", "My daughter is visiting at three.")
        self.intake.handle(self.forwarded())
        self.assertEqual(len(self.intake_chat.sent), before)

    def test_coordinator_summary_cites_lookups_and_the_service_checks_them(self):
        case, _ = self.open_case()
        case = confirm(self.chat, self.svc, dict(case) | {"nurse_root": case["nurse_root"]})
        root = as_post(next(x for x in self.chat.bot_posts("doctor-review") if "nurse-confirmed conflict" in x["message"]))
        CoordinatorAgent(self.coord_chat, self.tools).handle(root)
        summary = self.coord_chat.sent[-1]
        self.assertEqual(summary.root_id, root.id)                       # replies inside the thread
        self.assertIn("[ord-diet-1 v3", summary.message)
        self.assertIn("[proc-1 v3", summary.message)
        self.svc.handle(summary)
        checks = [e["text"] for e in self.db.execute("SELECT text FROM events WHERE kind='agent'")]
        self.assertTrue(any("2 of 2" in t and "verified" in t for t in checks), checks)

    def test_handoff_brief_reports_tracking_once_and_marks_it_simulated(self):
        case, _ = self.open_case()
        case = confirm(self.chat, self.svc, dict(case))
        decide(self.chat, self.svc, case)
        n = case["id"]
        self.svc.handle(self.chat.say("nurse-ana", "nurse-station", f"GIVEN Case {n} anti-nausea (fictional) 18:10", case["nurse_root"]))
        self.svc.handle(self.chat.say("nurse-ana", "nurse-station", f"HANDOFF Case {n} open: confirm she ate", case["nurse_root"]))
        pending = as_post(next(x for x in self.chat.bot_posts("nurse-station") if "HANDOFF pending" in x["message"]))
        tracking = {str(n): {"jira": {"ref": "KAN-5", "url": "https://x.example/KAN-5", "summary": "Case follow-up"},
                             "calendar": {"ref": "11:00", "summary": "Follow-up event"}}}
        agent = CoordinatorAgent(self.coord_chat, self.tools, tracking)
        agent.handle(pending)
        agent.handle(pending)
        brief = self.coord_chat.sent[-1].message
        self.assertIn("anti-nausea", brief)
        self.assertIn(f"ACCEPT Case {n}", brief)
        rows = self.db.execute("SELECT system, simulated FROM tracking ORDER BY system").fetchall()
        self.assertEqual([(r["system"], r["simulated"]) for r in rows], [("calendar", 1), ("jira", 1)])    # once, not twice
        self.assertTrue(any(e["kind"] == "tracking" for e in self.db.execute("SELECT kind FROM events WHERE case_id=?", (n,))))

    def test_only_a_known_agent_can_report_tracking(self):
        case, _ = self.open_case()
        body = {"case": case["id"], "system": "jira", "ref": "KAN-9", "summary": "x"}
        self.assertFalse(self.svc.record_tracking("nurse-ana", body)["ok"])
        self.assertFalse(self.svc.record_tracking("nobody", body)["ok"])
        self.assertTrue(self.svc.record_tracking("care-coordinator", body)["ok"])

    def test_runner_acts_only_on_record_bots_posts(self):
        seen = []

        class Agent:
            name = "x"

            def handle(self, p):
                seen.append(p.id)

        class Chat:
            def new_posts(self, room, since):
                return [Post("a", room, BOT, "m"), Post("b", room, "uid-nurse-ana", "m")], since + 1

        r = Runner(Agent(), Chat(), BOT, ["nurse-station"])
        r.step()
        r.step()
        self.assertEqual(seen, ["a"])                                    # not the nurse's post, and not twice


if __name__ == "__main__":
    unittest.main()


class TestInterpreter(unittest.TestCase):
    ES_IN = "Buenos días. El fisioterapeuta dijo que puedo sentarme en la silla para el almuerzo."

    def setUp(self):
        from lantern.simagents import InterpreterAgent
        self.chat, self.roles, self.db, self.svc = make_env()
        self.agent_chat = AgentChat(self.chat, "interpreter")
        self.agent = InterpreterAgent(self.agent_chat, ServiceTools(self.svc))

    def bot(self, room, startswith):
        return next(as_post(x) for x in self.chat.bot_posts(room) if x["message"].startswith(startswith))

    def test_a_spanish_patient_message_is_translated_for_the_nurse_and_the_original_is_kept(self):
        self.svc.handle(self.chat.say("patient-103", "patient-103", self.ES_IN))
        self.agent.handle(self.bot("nurse-station", "@interpreter Translate to English"))
        said = [p["message"] for p in self.chat.bot_posts("nurse-station")]
        tr = next(m for m in said if m.startswith("Translation (es→en)"))
        self.assertIn("The physio said I can sit in the chair for lunch.", tr)
        self.assertTrue(any("@intake" in m and "sentarme" in m for m in said))          # the original is still what intake sees
        row = self.db.execute("SELECT * FROM translations").fetchone()
        self.assertEqual((row["kind"], row["lang"], row["agent"]), ("patient_to_staff", "es", "interpreter"))

    def test_an_english_patient_gets_no_translation_request(self):
        self.svc.handle(self.chat.say("patient-101", "patient-101", "Can't wait for breakfast."))
        self.assertFalse(any("@interpreter" in p["message"] for p in self.chat.bot_posts("nurse-station")))

    def test_the_doctors_words_reach_a_spanish_patient_beside_the_original(self):
        from lantern.scenario import claim_card
        p = self.chat.say("patient-103", "patient-103", self.ES_IN)
        self.svc.handle(p)
        quote = "El fisioterapeuta dijo que puedo sentarme en la silla para el almuerzo"
        chart = self.svc.chart("103")
        order = next(o for o in chart["orders"] if o["type"] == "activity" and o["status"] == "active")
        card = claim_card(self.svc, p.id, quote=quote, topic="activity", version=chart["chart_version"], order=order["id"])
        self.svc.handle(self.chat.say("intake", "nurse-station", card))
        case = self.db.execute("SELECT * FROM cases ORDER BY id DESC LIMIT 1").fetchone()
        case = confirm(self.chat, self.svc, case)
        decide(self.chat, self.svc, case, version=chart["chart_version"], text="Sitting in the chair for lunch is fine with someone beside you. - Dr. Lee")
        # (decide() sends diet=regular; this test only needs the translation request, so use the request the service posted)
        req = next((as_post(x) for x in self.chat.bot_posts("doctor-review") if x["message"].startswith("@interpreter Translate to es")), None)
        self.assertIsNotNone(req)
        self.agent.handle(req)
        room = [x["message"] for x in self.chat.bot_posts("patient-103")]
        self.assertTrue(any("Sitting in the chair" in m for m in room))                  # the doctor's own words, unchanged
        tr = next(m for m in room if m.startswith("Translation (es)"))
        self.assertIn("Sentarse en la silla para el almuerzo", tr)
        self.assertIn("The words above are the original", tr)

    def test_unknown_sentences_are_not_guessed_and_only_agents_can_report(self):
        self.svc.handle(self.chat.say("patient-103", "patient-103", "Tengo una pregunta rara."))
        self.agent.handle(self.bot("nurse-station", "@interpreter Translate to English"))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM translations").fetchone()[0], 0)
        body = {"kind": "patient_to_staff", "post_id": "p1", "text": "x", "lang": "es"}
        self.assertFalse(self.svc.record_translation("nurse-ana", body)["ok"])

    def test_it_reads_aloud_only_when_asked(self):
        from lantern import simagents
        spoken = []
        real = simagents.subprocess.Popen
        simagents.subprocess.Popen = lambda cmd, *a, **k: spoken.append(cmd)
        try:
            quiet = simagents.InterpreterAgent(self.agent_chat, ServiceTools(self.svc), speak=False)
            loud = simagents.InterpreterAgent(self.agent_chat, ServiceTools(self.svc), speak=True)
            quiet._say_aloud("hola", "es")
            self.assertEqual(spoken, [])
            loud._say_aloud("hola", "es")
            self.assertEqual(spoken[0][0], "say")
        finally:
            simagents.subprocess.Popen = real


class TestScribeAndShiftRecord(unittest.TestCase):
    def setUp(self):
        from lantern.simagents import ScribeAgent
        self.chat, self.roles, self.db, self.svc = make_env()
        _, self.case = open_case(self.chat, self.svc)
        self.case = confirm(self.chat, self.svc, self.case)
        self.agent_chat = AgentChat(self.chat, "scribe")
        self.scribe = ScribeAgent(self.agent_chat, ServiceTools(self.svc))

    def note(self, text, user="nurse-ana", root=None):
        root = self.case["nurse_root"] if root is None else root
        self.svc.handle(self.chat.say(user, "nurse-station", f"NOTE Case {self.case['id']}: {text}", root))

    def ack(self):
        return as_post(next(x for x in reversed(self.chat.bot_posts("nurse-station")) if x["message"].startswith("Note recorded")))

    def test_a_dictated_note_is_filed_as_a_note_and_changes_nothing(self):
        self.note("She said the soup was too salty.")
        self.assertIn("dictated note", [e["text"] for e in self.db.execute("SELECT text FROM events WHERE kind='note'")][0])
        self.assertEqual(self.svc.chart("101")["chart_version"], 3)
        self.assertEqual(self.svc.case(self.case["id"])["state"], CONFIRMED)
        self.assertIn("a note changes nothing", self.ack().message)

    def test_only_staff_in_the_case_thread_can_file_a_note(self):
        self.note("x", user="service-sam")
        self.note("x", root="")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM events WHERE kind='note'").fetchone()[0], 0)

    def test_the_scribe_files_it_and_drafts_a_reminder_but_cannot_send_one(self):
        self.note("She ate half of it. Remind me to check again in 20 min.")
        self.scribe.handle(self.ack())
        said = self.agent_chat.sent[-1].message
        self.assertIn("Filed on the shift record", said)
        self.assertIn(f"REMIND Case {self.case['id']} in 20 min", said)
        self.svc.handle(self.agent_chat.sent[-1])                      # even if it posted the draft as a command...
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM reminders").fetchone()[0], 0)   # ...nothing happens

    def test_a_note_without_a_time_gets_no_draft(self):
        self.note("The patient is calm.")
        self.scribe.handle(self.ack())
        self.assertNotIn("REMIND", self.agent_chat.sent[-1].message)

    def test_the_shift_record_holds_notes_decisions_and_refusals(self):
        self.note("She asked for tea.")
        decide(self.chat, self.svc, self.case, user="nurse-ana")       # refused
        decide(self.chat, self.svc, self.case)
        from lantern import shiftreport
        text = shiftreport.render(self.svc)
        for needle in ("# Lantern shift record", "DICTATED NOTE", "She asked for tea", "CLINICIAN CONFIRMED", "refused or ignored",
                       "only a verified doctor can decide"):
            self.assertIn(needle, text)
        self.assertIn("<pre>", shiftreport.render_html(self.svc))

    def test_the_scribe_updates_the_record_when_a_handoff_is_accepted(self):
        decide(self.chat, self.svc, self.case)
        n = self.case["id"]
        self.svc.handle(self.chat.say("nurse-ana", "nurse-station", f"HANDOFF Case {n} open: confirm she ate", self.case["nurse_root"]))
        self.svc.handle(self.chat.say("nurse-ben", "nurse-station", f"ACCEPT Case {n}", self.case["nurse_root"]))
        acc = as_post(next(x for x in self.chat.bot_posts("nurse-station") if "follow-up accepted" in x["message"]))
        self.assertIn("@scribe", acc.message)
        self.scribe.handle(acc)
        self.assertIn("api/report", self.agent_chat.sent[-1].message)

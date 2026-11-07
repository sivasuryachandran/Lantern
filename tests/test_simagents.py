import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lantern.chat import Post  # noqa: E402
from lantern.scenario import confirm, decide, make_env  # noqa: E402
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

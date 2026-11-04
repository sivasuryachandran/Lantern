import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lantern.integrations import GoogleCalendar, Jira  # noqa: E402
from lantern.scenario import claim_card, confirm, decide, full_run, make_env, open_case  # noqa: E402
from lantern.service import CONFIRMED, HANDED_OFF, POSSIBLE  # noqa: E402


class FakeHttp:
    def __init__(self):
        self.calls = []

    def __call__(self, method, url, body=None, headers=None):
        self.calls.append((method, url, body))
        return {"key": "LAN-7"} if "issue" in url and method == "POST" else {"id": "evt1"}


class TestIntegrations(unittest.TestCase):
    def test_jira_and_calendar_carry_case_and_owner(self):
        chat, roles, db, svc = make_env()
        http = FakeHttp()
        svc.integrations = [Jira("https://x.atlassian.net", "a@b.test", "tok", "LAN",
                                 {"nurse-ana": "acc-ana", "nurse-ben": "acc-ben"}, http),
                            GoogleCalendar("tok", "care", http=http)]
        full_run(chat, svc)
        create = [c for c in http.calls if c[0] == "POST" and "issue" in c[1]]
        self.assertEqual(len(create), 1)
        self.assertIn("Case 17", create[0][2]["fields"]["summary"])
        assigns = [c[2]["accountId"] for c in http.calls if c[0] == "PUT"]
        self.assertEqual(assigns, ["acc-ana", "acc-ben"])          # owner changes on ACCEPT
        cal = [c for c in http.calls if "calendar" in c[1]]
        self.assertEqual(len(cal), 1)
        self.assertIn("Case 17", cal[0][2]["summary"])
        self.assertIn("nurse-ana", cal[0][2]["description"])

    def test_integration_failure_does_not_block_loop(self):
        chat, roles, db, svc = make_env()
        def boom(*a, **k):
            raise OSError("down")
        svc.integrations = [Jira("https://x", "a", "t", "LAN", http=boom)]
        case = full_run(chat, svc)
        self.assertEqual(case["state"], HANDED_OFF)
        self.assertTrue(any("failed" in r["text"] for r in db.execute("SELECT text FROM events")))


class TestButtons(unittest.TestCase):
    def setUp(self):
        self.chat, self.roles, self.db, self.svc = make_env()
        self.svc.action_url = "http://bot:8099/action"

    def test_root_post_has_buttons_only_when_enabled(self):
        _, case = open_case(self.chat, self.svc)
        root = next(p for p in self.chat.posts if p["id"] == case["nurse_root"])
        names = [a["name"] for a in root["props"]["attachments"][0]["actions"]]
        self.assertEqual(names, ["Confirm", "Reject"])

    def test_click_uses_verified_user_and_same_checks(self):
        _, case = open_case(self.chat, self.svc)
        ctx = {"command": "CONFIRM", "case": case["id"]}
        self.assertIn("Not allowed", self.svc.handle_action("uid-patient-101", ctx))
        self.assertIn("Not allowed", self.svc.handle_action("uid-intake", ctx))
        self.assertEqual(self.svc.case(case["id"])["state"], POSSIBLE)
        self.assertEqual(self.svc.handle_action("uid-nurse-ana", ctx), "Done.")
        self.assertEqual(self.svc.case(case["id"])["state"], CONFIRMED)

    def test_accept_button_only_works_for_incoming_nurse(self):
        _, case = open_case(self.chat, self.svc)
        case = confirm(self.chat, self.svc, case)
        decide(self.chat, self.svc, case)
        self.svc.handle(self.chat.say("nurse-ana", "nurse-station", f"HANDOFF Case 17 open: x", case["nurse_root"]))
        ctx = {"command": "ACCEPT", "case": 17}
        self.assertIn("Not allowed", self.svc.handle_action("uid-nurse-ana", ctx))
        self.assertEqual(self.svc.handle_action("uid-nurse-ben", ctx), "Done.")
        self.assertEqual(self.svc.case(17)["owner"], "nurse-ben")


class TestClip(unittest.TestCase):
    def test_claim_cites_clip_timestamp(self):
        chat, roles, db, svc = make_env()
        data = json.loads((Path(__file__).resolve().parent.parent / "data" / "clip-example.json").read_text())
        svc.ingest_clip("101", data["clip_id"], data["segments"])
        sid = "clip:bedside-1@9.8"
        quote = "Dr. Lee said it's fine now that my procedure moved"
        svc.handle(chat.say("intake", "nurse-station", claim_card(svc, sid, quote)))
        case = db.execute("SELECT * FROM cases").fetchone()
        self.assertEqual(case["original_post_id"], sid)
        src = db.execute("SELECT source FROM events WHERE kind='said' AND text LIKE ?", ("%breakfast%",)).fetchone()
        self.assertEqual(src["source"], "clip bedside-1 @ 9.8s")


if __name__ == "__main__":
    unittest.main()


class TestEvidenceReceipts(unittest.TestCase):
    """Code decides what gets a check mark. Wrong value, missing receipt, wrong patient and stale version never do."""

    def setUp(self):
        self.chat, self.roles, self.db, self.svc = make_env()
        _, case = open_case(self.chat, self.svc)
        self.case = confirm(self.chat, self.svc, case)

    def coord(self, text, user="care-coordinator"):
        n = len(self.chat.bot_posts("doctor-review"))
        self.svc.handle(self.chat.say(user, "doctor-review", text, self.case["doctor_root"]))
        new = self.chat.bot_posts("doctor-review")[n:]
        return new[-1]["message"] if new else ""

    def lookup(self, entry="proc-1", agent="care-coordinator", patient="101"):
        return self.svc.lookup(agent, patient, entry)

    def test_verified_card_uses_logged_value_not_agent_words(self):
        r = self.lookup()
        out = self.coord(f"Procedure moved. {r['citation']}")
        self.assertIn("✓ Verified", out)
        self.assertIn("Fictional procedure: Thu 9:00", out)
        self.assertIn(f"lookup `#{r['lookup']}`", out)
        self.assertIn("unverified interpretation", out)

    def test_interpretation_is_never_verified(self):
        r = self.lookup()
        out = self.coord(f"So the patient can eat. [proc-1 v3 · lookup #{r['lookup']}]")
        self.assertIn("Everything else in the message above is unverified interpretation", out)
        self.assertNotIn("can eat", out.split("Source:")[0])

    def test_wrong_value_refused(self):
        r = self.lookup()
        out = self.coord(f"[proc-1 v3 · lookup #{r['lookup']} = Fri 9:00]")
        self.assertIn("wrong value", out)
        self.assertNotIn("✓", out)

    def test_missing_receipt_refused(self):
        self.assertIn("no lookup receipt", self.coord("The procedure moved to Thursday."))
        self.assertIn("no matching lookup #99", self.coord("[proc-1 v3 · lookup #99]"))
        self.assertNotIn("✓", self.coord("[proc-1 v3 · lookup #99]"))

    def test_wrong_entry_version_or_agent_refused(self):
        r = self.lookup()
        self.assertIn("is proc-1 v3, not ord-diet-1 v3", self.coord(f"[ord-diet-1 v3 · lookup #{r['lookup']}]"))
        self.assertIn("not proc-1 v2", self.coord(f"[proc-1 v2 · lookup #{r['lookup']}]"))
        other = self.lookup(agent="intake")
        self.assertIn("was made by intake", self.coord(f"[proc-1 v3 · lookup #{other['lookup']}]"))

    def test_wrong_patient_refused(self):
        r = self.svc.lookup("care-coordinator", "102", "ord-diet-2")
        out = self.coord(f"[ord-diet-2 v1 · lookup #{r['lookup']}]")
        self.assertIn("patient 102", out)
        self.assertNotIn("✓", out)

    def test_stale_version_refused_and_timeline_marks_it(self):
        r = self.lookup()
        decide(self.chat, self.svc, self.case)                       # chart is now v4
        out = self.coord(f"[proc-1 v3 · lookup #{r['lookup']}]")
        self.assertIn("stale", out)
        self.assertNotIn("✓", out)
        from lantern import timeline
        self.assertIn("STALE", timeline.render(self.db, self.svc, "101", "nurse"))

    def test_no_data_allowed_and_unknown_entry_not_logged(self):
        self.assertEqual(self.coord("NO DATA: no allergy list in the chart."), "")
        self.assertIsNone(self.lookup("nope-9"))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM lookups").fetchone()[0], 0)

    def test_agent_still_cannot_decide(self):
        decide(self.chat, self.svc, self.case, user="care-coordinator")
        self.assertEqual(self.svc.chart("101")["chart_version"], 3)

    def test_http_lookup_tool_logs_calls(self):
        import urllib.error
        import urllib.request
        from lantern import actions
        server, _ = actions.serve(self.svc, port=0)
        port = server.server_address[1]
        try:
            res = json.loads(urllib.request.urlopen(
                f"http://127.0.0.1:{port}/chart/101/proc-1?agent=care-coordinator").read())
            self.assertEqual((res["entry"], res["version"], res["lookup"]), ("proc-1", 3, 1))
            self.assertIn("lookup #1", res["citation"])
            for bad in ("/chart/101/proc-1?agent=patient-101", "/chart/101/proc-1?agent=nobody"):
                with self.assertRaises(urllib.error.HTTPError) as cm:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}{bad}")
                self.assertEqual(cm.exception.code, 403)
        finally:
            server.shutdown()
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM lookups").fetchone()[0], 1)


class TestTimelineViews(unittest.TestCase):
    def test_timeline_command_is_role_scoped(self):
        chat, roles, db, svc = make_env()
        full_run(chat, svc)
        svc.handle(chat.say("nurse-ben", "nurse-station", "TIMELINE 101"))
        out = chat.bot_posts("nurse-station")[-1]["message"]
        self.assertIn("NURSE CONFIRMED", out)
        self.assertIn("CLINICIAN CONFIRMED", out)
        before = len(chat.posts)
        svc.handle(chat.say("patient-101", "nurse-station", "TIMELINE 101"))      # a patient can't ask
        svc.handle(chat.say("intake", "nurse-station", "TIMELINE 101"))           # nor an agent
        self.assertEqual(len(chat.posts), before + 2)

    def test_html_view(self):
        from lantern import timeline
        chat, roles, db, svc = make_env()
        full_run(chat, svc)
        page = timeline.render_html(db, svc, "101", "nurse")
        self.assertIn("<table>", page)
        self.assertIn("Fictional data", page)
        self.assertNotIn("DRAFT", timeline.render_html(db, svc, "101", "patient"))

    def test_openers_are_short_and_commands_live_in_the_thread(self):
        chat, roles, db, svc = make_env()
        _, case = open_case(chat, svc)
        root = next(p for p in chat.posts if p["id"] == case["nurse_root"])
        self.assertNotIn("CONFIRM", root["message"])
        thread = [p for p in chat.bot_posts("nurse-station") if p["root_id"] == case["nurse_root"]]
        self.assertTrue(any("CONFIRM Case 17" in p["message"] for p in thread))


class TestBackendApi(unittest.TestCase):
    def setUp(self):
        import subprocess
        from lantern import actions
        self.chat, self.roles, self.db, self.svc = make_env()
        subprocess.run([sys.executable, str(Path(__file__).resolve().parent.parent / "scripts" / "seed_demo_db.py"),
                        self.db.execute("PRAGMA database_list").fetchone()[2]], check=True, capture_output=True)
        self.server, _ = actions.serve(self.svc, port=0)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()

    def get(self, path):
        import urllib.request
        with urllib.request.urlopen(self.base + path) as r:
            body = r.read().decode()
            return json.loads(body) if r.headers["Content-Type"].startswith("application/json") else body

    def test_seeded_history_and_next_case_is_17(self):
        self.assertEqual([c["id"] for c in self.get("/api/cases")], [14, 15, 16])
        self.assertEqual(len(self.get("/api/patients")), 4)
        _, case = open_case(self.chat, self.svc)
        self.assertEqual(case["id"], 17)

    def test_reads(self):
        self.assertEqual(self.get("/healthz")["status"], "ok")
        self.assertEqual(self.get("/api/patients/103/chart")["chart_version"], 5)
        self.assertEqual(self.get("/api/cases?state=REJECTED")[0]["patient_id"], "104")
        detail = self.get("/api/cases/14")
        self.assertEqual(detail["case"]["state"], "HANDED_OFF")
        self.assertTrue(detail["events"])

    def test_live_case_visible_through_api(self):
        full_run(self.chat, self.svc)
        self.assertEqual(self.get("/api/cases/17")["case"]["state"], "HANDED_OFF")
        self.assertEqual([v["version"] for v in self.get("/api/patients/101/chart/versions")], [3, 4])
        self.assertTrue(self.get("/api/audit"))
        self.assertIn("CLINICIAN CONFIRMED", self.get("/api/timeline/101?role=doctor"))
        self.assertIn("<table>", self.get("/api/timeline/101?role=nurse&format=html"))

    def test_patient_role_and_unknowns_refused(self):
        import urllib.error
        import urllib.request
        for path, code in (("/api/timeline/101?role=patient", 403), ("/api/cases/999", 404),
                           ("/api/patients/999/chart", 404), ("/api/nope", 404)):
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(self.base + path)
            self.assertEqual(cm.exception.code, code, path)

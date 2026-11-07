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
        create = [c for c in http.calls if c[0] == "POST" and "issue" in c[1]
                  and c[2]["fields"]["summary"].startswith("Case")]           # the case task; the tray task is tested apart
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

    def test_switch_progress_posts_get_no_receipt(self):
        for text in ("**Working… 13s**", "**Worked for 44s. 9 tool calls.**", "**Queued. Waiting for the agent to start…**",
                     "Starting a session to handle this — one moment."):
            self.assertEqual(self.coord(text), "", text)
        self.assertIn("no lookup receipt", self.coord("The patient may eat."))

    def test_lookup_label_marks_superseded_orders(self):
        self.assertEqual(self.lookup("ord-diet-1")["label"], "Diet order")
        self.svc.handle(self.chat.say("dr-lee", "doctor-review",
                                      "DECIDE Case 17 v3 diet=regular\nEXPLAIN: ok. - Dr. Lee", self.case["doctor_root"]))
        self.assertEqual(self.lookup("ord-diet-1")["label"], "Diet order (superseded)")

    def test_http_forwarded_id_lookup(self):
        import urllib.error
        import urllib.request
        from lantern import actions
        orig = self.db.execute("SELECT post_id, forwarded_post_id FROM said LIMIT 1").fetchone()
        server, _ = actions.serve(self.svc, port=0)
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            res = json.loads(urllib.request.urlopen(f"{base}/forwarded/{orig['post_id']}?agent=intake").read())
            self.assertEqual(res["forwarded_post_id"], orig["forwarded_post_id"])
            for bad, code in (("/forwarded/nope?agent=intake", 404), (f"/forwarded/{orig['post_id']}?agent=nobody", 403),
                              (f"/forwarded/{orig['post_id']}?agent=patient-101", 403)):
                with self.assertRaises(urllib.error.HTTPError) as cm:
                    urllib.request.urlopen(base + bad)
                self.assertEqual(cm.exception.code, code)
        finally:
            server.shutdown()


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

    def test_dashboard_page_is_served_and_only_reads_the_api(self):
        for path in ("/", "/ui"):
            page = self.get(path)
            self.assertIn("Lantern", page)
            self.assertIn("Fictional data, not for clinical use", page)
        self.assertNotIn("method:'POST'", self.get("/"))     # the page never writes

    def test_patient_role_and_unknowns_refused(self):
        import urllib.error
        import urllib.request
        for path, code in (("/api/timeline/101?role=patient", 403), ("/api/cases/999", 404),
                           ("/api/patients/999/chart", 404), ("/api/nope", 404)):
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(self.base + path)
            self.assertEqual(cm.exception.code, code, path)


class TestWardFeeds(unittest.TestCase):
    """Orders, medication and room-service are write-only staff feeds; nothing there can change the record."""

    def test_decision_reaches_orders_and_room_service_and_given_reaches_medication(self):
        chat, roles, db, svc = make_env()
        full_run(chat, svc)
        orders = [p["message"] for p in chat.bot_posts("orders")]
        self.assertEqual(len(orders), 1)
        self.assertIn("v3 -> v4", orders[0])
        self.assertIn("Dr. Lee", orders[0])
        tray = [p["message"] for p in chat.bot_posts("room-service")]
        self.assertEqual(len(tray), 1)
        self.assertIn("diet", tray[0])
        given = [p["message"] for p in chat.bot_posts("medication")]
        self.assertEqual(len(given), 1)
        self.assertIn("No order was changed", given[0])

    def test_refused_decision_posts_nothing_to_the_feeds(self):
        chat, roles, db, svc = make_env()
        _, case = open_case(chat, svc)
        case = confirm(chat, svc, case)
        decide(chat, svc, case, user="nurse-ana")          # a nurse cannot decide
        for room in ("orders", "room-service", "medication"):
            self.assertEqual(chat.bot_posts(room), [])

    def test_replay_does_not_duplicate_feed_posts(self):
        chat, roles, db, svc = make_env()
        _, case = open_case(chat, svc)
        case = confirm(chat, svc, case)
        post = chat.say("dr-lee", "doctor-review", f"DECIDE Case {case['id']} v3 diet=regular\nEXPLAIN: You can eat. - Dr. Lee",
                        case["doctor_root"])
        svc.handle(post)
        svc.handle(post)                                  # the same post delivered again after a restart
        self.assertEqual(len(chat.bot_posts("orders")), 1)
        self.assertEqual(len(chat.bot_posts("room-service")), 1)

    def test_feeds_have_no_agents_and_no_patients(self):
        chat, roles, db, svc = make_env()
        for room in ("orders", "medication", "room-service"):
            for member in roles.rooms[room]:
                self.assertIn(roles.by_name(member).role, ("nurse", "doctor", "bot", "service"))
        self.assertEqual(roles.agents_in_patient_rooms(), [])
        self.assertEqual(sorted(r for r in roles.rooms if r.startswith("patient-")),
                         ["patient-101", "patient-102", "patient-103", "patient-104"])


class TestRoomsAndRoomService(unittest.TestCase):
    def say_done(self, chat, svc, user, task, room="room-service"):
        svc.handle(chat.say(user, room, f"DONE {task}"))

    def test_rooms_hold_previous_occupant_and_turnover_state(self):
        chat, roles, db, svc = make_env()
        r = db.execute("SELECT * FROM rooms WHERE room='4W-102'").fetchone()
        self.assertEqual(r["patient_id"], "102")
        self.assertIn("contact precautions", r["prev_precautions"])
        states = {t["id"]: t["status"] for t in db.execute("SELECT * FROM room_tasks WHERE room='4W-102'")}
        self.assertEqual(states["T-102-1"], "done")
        self.assertEqual(states["T-102-3"], "open")

    def test_diet_decision_opens_a_tray_task_and_room_service_closes_it(self):
        chat, roles, db, svc = make_env()
        _, case = open_case(chat, svc)
        case = confirm(chat, svc, case)
        decide(chat, svc, case)
        task = db.execute("SELECT * FROM room_tasks WHERE source_case=?", (case["id"],)).fetchone()
        self.assertEqual((task["kind"], task["status"], task["room"]), ("tray", "open", "4W-101"))
        self.assertIn(f"DONE {task['id']}", chat.bot_posts("room-service")[-1]["message"])
        self.say_done(chat, svc, "service-sam", task["id"])
        done = db.execute("SELECT * FROM room_tasks WHERE id=?", (task["id"],)).fetchone()
        self.assertEqual((done["status"], done["done_by"]), ("done", "service-sam"))
        self.assertIn("Recorded", chat.bot_posts("room-service")[-1]["message"])
        kinds = [(e["kind"], e["actor"]) for e in db.execute("SELECT * FROM events WHERE case_id=?", (case["id"],))]
        self.assertIn(("service", "service-sam"), kinds)

    def test_only_room_service_can_close_a_task_and_only_once(self):
        chat, roles, db, svc = make_env()
        self.say_done(chat, svc, "nurse-ana", "T-102-3")
        self.say_done(chat, svc, "patient-101", "T-102-3", room="patient-101")
        self.assertEqual(db.execute("SELECT status FROM room_tasks WHERE id='T-102-3'").fetchone()["status"], "open")
        self.assertEqual(db.execute("SELECT outcome FROM audit WHERE action='DONE'").fetchone()["outcome"], "rejected")
        self.say_done(chat, svc, "service-rita", "T-102-3")
        self.say_done(chat, svc, "service-sam", "T-102-3")          # a second close does nothing
        self.assertEqual(db.execute("SELECT done_by FROM room_tasks WHERE id='T-102-3'").fetchone()["done_by"], "service-rita")
        self.say_done(chat, svc, "service-sam", "T-999-9")
        self.assertIn("No task", chat.bot_posts("room-service")[-1]["message"])

    def test_service_events_are_staff_only(self):
        chat, roles, db, svc = make_env()
        _, case = open_case(chat, svc)
        decide(chat, svc, confirm(chat, svc, case))
        from lantern import timeline
        self.assertIn("ROOM SERVICE", timeline.render(db, svc, "101", "nurse"))
        self.assertNotIn("ROOM SERVICE", timeline.render(db, svc, "101", "patient"))

    def test_jira_task_for_a_tray_change_uses_the_fake_http_layer(self):
        calls = []
        jira = Jira("https://x.example", "a@b.c", "tok", "LAN", http=lambda m, u, b=None, h=None: calls.append((m, u, b)) or {"key": "LAN-7"})
        chat, roles, db, svc = make_env()
        svc.integrations = [jira]
        _, case = open_case(chat, svc)
        decide(chat, svc, confirm(chat, svc, case))
        summaries = [c[2]["fields"]["summary"] for c in calls if c[1].endswith("/issue") and c[0] == "POST"]
        self.assertTrue(any(s.startswith("Room service 4W-101") for s in summaries))


class TestWholeWardExtras(unittest.TestCase):
    def nurse(self, chat, svc, text, user="nurse-ana"):
        svc.handle(chat.say(user, "nurse-station", text))

    def test_discharge_opens_a_turnover_checklist_for_room_service(self):
        chat, roles, db, svc = make_env()
        self.nurse(chat, svc, "DISCHARGE 103")
        ids = [r["id"] for r in db.execute("SELECT id FROM room_tasks WHERE id LIKE 'T-103-X1-%' ORDER BY id")]
        self.assertEqual(len(ids), 5)
        feed = chat.bot_posts("room-service")[-1]["message"]
        self.assertIn("Patient 103 discharged", feed)
        self.assertIn("DONE", feed)
        svc.handle(chat.say("service-sam", "room-service", f"DONE {ids[0]}"))
        self.assertEqual(db.execute("SELECT status FROM room_tasks WHERE id=?", (ids[0],)).fetchone()[0], "done")
        self.nurse(chat, svc, "DISCHARGE 103")                       # a second discharge is a new numbered checklist
        self.assertEqual(db.execute("SELECT COUNT(*) FROM room_tasks WHERE id LIKE 'T-103-X2-%'").fetchone()[0], 5)

    def test_only_nurses_can_start_a_discharge_and_unknown_patients_are_refused(self):
        chat, roles, db, svc = make_env()
        svc.handle(chat.say("service-sam", "nurse-station", "DISCHARGE 103"))
        self.nurse(chat, svc, "DISCHARGE 999")
        self.assertEqual(db.execute("SELECT COUNT(*) FROM room_tasks WHERE id LIKE 'T-103-X%'").fetchone()[0], 0)
        self.assertEqual(db.execute("SELECT outcome FROM audit WHERE action='DISCHARGE'").fetchone()[0], "rejected")

    def test_ready_answers_from_the_task_list_and_precautions(self):
        chat, roles, db, svc = make_env()
        self.nurse(chat, svc, "READY 4W-102")
        said = chat.bot_posts("nurse-station")[-1]["message"]
        self.assertIn("NOT ready", said)
        self.assertIn("T-102-3", said)
        self.assertIn("contact precautions", said)
        self.nurse(chat, svc, "READY 4W-103")
        self.assertIn("is READY", chat.bot_posts("nurse-station")[-1]["message"])

    def test_overdue_reminder_posts_once_per_task_and_is_off_without_a_threshold(self):
        import time
        chat, roles, db, svc = make_env()
        self.assertEqual(svc.remind_overdue(), 0)                    # unset means off
        svc.now = lambda: time.time() + 3 * 3600
        n = svc.remind_overdue(minutes=120)
        self.assertEqual(n, db.execute("SELECT COUNT(*) FROM room_tasks WHERE status='open'").fetchone()[0])
        before = len(chat.bot_posts("room-service"))
        svc.remind_overdue(minutes=120)                              # keyed: no repeat
        self.assertEqual(len(chat.bot_posts("room-service")), before)

    def test_second_entry_for_the_same_medicine_is_flagged_not_blocked(self):
        chat, roles, db, svc = make_env()
        _, case = open_case(chat, svc)
        case = confirm(chat, svc, case)
        for t in ("18:10", "18:40"):
            svc.handle(chat.say("nurse-ana", "nurse-station", f"GIVEN Case {case['id']} anti-nausea (fictional) {t}", case["nurse_root"]))
        self.assertEqual(db.execute("SELECT COUNT(*) FROM meds").fetchone()[0], 2)          # both kept
        warns = [p["message"] for p in chat.bot_posts("medication") if "Possible double entry" in p["message"]]
        self.assertEqual(len(warns), 1)

    def test_api_exposes_room_readiness(self):
        chat, roles, db, svc = make_env()
        from lantern import api
        import json as _json
        _, _, body = api.route(svc, "/api/rooms", {})
        rooms = {r["room"]: r for r in _json.loads(body)}
        self.assertFalse(rooms["4W-102"]["ready"])
        self.assertTrue(rooms["4W-103"]["ready"])
        self.assertIn("T-102-3", rooms["4W-102"]["open_tasks"])


class TestDictatedAdvice(unittest.TestCase):
    def say(self, chat, svc, user, text, root, room="doctor-review"):
        svc.handle(chat.say(user, room, text, root))

    def setup_case(self):
        chat, roles, db, svc = make_env()
        _, case = open_case(chat, svc)
        return chat, db, svc, confirm(chat, svc, case)

    def test_advice_is_recorded_as_advice_and_drafts_a_decide_without_applying_it(self):
        chat, db, svc, case = self.setup_case()
        self.say(chat, svc, "dr-lee", f"ADVICE Case {case['id']}: She can have a regular diet today, her procedure moved to Thursday.", case["doctor_root"])
        self.assertEqual(svc.chart("101")["chart_version"], 3)                       # nothing changed
        self.assertEqual(db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], 0)
        kinds = [e["kind"] for e in db.execute("SELECT kind FROM events WHERE case_id=?", (case["id"],))]
        self.assertIn("advice", kinds)
        said = chat.bot_posts("doctor-review")[-1]["message"]
        self.assertIn("not a decision", said)
        self.assertIn("@care-coordinator", said)
        self.assertIn(f"DECIDE Case {case['id']} v3 diet=regular", said)
        self.assertEqual(svc.case(case["id"])["state"], CONFIRMED)

    def test_the_doctor_still_has_to_send_the_decide_herself(self):
        chat, db, svc, case = self.setup_case()
        self.say(chat, svc, "dr-lee", f"ADVICE Case {case['id']}: regular diet today", case["doctor_root"])
        self.say(chat, svc, "care-coordinator", f"DECIDE Case {case['id']} v3 diet=regular\nEXPLAIN: agent draft", case["doctor_root"])
        self.assertEqual(svc.chart("101")["chart_version"], 3)                       # an agent's DECIDE counts for nothing
        decide(chat, svc, case)
        self.assertEqual(svc.chart("101")["chart_version"], 4)

    def test_only_a_doctor_in_the_case_thread_can_record_advice(self):
        chat, db, svc, case = self.setup_case()
        self.say(chat, svc, "nurse-ana", f"ADVICE Case {case['id']}: regular diet", case["doctor_root"])
        self.say(chat, svc, "dr-lee", f"ADVICE Case {case['id']}: regular diet", "")      # top-level, not the case thread
        self.assertEqual(db.execute("SELECT COUNT(*) FROM events WHERE kind='advice'").fetchone()[0], 0)
        outcomes = [r[0] for r in db.execute("SELECT outcome FROM audit WHERE action='ADVICE'")]
        self.assertEqual(outcomes, ["rejected", "rejected"])

    def test_no_draft_when_the_words_name_no_change(self):
        chat, db, svc, case = self.setup_case()
        self.say(chat, svc, "dr-lee", f"ADVICE Case {case['id']}: Let's talk to the family first.", case["doctor_root"])
        said = chat.bot_posts("doctor-review")[-1]["message"]
        self.assertIn("no draft", said)
        self.assertNotIn("```", said)

    def test_advice_is_staff_only_on_the_timeline(self):
        chat, db, svc, case = self.setup_case()
        self.say(chat, svc, "dr-lee", f"ADVICE Case {case['id']}: regular diet today", case["doctor_root"])
        from lantern import timeline
        self.assertIn("DOCTOR ADVICE (dictated)", timeline.render(db, svc, "101", "doctor"))
        self.assertNotIn("DOCTOR ADVICE", timeline.render(db, svc, "101", "patient"))

    def test_replaying_the_same_advice_post_does_not_duplicate_the_reply(self):
        chat, db, svc, case = self.setup_case()
        post = chat.say("dr-lee", "doctor-review", f"ADVICE Case {case['id']}: regular diet today", case["doctor_root"])
        svc.handle(post)
        svc.handle(post)
        self.assertEqual(len([p for p in chat.bot_posts("doctor-review") if "Advice recorded" in p["message"]]), 1)

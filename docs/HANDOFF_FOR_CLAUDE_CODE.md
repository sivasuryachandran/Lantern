# Handoff for Member A (80%), written for Claude Code

**Read this file first, then do the work in order.** You are a Claude Code session on the teammate's machine. The repo is `https://github.com/sivasuryachandran/Lantern`. Your human owns the Switch, demo, video and submission work. The other teammate (Member B, 20%) does the nurse call, blog and #HowISwitch post. Do not do B's work.

**Deadline: Sat Nov 7, 10:29 AM PT. Target: submit Friday night (Nov 6).** Feature freeze Friday 3 PM PT.

---

## 0. What Lantern is, in 60 seconds

Lantern is a hackathon entry for *Flip the Switch* (track: Best Business Workflow). It is a hospital-style workflow on **fictional data**:

1. A patient posts a casual message in their own private Mattermost room (`patient-101`), e.g. that Dr. Lee said breakfast is fine, while the chart has an active **NPO (nothing by mouth) diet order** (`ord-diet-1`, chart v3) tied to procedure `proc-1`, which Dr. Lee moved to Thu 9:00. Exact demo wording is in `docs/DEMO_SCRIPT.md` and `lantern/scenario.py` (`PATIENT_TEXT`, `QUOTE`).
2. `record-bot` (plain Python code, not an agent) forwards it to `nurse-station` and mentions the **`intake`** agent.
3. `intake` (a Switch agent) replies with a JSON claim card. `record-bot` validates it in code and opens **Case 17** as a thread.
4. A nurse replies `CONFIRM Case 17`. `record-bot` mentions **`care-coordinator`** (a real coding agent) in `doctor-review`.
5. `care-coordinator` looks facts up via a local HTTP lookup tool and posts a summary with citations. `record-bot` posts ✓/⚠ evidence cards built from its own lookup log.
6. Only a verified doctor replying `DECIDE Case 17 ...` in the case thread changes the **simulated** chart.
7. Handoff between nurses (`HANDOFF` / `ACCEPT`), a timeline per role, patient isolation.

**Core rule: agents extract and route. Code decides. Only a doctor's DECIDE changes the chart.**

Rooms: `patient-101`, `patient-102`, `nurse-station`, `doctor-review`. No agent is ever in a patient room.
Agents: `intake` (nurse-station), `care-coordinator` (nurse-station + doctor-review). `record-bot` is code.

## 1. Hard rules (do not break these)

1. **Never loosen a safety check to make a demo pass.** If a real agent misbehaves, change the agent's instructions in `docs/agents/*.md` first. Decision validity requires: doctor role by user_id, room `doctor-review`, reply in that case's doctor thread, unedited post, current chart version, case in `CONFIRMED_CONFLICT`. Claim cards require: exact-substring quote of the patient's original post, matching active order, current chart version, status only `possible_discrepancy`.
2. **All data is fictional.** Keep the "Fictional data, not for clinical use" banners. Never add real patient data.
3. **Do not commit** `.venv/`, `*.db`, `__pycache__/`, tokens, passwords, or `.env` files. `.gitignore` already covers the first three. Never print or commit `LANTERN_TEST_PASSWORD` or any `MM_TOKEN`.
4. **No new runtime dependencies.** The service is stdlib + PyYAML only. No web framework.
5. **Do not add `intake` or `care-coordinator` to any `patient-*` room.** Switch must refuse intake in a patient room; that refusal is a demo scene.
6. **Do not claim things that are not verified.** If something has only run against scripted stand-ins, say so in the README ("Verification status"). Update that section honestly after each real run.
7. **The 47 tests must stay green.** Run them before every commit.
8. **Small commits**, clear messages. The history should show work during the event window.
9. **Do not do B's tasks** (nurse call, blog, #HowISwitch, cold README reproduction). Do not invent a nurse quote. If there is no real quote, the video's closing card is cut.

## 2. Repo map

```
lantern/
  service.py      core: SQLite schema, Service.handle, claim validation, commands, decide, lookup, citation verify
  bot.py          run(): polls rooms, starts HTTP server (port 8099), cursor stored in DB
  chat.py         MattermostChat (urllib REST) and Post dataclass
  actions.py      HTTP: GET /chart/<patient>/<entry>?agent=  (lookup tool), GET /api/..., POST /action (buttons)
  api.py          read-only REST over the DB
  roles.py        loads config/roles.yaml
  timeline.py     role-scoped timeline (Markdown / HTML)
  integrations.py optional Jira / Google Calendar (direct HTTP)
  fake.py         FakeChat used by tests
  scenario.py     helpers that script a Case 17 run
  __main__.py     CLI: run | timeline <p> <role> [--html] | chart <p> | lookup <p> <entry> <agent> | clip <p> <file>
config/roles.yaml usernames, roles, room membership, first_case_number: 17
data/             patient-101..104.json, clip-example.json
tests/            test_must_pass.py (24), test_extras.py (23)  -> 47 tests
scripts/          setup_mattermost.py, start.sh, check_intake.py, live_e2e.py, demo_offline.py, seed_demo_db.py
docs/             SWITCH_SETUP, DEMO_SCRIPT, SUBMISSION, TEAM_SPLIT, NURSE_REVIEW, BLOG, HOWISWITCH, VOICE_LOG, agents/
README.md         must stay accurate; "How Switch is used" is at the top
```

## 3. Environment setup (first 20 minutes)

```bash
git clone https://github.com/sivasuryachandran/Lantern.git
cd Lantern
python3 -m venv .venv
.venv/bin/pip install pyyaml
.venv/bin/python -m unittest discover -s tests          # expect: Ran 47 tests ... OK
.venv/bin/python scripts/demo_offline.py                # offline scripted Case 17, no Mattermost needed
```

If the tests do not pass on a clean clone, **stop and fix that first** (likely a Python version below 3.11 or missing PyYAML). Report the exact failure to your human.

Then Mattermost + Switch. Your human must do the Switch Console clicking; you prepare and verify.

1. Install/open **Switch** (Switch Console 0.40.1 was used). It bundles Mattermost. Note the Mattermost URL (the original developer used `http://localhost:8065`).
2. Create an admin account and a team. The scripts read `MM_TEAM` (default in `start.sh`: `lantern`).
3. Run the setup script (it creates users and the four private rooms from `config/roles.yaml`):

```bash
MM_URL=http://localhost:8065 MM_TEAM=lantern MM_ADMIN_TOKEN=<admin token> .venv/bin/python scripts/setup_mattermost.py
```

   - If the server has personal access tokens disabled, the script tells you; either enable them in System Console > Integrations, or use login session tokens (the E2E script and `start.sh` log in with a password).
   - The script prints a throwaway test password for the fictional accounts. **Keep it in your shell only** (`export LANTERN_TEST_PASSWORD=...`). Never commit it.
4. Create the two agents in the **Switch Console** using the instructions in `docs/agents/intake.md` and `docs/agents/care-coordinator.md`:
   - `intake`: nurse-station only.
   - `care-coordinator`: nurse-station and doctor-review. It must be a **real coding agent** (Claude Code or Codex) running on the same machine as the bot so it can `curl 127.0.0.1:8099`.
   - Their Mattermost usernames must match `config/roles.yaml`. If Switch assigns different names, **edit `config/roles.yaml`** and keep tests passing.
5. Start the record service:

```bash
export LANTERN_TEST_PASSWORD=<printed password>
scripts/start.sh
```

   `start.sh` logs `record-bot` in, seeds `lantern.db` with demo cases 14 to 16 if absent (so the next case is Case 17), and runs the bot plus the HTTP server on 127.0.0.1:8099.

## 4. Wednesday milestone: make the real loop work

Do these in order. After each one write what happened (real output) in a scratch note; you will use it for the README's verification status.

### 4.1 Lookup tool sanity (no agents needed)

```bash
curl -s "http://127.0.0.1:8099/healthz"
curl -s "http://127.0.0.1:8099/chart/101/proc-1?agent=care-coordinator"
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8099/chart/101/proc-1?agent=nobody"
```

Expect: health OK; JSON with `lookup` number and a `citation` like `[proc-1 v3 · lookup #31 = Thu 9:00]`; `403` for the unknown agent.

### 4.2 Intake check against the real agent

```bash
.venv/bin/python scripts/check_intake.py
```

It posts three casual phrasings as patient-101. **All three must produce a possible-discrepancy claim card** and a new case. If one fails:
- Read what `intake` actually replied (the nurse-station thread).
- Fix `docs/agents/intake.md` (stricter JSON-only instruction, quote must be copied verbatim from the patient's post, `status` must be `possible_discrepancy`, cite the active order). Re-paste the instructions into the Switch Console.
- Do **not** weaken `_claim_card` validation in `lantern/service.py`.

### 4.3 care-coordinator uses the lookup tool and cites exactly

Run Case 17 up to the nurse CONFIRM (section 4.4). In `doctor-review`, care-coordinator must:
- call the `curl` lookup (check `curl -s http://127.0.0.1:8099/api/lookups?agent=care-coordinator` afterwards), and
- paste the `citation` string **exactly**.

Then record-bot should post a card under that message with ✓ verified. If you only see ⚠, compare the cited text with the log: wrong value, wrong entry, wrong version, wrong patient, missing receipt and stale version are all (correctly) refused. Fix the agent instructions, not the verifier.

### 4.4 Full Case 17 by hand (this is the milestone)

As the humans (log in as each fictional user, or use the live E2E helper for stand-ins), perform:
1. patient-101 posts the casual diet message in `patient-101` (wording in `docs/DEMO_SCRIPT.md`).
2. record-bot forwards to `nurse-station` mentioning `@intake`.
3. intake posts a JSON claim card; record-bot opens **Case 17** and tells the patient it is under review.
4. nurse-ana replies `CONFIRM Case 17` in the case thread.
5. record-bot opens the doctor thread in `doctor-review`, mentions `@care-coordinator`.
6. care-coordinator posts quote + confirmation + cited facts; record-bot posts ✓ cards.
7. dr-lee replies in the doctor thread, exact grammar (`RE_DECIDE`, `lantern/service.py`), two lines, chart version must be current:

   ```
   DECIDE Case 17 v3 diet=regular
   EXPLAIN: Your procedure moved to Thursday, so you can eat normally today. - Dr. Lee
   ```
8. Chart version increments; patient is told the outcome; case is RESOLVED.
9. `.venv/bin/python -m lantern timeline 101 nurse` and `... patient` show the right rows; the patient view hides internal rows.

Also try these negative checks and confirm each is **refused**:
- `DECIDE` from a nurse; from a patient; outside `doctor-review`; as a new top-level post; in another case's thread; after editing the post; after the chart version changed.

### 4.5 Commit a checkpoint

```bash
.venv/bin/python -m unittest discover -s tests
git add -A && git commit -m "Wed: real intake + care-coordinator verified against live Switch"
git push
```

Update README "Verification status" to say exactly what ran live and what did not.

## 5. Thursday: harden the demo

- **Handoff scene:** exact grammar, in the nurse-station case thread: nurse-ana `GIVEN Case 17 anti-nausea (fictional) 18:10`, then `HANDOFF Case 17 open: confirm patient ate without nausea`; care-coordinator briefs nurse-ben; nurse-ben `ACCEPT Case 17`. Other commands: `CONFIRM Case 17`, `REJECT Case 17 <reason>`. Confirm tasks and timeline show ownership.
- **Isolation scene:** patient-102 cannot see `patient-101`; patient-102 posting about 101's order does not create a case on 101; Switch refuses to add `intake` to a patient room.
- **Three clean runs in a row** of the whole loop with the real agents. If any run differs, fix instructions and repeat. Keep a short log of the three runs (timestamps, case numbers).
- Fix whatever the real agents break by adjusting `docs/agents/`. If a code bug is found, add a failing test first, then fix.
- **Optional, cut first if behind:** interactive buttons, Jira, Google Calendar, clip ingest. Each is injectable/mocked in tests; none has been run live. Do not claim them as live in the README unless you ran them.
- Add or adjust must-pass tests in `tests/test_must_pass.py` if the runs reveal gaps.
- Any upstream Switch bug you hit: reproduce minimally and open an issue or PR upstream (counts toward Core Contribution). Capture the link.

## 6. Friday: video, README, submit

- Follow `docs/DEMO_SCRIPT.md` (timed storyboard, 2:30 to 2:45). Record from **real runs**, record-bot kept quiet on screen where the script says so. Do not stage with scripted stand-ins unless the video says so.
- The last 10 seconds are the nurse quote card from B. **No quote, no card.**
- README final pass: 30-second GIF, room diagram, trust model, fictional-data banner, "How Switch is used" matching the running code, paste B's nurse quote into "Nurse review", honest verification status.
- Save the Wispr Insights screenshot as `docs/wispr-scorecard.png` (human step). Use `docs/VOICE_LOG.md` for the voice-coding evidence.
- Final pass on `docs/SUBMISSION.md`. Submit on the event site before Friday night if possible.
- After 3 PM Friday: **fixes only**. Saturday morning is buffer.

## 7. Troubleshooting

| Symptom | Likely cause / fix |
| --- | --- |
| `could not log record-bot in` | `LANTERN_TEST_PASSWORD` unset/wrong, or MM_URL/MM_TEAM wrong |
| Tokens refused / 401 | Personal access tokens disabled on server; use login session tokens (`start.sh` does) or enable them |
| intake replies prose instead of JSON | Tighten `docs/agents/intake.md`; re-paste into Switch Console |
| Claim card rejected | Quote not an exact substring of the patient's post, or status not `possible_discrepancy`, or stale chart version. Fix the agent, not the validator |
| ⚠ on every citation | Agent did not call the lookup tool, edited the citation, or the bot restarted with a different DB. Check the `lookups` table |
| Agents reply to each other forever | An agent is set to answer every message; restrict to mentions. record-bot posts are ignored by the service |
| Bot replays old messages | Cursor in `meta` table; delete `lantern.db` and rerun `start.sh` for a fresh seed |
| Port 8099 busy | Another bot instance; stop it |
| Mattermost in Docker cannot reach button URL | Set `LANTERN_BIND=0.0.0.0` |

## 8. Known limits (keep documented honestly)

- Agent names in lookup requests are self-declared unless `LANTERN_LOOKUP_KEY` is set.
- If the process crashes mid-command, a follow-up message can be dropped; state itself is transactional.
- Jira, Google Calendar and Mattermost buttons were tested only with injected fakes. Real Switch agents had not been run at the time of this handoff.

## 9. Definition of done for Member A

- [ ] 47+ tests pass on a clean clone
- [ ] Real `intake` and `care-coordinator` created in Switch Console, usernames match `config/roles.yaml`
- [ ] `check_intake.py`: all three phrasings pass live
- [ ] care-coordinator calls the lookup tool and pastes citations exactly (✓ cards seen)
- [ ] Full Case 17 runs live **three times in a row**
- [ ] Handoff and isolation scenes work
- [ ] Final video recorded from real runs (2:30 to 2:45)
- [ ] README final pass, honest verification status, nurse quote pasted (if B delivered one)
- [ ] `docs/wispr-scorecard.png` saved; `docs/SUBMISSION.md` filled
- [ ] Submitted before Sat Nov 7, 10:29 AM PT

## 10. Reporting back to your human

After each numbered step in section 4 and each Thursday item, tell your human in two lines: what ran, what the real output was, and what is still unverified. If you are blocked on a human-only step (Switch Console clicks, Wispr screenshot, recording, submitting), say exactly what to click or do and wait.

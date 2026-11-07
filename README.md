# Lantern

**No concern left in the dark. What was said, what was confirmed, who owns what's next.**

> **Fictional data. Not for clinical use.** Every person and record here is invented. Lantern gives no medical advice, is not HIPAA-compliant, and is not an EHR. The "chart" is a small *simulated chart* inside Lantern.

Built for the Flip the Switch hackathon (WeMakeDevs × DevTools Academy × Switch).

Every morning at seven a nurse hands her patients to someone new, and that is when things get lost: nobody can see who owns what's next. Lantern is a ward built on Switch. Patients talk to a bedside tablet. AI agents notice a mismatch between what a patient says and what the chart says, and carry it to the nurse and the doctor. **Only a verified doctor's decision changes the record**, and nothing changes hands until the incoming nurse accepts.

## Watch the demo

**YouTube: https://youtu.be/QR7r84tyBlo**

[`recordings/final/lantern_demo_3min.mp4`](recordings/final/lantern_demo_3min.mp4) (2:52, captions in `.srt`). Chapters: [`chapters.txt`](recordings/final/chapters.txt). Every cut, speed change and insert: [`cutlist.md`](recordings/final/cutlist.md). What was and was not recorded: [`shotlist_actual.md`](recordings/final/shotlist_actual.md).

How honest the video is:

- All record-service posts, ✓ checks, refusals, chart changes and ownership changes are from one real run.
- Human roles (patients, nurses, Dr. Lee, room service) were played by our team's script.
- **The agent steps in the recording are the scripted stand-in agents** (`lantern/simagents.py`), captioned "stand-in mode (tests)". The two Switch Console agents were not answering Mattermost messages at recording time.
- The Wispr Flow bubbles are labelled re-enactments: the driver typed those commands.
- The Calendar and Jira inserts are screenshots of the real services, cropped to the events and the board.
- The first seconds use AI-generated concept footage, labelled as such.

## How it works

Three kinds of actor, each with one job:

| Actor | What it does | What it can never do |
| --- | --- | --- |
| **Agents** (Switch): `intake`, `care-coordinator`, plus `interpreter` and `scribe` | notice, quote, summarise with cited chart facts, translate, file notes | join a patient room, change the chart, say "resolved" |
| **record-bot** (plain code) | forwards patient messages, opens cases, posts ✓/⚠ checks from its own log, sends fixed patient templates and the doctor's own words | accept free-text from a patient as a command |
| **People** | confirm, decide, hand off, accept | decide outside their role |

The deterministic **record service** ([`lantern/service.py`](lantern/service.py)) is the only thing that changes the simulated chart. It matches on Mattermost `user_id`s resolved from [`config/roles.yaml`](config/roles.yaml), never on display names.

### The ward: nine private rooms

| Room | Who is in it | Purpose |
| --- | --- | --- |
| `patient-101` … `patient-104` | that patient, record-bot | bedside tablet. **No agent is ever a member** |
| `nurse-station` | nurses, intake, care-coordinator, record-bot | flag, confirm, hand off |
| `doctor-review` | Dr. Lee, Nurse Ana, care-coordinator, record-bot | evidence with receipts, then the decision |
| `orders` | doctor, nurses, record-bot | write-only feed of every chart change |
| `medication` | nurses, doctor, record-bot | write-only feed of every `GIVEN` |
| `room-service` | Sam and Rita, nurses, record-bot | tray and turnover tasks, closed with `DONE <id>` by room service only |

### Case 17 in one minute

1. Patient 101 on the tablet: "Can't wait for breakfast. Dr. Lee said it's fine now." The chart says `diet = NPO` (v3).
2. record-bot forwards it to `nurse-station`. **intake** posts a *possible* discrepancy quoting the patient word for word. The service checks the quote is an exact substring of the original post and opens Case 17.
3. The nurse replies `CONFIRM Case 17`. record-bot opens the thread in `doctor-review`; **care-coordinator** summarises the chart facts, and each cited fact gets a ✓ receipt from the lookup log. The ✓ means "matches the logged lookup", not "medically right".
4. A nurse who tries `DECIDE` is refused by code. Dr. Lee's `DECIDE Case 17 v3 diet=regular` plus `EXPLAIN:` is verified (author, role, room, thread, unedited, current version), the chart moves v3 → v4, and the patient receives Dr. Lee's own words.
5. The decision opens a tray task in `room-service`; only room service can close it.
6. At shift change the owner posts `HANDOFF`, the coordinator briefs the incoming nurse, and ownership moves only on `ACCEPT`.

### Commands

`CONFIRM`, `REJECT`, `DECIDE … EXPLAIN:`, `GIVEN`, `HANDOFF`, `ACCEPT`, `ADVICE` (dictated doctor advice, recorded as advice with a draft `DECIDE`), `NOTE` (dictated note, never an order), `REMIND`, `DONE`, `DISCHARGE`, `READY`, `TIMELINE`. They are designed to be spoken with Wispr Flow; see [docs/WISPR.md](docs/WISPR.md).

### Trust model

- A claim is rejected unless its `quote` is an exact substring of the patient's post, it names an active order of that topic, and it cites the current chart version.
- A decision counts only from a user listed as `doctor`, in `doctor-review`, as an unedited reply in that case's thread, naming the current chart version, on a nurse-confirmed case.
- Everything a patient sees from the service is a fixed template, the doctor's own words, or a translation labelled as one.
- Every side effect is keyed and idempotent: a restart creates no duplicate case or message.

## Run it

Python 3.11+ and PyYAML.

```bash
python3 -m venv .venv && .venv/bin/pip install pyyaml
.venv/bin/python -m unittest discover -s tests          # 98 tests, no network
.venv/bin/python scripts/demo_offline.py                # the whole case with no Mattermost
```

With Switch and its bundled Mattermost running, follow [docs/SWITCH_SETUP.md](docs/SWITCH_SETUP.md): create the agents (instructions in [`docs/agents/`](docs/agents)), run `scripts/setup_mattermost.py`, then:

```bash
export MM_URL=http://localhost:8065 MM_TEAM=lantern LANTERN_TEST_PASSWORD=...   # throwaway test password
scripts/start.sh                                         # record service, dashboard on :8099
.venv/bin/python -m lantern simagents                    # stand-in agents, if the Switch agents are not running
.venv/bin/python scripts/ward_scenarios.py               # a day on the ward, played by scripted humans
```

The **mission-control dashboard** at `http://127.0.0.1:8099/` is read-only and polls every two seconds: patients and orders, the case pipeline, evidence ledger, simulated chart versions, medicines, room tasks, translations, reminders, tracking items and the command audit. `/api/report?format=html` is the shift record.

## Integrations

- **Jira and Google Calendar:** the care-coordinator creates a task and a calendar event per follow-up. In our demo workspace these exist for real (KAN board, three `[Lantern]` events). Direct service hooks (`lantern/integrations.py`) are unit-tested against fakes only.
- **Wispr Flow:** voice input for commands and notes. Dictation was not recorded in the demo.
- **Translation:** patient 103 writes Spanish; the interpreter translates both ways and can read aloud (macOS voice).

## Status, plainly

- **Tested:** 98 unit tests (`tests/`), no network; the offline demo; live runs against a local Mattermost with stand-in agents (`scripts/live_e2e.py`, `scripts/ward_scenarios.py`).
- **Switch agents:** `intake` and `care-coordinator` were run live in Switch Console on Nov 4 (full Case 17 passed three runs in a row, refusals checked live). The Console agents have since been re-created on OpenCode and, at recording time, did not receive Mattermost messages, so the recorded run uses stand-ins. `interpreter` and `scribe` exist only as code stand-ins.
- **Not done:** the nurse review (questions prepared in [docs/NURSE_REVIEW.md](docs/NURSE_REVIEW.md); no clinician feedback exists), live Mattermost buttons, and live calls from the service's own Jira/Calendar hooks.
- **Known limit:** a crash in the middle of a command can drop that command's follow-up message; restarts never duplicate anything.

## Layout

| Path | What |
| --- | --- |
| `lantern/service.py` | record service: SQLite, chart versions, cases, decision verification, room tasks |
| `lantern/bot.py`, `lantern/chat.py` | record-bot poller and Mattermost REST client (stdlib only) |
| `lantern/simagents.py` | rule-based stand-in agents (tests and fallback) |
| `lantern/api.py`, `lantern/ui.html` | read-only API and the dashboard |
| `config/roles.yaml`, `data/` | roles, room membership, synthetic charts |
| `scripts/` | Mattermost setup, offline demo, live checks, ward scenarios, reset |
| `docs/` | setup, agent instructions, scenarios, demo scripts, blog and #HowISwitch drafts |
| `site/` | the project website |
| `film/`, `demo-video/` | concept film and the card/voice kit |
| `recordings/final/` | the submission video, captions, chapters, cut list |

More: [Hospital scenarios](docs/HOSPITAL_SCENARIOS.md) · [Recording guide](docs/RECORDING_GUIDE.md) · [Submission checklist](docs/SUBMISSION.md) · [Blog draft](docs/BLOG.md) · [#HowISwitch draft](docs/HOWISWITCH.md)

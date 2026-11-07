# Recording the demo (one person, one take at a time)

Goal: a 2:30 to 2:45 video from **real runs**, readable on a phone screen. Say "fictional data" once, early. There is no nurse-quote card (the nurse review was not done); end on the dashboard timeline with the repo URL.

## Layout (record at 1920x1080, one screen)

| Where | What |
| --- | --- |
| Left 60% | Mattermost in a browser: `nurse-station` and `doctor-review` threads (use a second window for `patient-101`) |
| Right 40% | The dashboard at `http://127.0.0.1:8099/`, presentation mode (press **P**) |

Log in to Mattermost as each person in a separate browser profile or private window: `patient-101`, `nurse-ana`, `dr-lee`, `nurse-ben`, `patient-102`. Use macOS Cmd+Shift+5, or OBS. Turn on Do Not Disturb.

## Two ways to run the scenes

1. **Real agents (best for the video).** Start `scripts/start.sh`. In Switch Console the real `intake` and `care-coordinator` are running. Run the driver in `--real` mode so it plays only the human roles and waits for the agents:
   ```bash
   export MM_URL=... MM_TEAM=... LANTERN_TEST_PASSWORD=...
   .venv/bin/python scripts/demo_driver.py --real --pause
   ```
2. **Stand-ins (rehearsal only).** Without `--real` two scripted accounts play intake and care-coordinator, calling the real lookup tool. Fine for rehearsing the timing and the dashboard. **Do not present stand-in agents as Switch agents in the video**; if you use it, say so on screen.

`--pause` waits for Enter before each step so you control timing on camera. The driver prints what to say next.

## Before each take

```bash
scripts/reset_demo.sh        # stops the bot, deletes the demo DB, waits 62 s, restarts with cases 14-16 seeded
```
The next case is Case 17. Do `python scripts/check_intake.py` once before the first take (real agents).

## Shot list (matches docs/DEMO_SCRIPT.md)

| Time | Show | Say |
| --- | --- | --- |
| 0:00 | Patient room, driver step 1 | "A patient tells their bedside tablet Dr. Lee said breakfast is fine. The chart says nothing by mouth. All data is fictional." |
| 0:15 | Dashboard: pipeline lights Patient, then intake | "Agents do the teamwork through Switch. Plain code handles the patient edge and the checks." |
| 0:35 | nurse-station thread: CONFIRM (step 3) | "intake only asks. A nurse confirms." |
| 0:55 | doctor-review: care-coordinator's cited summary, ✓ card; dashboard Evidence ledger | "Every fact comes with its source, taken from the service's own log." |
| 1:15 | Dashboard command audit with a red refusal (see below) | "Anything not allowed is refused by code, with a reason." |
| 1:30 | DECIDE (step 5); chart v3 to v4, old order struck through, ledger turns STALE | "Only a verified doctor's decision changes the record, and old receipts go stale." |
| 1:50 | Patient room: doctor's words, "Following up: nurse-ana" | "The patient gets the clinician's own words and who owns the follow-up." |
| 2:05 | Handoff, step 6, owner becomes nurse-ben | "A handoff passes responsibility, not just information." |
| 2:20 | Isolation, step 7, patient-102 refused; HTTP 403 | "Isolation is Switch room membership." |
| 2:35 | Dashboard timeline, repo URL | "What was said. What was confirmed. Who owns what's next." |

## Getting a real red refusal on camera
During the DECIDE scene, post `DECIDE Case 17 v3 diet=regular` plus an `EXPLAIN:` line as **nurse-ana** in the doctor thread (a nurse is not a doctor), or post it from dr-lee as a top-level message. Both are refused and show up red in the Command audit. Do it before the real DECIDE.

## Checklist before you press record
- [ ] `curl -s localhost:8099/healthz` is ok, dashboard shows live (green dot)
- [ ] All Mattermost windows logged in as the right people, notifications off
- [ ] Case 17 does not exist yet (fresh reset)
- [ ] Fonts big enough: browser zoom 125%
- [ ] Do not show tokens, passwords or terminals with `LANTERN_TEST_PASSWORD`
- [ ] After recording: speed up waits in editing, never fake a step; add captions

## Populating the whole ward first
Start the agents first: the real Switch agents if they answer, otherwise `python -m lantern simagents` (say "scripted stand-ins" on screen).

`python scripts/ward_scenarios.py` plays a day on the ward through the Mattermost API (scripted stand-ins for the two agents unless `--real`): patient 101 diet with a refused nurse DECIDE and a tray task closed by room service, patient 102 left awaiting the doctor, patient 103 decided with a flagged double medicine entry and a partial discharge turnover, patient 104 rejected, a refused cross-patient question, and a shift change handing three cases to nurse-ben. Run it after `scripts/reset_demo.sh`, with `MM_TEAM=lantern` (the team Console's connection uses).

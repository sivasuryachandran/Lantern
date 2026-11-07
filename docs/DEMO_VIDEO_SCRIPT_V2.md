# Demo video script v2, corrected to what the build does (≤ 3:00)

Supersedes the pasted v2 where they differ. Changes are in **bold**. All the live flow below was run on Nov 6 against the local Mattermost with scripted stand-ins; the real agents must be re-checked in your take.

Tagline: **What was said. What was confirmed. Who owns what's next.**

## What changed from the pasted v2, and why

| Pasted v2 | Build | Script now |
| --- | --- | --- |
| Pre-roll case is Case 18, live case is Case 17 | The counter hands out numbers in order, so the pre-roll case is **Case 17 (patient 102)** and the live case is **Case 18 (patient 101)** | Use those numbers on every label |
| `HANDOFF Case 17: …` and `HANDOFF Case 18: …`, ACCEPT both | **Fixed in the code (Nov 7):** the owner can hand off an open or resolved case; ACCEPT moves ownership and leaves the clinical state alone. Syntax is `HANDOFF Case N open: <text>`, one post per case | Hand off **both** cases, two posts, two ACCEPTs. Case 17 stays awaiting Dr. Lee, now owned by nurse-ben |
| `GIVEN … 06:05` "patient-level" | `GIVEN Case N <what> HH:MM` inside that case's nurse thread | `GIVEN Case 17 pain relief (fictional) 06:05` |
| Clock "06:40 · shift change 07:00" on the dashboard | No clock exists | Cut it. Say the times in the voice-over and on lower thirds |
| Patient / nurse / doctor view toggle on the dashboard | The API refuses the patient role; views are the CLI | Show `python -m lantern timeline 101 patient` (and `nurse`, `doctor`) as `--html` pages, or drop the patient view |
| REFUSED row in the patient timeline | Refusals are in **Command audit** | Show the red row in Command audit |
| `ord-activity-1 · assist required · fall risk` for patient 102 | Added to `data/patient-102.json` | no change needed |
| "OpenCode" | Unverified; README says Claude Code | Use whatever Switch Console shows |
| Four rooms | **Nine rooms** (room-service staff included): patient-101 to 104, nurse-station, doctor-review, and write-only feeds **orders, medication, room-service** | New "downstream" beat below |

## Pre-roll (before the camera rolls), real system only

```bash
export MM_URL=… MM_TEAM=… LANTERN_TEST_PASSWORD=…
scripts/reset_demo.sh                         # fresh DB, seeded cases 14-16
python3 scripts/demo_driver.py --preroll --real      # patient 102: Case 17, confirmed, GIVEN 06:05, left open
# the take itself: python3 scripts/demo_driver.py --real --pause --also 17   # patient 101 is Case 18; --also hands over Case 17 too
```
Board check: Case 17 · patient 102 · activity · CONFIRMED_CONFLICT · owner nurse-ana; one `medication` post; patient 101 untouched. Do **not** decide Case 17.

## Shots (Layouts: A split, B focus, W dashboard full screen)

| Time | Shot | Voice-over |
| --- | --- | --- |
| 0:00 | **W**: dashboard with Case 17 open and its GIVEN entry; push-in | "At shift change, a nurse doesn't hand over one question. She hands over patients, medicines already given, decisions still waiting. Lantern keeps all of it in one shared record, inside the team's chat." |
| 0:15 | **A**: patient-101 message, forwarded, intake's card (Case 18 opens), lanterns 1 to 2 | "Here's one concern, end to end. Patient 101 mentions breakfast in passing. The intake agent, working through Switch, notices her chart still says nothing by mouth, quotes her exactly, and flags it as possible. It doesn't decide." |
| 0:30 | **A → B**: fixed acknowledgment, `CONFIRM Case 18`, coordinator's cited answer, hold the ✓ 2 s | "Ana confirms what the patient meant. The coordinator agent carries the case into the doctor's room and cites the chart with a receipt. Lantern checks that the cited value matches the lookup it logged at that chart version, and only then marks it verified." |
| 0:58 | **B → A**: Ana's DECIDE refused (red row in Command audit); Dr. Lee's `DECIDE Case 18 v3 diet=regular` + `EXPLAIN:`; chart v3 → v4; patient tablet | "A nurse can't change the order here. Only a verified doctor can. Dr. Lee decides, the simulated chart moves to version four, and the patient gets her exact words, not an AI rewrite." |
| 1:22 | **New. The ward feeds in Mattermost**: `orders` shows the v3 → v4 line; `room-service` shows the tray task `T-101-D18`; a nurse's `DONE` is refused (red row in Command audit), then Sam posts `DONE T-101-D18` and record-bot confirms; `medication` shows the GIVEN; dashboard "Rooms & turnover" shows 4W-101 and the previous occupant | "One decision reaches the whole ward. The orders room logs the new chart version. Room service gets a tray task, only room service can close it, and the record shows who did and when. Medication keeps what was given separate from what was ordered." |
| 1:40 | **W**: patient 101's timeline in nurse, doctor, patient views (CLI/HTML), about 2 s each | "Everything lands in one record, and nothing gets blurred together. What she said, what the chart said, what was checked, what was decided, and who owns what's next. Each role sees the same record through its own window." |
| 1:55 | **W → A**: select Case 17 (patient 102): confirmed, waiting for Dr. Lee, owner nurse-ana | "And it isn't just Patient 101. Patient 102's question about walking alone is confirmed and waiting on the doctor, and Ana still owns it." |
| 2:05 | **A**: `HANDOFF Case 18 open: confirm she ate without nausea`, then `HANDOFF Case 17 open: awaiting Dr. Lee; fall risk, assist to bathroom`; coordinator briefs Ben on both with sources; `ACCEPT Case 18`, `ACCEPT Case 17`; both owners flip to nurse-ben on the board and the tablets; Case 17 still shows awaiting Dr. Lee; lantern 6; hold 4 s, music only | "Seven o'clock. Ana hands over everything that's still open, across both patients. The coordinator walks Ben through it, with sources. Ben accepts, and the whole ward knows he owns it now." |
| 2:30 | **Proof**: Switch Console agent list beside the room list; 2 s of the test run ending in OK | "Two agents in Switch rooms do the noticing and the legwork. A small service enforces the rules and keeps the record." |
| 2:45 | Concept clip d2 (labeled) → end card | "Agents notice. People decide. Code enforces. Lantern." |

End-card small print: "Agent replies, checks and record updates are live. Human lines played from scripts/demo_driver.py. Fictional data, not for clinical use."

## What we say, and what we don't

Say: "one shared record for a ward", "simulated chart", "matches the lookup it logged at that chart version". Don't say: "the EHR", "verified correct", "Lantern listens at the bedside", or a provider name you have not confirmed in Console.

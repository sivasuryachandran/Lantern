# Demo video script (2:30 to 2:45, every scene from a real run)

Title card: **No concern left in the dark.** Say "fictional data" on screen. Speed up waits in editing, never fake a step. Do three clean runs first, and run `scripts/check_intake.py` before every take.

| Time | Scene | On screen | Say |
| --- | --- | --- | --- |
| 0:00 | patient-101 (bedside tablet) | Patient dictates the Case 17 line | "A patient tells their bedside tablet Dr. Lee said breakfast is fine. The chart says nothing by mouth." |
| 0:12 | nurse-station | record-bot forwards; intake posts the quote next to order v3 | "This isn't a scribe. It's what happens when what was said and what's on record disagree." |
| 0:25 | nurse-station + patient-101 | Case 17 opens; patient sees the fixed template | "The patient hears nothing until the service has checked the quote against the original post." |
| 0:38 | nurse thread | intake asks; nurse replies CONFIRM (or taps the button) | "intake only asks. A nurse confirms." |
| 0:52 | doctor-review | care-coordinator calls the lookup tool and cites `[proc-1 v3 · lookup #31]`; record-bot posts the card: **Procedure: Thu 9:00**, source, lookup #31, ✓ verified | "A real coding agent answers from the live chart. Under every cited fact, the system shows what its own log says." |
| 1:10 | doctor-review | One ⚠ from a real run (wrong value or no lookup number), then the timeline showing the lookup trail | "A claim with no receipt, or the wrong value, never gets a check mark. And a new chart version marks old receipts stale." |
| 1:25 | doctor-review | Dr. Lee DECIDE with her explanation; chart v3 to v4 | "Only a verified doctor's decision changes the record." |
| 1:40 | patient-101 | Her words word for word; "Following up: nurse-ana" | "The patient gets the clinician's own words, and who owns the follow-up." |
| 1:55 | nurse-station | GIVEN, HANDOFF, incoming nurse ACCEPT; owner line becomes nurse-ben | "A handoff passes responsibility, not just information." |
| 2:25 | patient-102 | Cannot open patient-101; Case 17 question gets the refusal | "Isolation is Switch room membership. No agent can reach a patient room." |
| 2:40 | Timeline | Said / simulated chart / given / confirmed / owner | "What was said. What was confirmed. Who owns what's next." |

**Staging rules**
- Keep record-bot quiet on screen. Most staff scenes should show agents and people talking in the threads. record-bot gets short plain lines only: the forwarded message, a ✓ or ⚠, a verdict. Crop or scroll past its longer thread openers.
- Frame the receipts as good teamwork: "every claim comes with its source, like a good colleague's," not "we don't trust the agent."
- Say once, early: "agents do the teamwork through Switch; plain code handles the patient edge and the checks."

**Closing 10 seconds:** end on the timeline with the on-screen line "Fictional data. Not clinical software. Not reviewed by a clinician yet." and the repo URL. There is no nurse-quote card because the nurse review was not done; never invent one.

Only include Jira or Calendar if they worked on the first try.

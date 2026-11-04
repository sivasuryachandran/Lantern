# Team split: 80% / 20%

**Deadline: Sat Nov 7, 10:29 AM PT. Aim to submit Friday night.** Today is Wed Nov 4. Confirm the Tuesday 8 PM fallback check result (agent-only loop works live, or switch to Blast Radius) before anything else.

Assumption: **Member A (you) carries 80%** and **Member B carries 20%**. If it is the other way round, swap the names. B's 20% is chosen to be **independent work that needs no Switch setup and no code changes**, so B never blocks A and A never has to explain internals.

The code side is built (record service, bot, backend, evidence receipts, tests, docs). What is left is Switch setup, making the real agents behave, the demo, the video and the writing.

## Member A: 80%. Switch, code, demo, video, submission

**If Member A uses Claude Code, point it at [`HANDOFF_FOR_CLAUDE_CODE.md`](HANDOFF_FOR_CLAUDE_CODE.md) first. It has the full step-by-step with commands, grammar and acceptance checks.**

**Wed (today), the milestone**
1. Confirm `python -m unittest discover -s tests` passes (47 tests) and `scripts/live_e2e.py` passes. Start the real repo today and commit in small steps, so the history shows the work in the event window. Check the exact rule on the hackathon page.
2. Create `intake` and `care-coordinator` in Switch Console with the instructions in `docs/agents/`. care-coordinator is a real coding agent (Claude Code or Codex) on the same machine as the bot.
   - intake: `nurse-station` only. care-coordinator: `nurse-station` and `doctor-review`. **Neither in a patient room.** If usernames differ, edit `config/roles.yaml`.
3. Run `scripts/start.sh` (needs `LANTERN_TEST_PASSWORD`), then `scripts/check_intake.py`. All three casual phrasings must open a possible discrepancy.
4. Check care-coordinator calls `curl http://127.0.0.1:8099/chart/101/proc-1?agent=care-coordinator` and pastes the `citation` string exactly, so record-bot posts a ✓ card.
5. Run the full Case 17 by hand. Record a rough take.
6. **Hand B the nurse-call brief tonight** (see B below).

**Thu**
- Fix whatever the real agents break: change agent instructions first; never loosen the decision checks to make a demo pass.
- GIVEN, HANDOFF and ACCEPT scene, the isolation scene (patient-102 blocked, Switch refuses intake in a patient room), three clean runs.
- Optional, only if everything else works: buttons, Jira, Calendar. **Cut these first.**
- Add or adjust must-pass tests if runs reveal gaps.

**Fri**
- Final video, 2:30 to 2:45, from real runs (`docs/DEMO_SCRIPT.md`; record-bot kept quiet on screen). Last 10 seconds: the nurse quote card. Cut it if there is no real quote.
- README final pass: 30-second GIF, room diagram, trust model, fictional-data banner; "How Switch is used" matches the running code. Paste B's nurse quote into "Nurse review".
- Any Switch bug fixed upstream as a PR.
- Wispr Insights screenshot saved as `docs/wispr-scorecard.png`. Final pass on `docs/SUBMISSION.md`, submit.

**A's definition of done:** the full Case 17 runs live with the real agents three times in a row, the video is recorded, and the repo is submitted.

## Member B: 20%. Nurse call, writing, outside check

About 4 to 5 hours in total, none of it touching `lantern/`.

1. **Nurse review (Wed night or Thu morning, about 1 hour including booking).** Find a nurse who is not on the team, run the 15-minute call using `docs/NURSE_REVIEW.md`, ask permission to quote them by role, and send A the quote and what they said would change. Everything shown is fictional; take no real patient details.
2. **Blog (Thu, about 2 hours).** Fill the brackets in `docs/BLOG.md` and add a short "how I set up Switch" section for first-time users. That is what the Best Blog judges score. A supplies any Switch gotchas.
3. **#HowISwitch post (Fri, 15 minutes).** Polish `docs/HOWISWITCH.md`, attach A's clip, post.
4. **Cold reproduction (Fri evening, about 1 hour).** Follow the README on a machine that has not seen the project: venv, tests, `scripts/demo_offline.py`. Write down every place you got stuck and give the list to A.
5. **Own Wispr screenshot (Fri, 5 minutes).** If B dictated anything, take Insights; A submits whichever has the stronger numbers, or both.

**B's definition of done:** nurse quote delivered, blog and post published, and a cold run of the README logged with any stuck points.

## Shared

| When | Both |
| --- | --- |
| Daily | 10-minute sync; post what is blocked |
| Fri 3 PM PT | Feature freeze. Only fixes after this |
| Fri night | B's cold reproduction done; A submits |
| Sat morning | Buffer only. Do not start anything new |

## Cut order if behind

Buttons, Jira, Calendar, recorded clip, timeline polish, then the isolation scene (keep the test, cut the scene). **Never cut the core loop, the nurse quote, or the video.**

## Handoffs

| A gives B | B gives A |
| --- | --- |
| Tonight: the nurse-call brief and `docs/NURSE_REVIEW.md` | The nurse quote, by role, with permission |
| Thu: Switch gotchas for the blog | Blog draft for a claims check against the code |
| Fri: the video clip for the post | The list of README stuck points from the cold run |

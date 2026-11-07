# 3-minute demo: script vs. the running build

Checked against this repo (regexes in `lantern/service.py`, `scripts/demo_driver.py`, `lantern/ui.html`, `docs/agents/`). Fix the **script**, not the code.

## Must fix before recording

| Script says | Build does | Fix |
| --- | --- | --- |
| Nurse posts `CONFIRM Case 17: she believes Dr. Lee cleared her…` | `RE_CONFIRM = ^CONFIRM Case (\d+)\s*$`: any text after the number is **not a valid CONFIRM** and is ignored | Post exactly `CONFIRM Case 17`. Let intake's card carry the meaning |
| Human lines "played from `demo/case17.py`" | There is no such file | Say `scripts/demo_driver.py` (use `--real --pause`) in the end card and README |
| "AGENT · intake · OpenCode", "OpenCode agents" | README (teammate's Nov 4 report) says both agents run on **Claude Code**; nothing in the repo shows OpenCode | Read the provider and model off Switch Console and use that. VO uses "coding agents" unless `AGENT_PROVIDER` is set |
| `[proc-1 v3 · lookup #31]` on screen | Lookup numbers count from the live DB; a fresh run gives `#1`, `#2`… | Use the number that actually appears in your take. Never type a number into a card |
| "Lantern checks … Evidence receipts panel" | The dashboard panel is called **Evidence ledger** | Rename in the script or the lower third |
| "red toast" on refusal | The dashboard shows the refusal as a **red row in Command audit**; there is no toast | Cut "red toast", or add one (small UI change) |
| "7 must-pass checks" on screen over the test run | `python -m unittest discover -s tests` prints `Ran 51 tests … OK`; the 24 must-pass tests cover 7 areas | Caption: "51 tests · 7 must-pass areas" |

## Unverified, so confirm in the take or soften the line

- "Switch decides who's in which room, **who can address which agent**, and keeps every reply in its thread." The repo only shows room membership; thread replies depend on the agents following their instructions. Confirm in Console, else say "who's in which room."
- Dr. Lee asks "When did the procedure move?" and the coordinator answers with a citation. The agent doc supports it, but it has only been seen with stand-ins here. Confirm live.
- "The coordinator walks Ben through it, citing receipts." The handoff brief is specified; citations in it are not guaranteed.
- Everything the script calls live must come from a real run with the real agents. The Nov 6 runs here used scripted stand-ins.

## Matches the build

Quote and order (`ord-diet-1 · NPO · chart v3`), possible-discrepancy card, fixed patient template "Your care team is checking this (Case 17)", `DECIDE Case 17 v3 diet=regular` + `EXPLAIN:` (two lines), refusal for a nurse's DECIDE, chart v3 → v4 with the old order struck through, doctor's words verbatim plus "Following up: nurse-ana", `GIVEN` / `HANDOFF … open:` / `ACCEPT`, owner → nurse-ben, "Present" mode (key P), the progress strip and hero sweep as edit overlays.

## Narration draft (generated with Google Cloud TTS, Orus, natural pace)

`demo-video/voice.py` makes `out/vo-draft.wav` and `out/captions.srt` (git-ignored; rebuild with the command below). Natural pace is longer than the script's slots, so beats drift later. Cut the live recording to the voice, as the script's edit order says.

| Beat | Script start | Actual start | Length | Note |
| --- | --- | --- | --- | --- |
| 1 Cold open | 0:00 | 0:00 | 7.9 s | slot is 6 s: start the title card at 0:08 |
| 2 "Her chart still says…" | 0:06 | 0:08 | 2.2 s | |
| 3 The problem | 0:12 | 0:12 | 13.7 s | |
| 4 The setup | 0:24 | 0:26 | 19.0 s | room map runs to about 0:45 |
| 5 She mentions it | 0:38 | 0:45 | 6.5 s | |
| 6 intake notices | 0:46 | 0:52 | 9.6 s | |
| 7 Patient told | 0:56 | 1:02 | 4.2 s | |
| 8 Nurse confirms | 1:00 | 1:07 | 4.7 s | |
| 9 Receipts | 1:08 | 1:12 | 21.3 s | |
| 10 Refusal | 1:32 | 1:34 | 10.9 s | |
| 11 Dr. Lee decides | 1:42 | 1:45 | 6.0 s | |
| 12 Patient reads | 1:52 | 1:52 | 5.6 s | |
| 13 Shift change | 2:00 | 2:00 | 13.7 s | 8 s of slack: let lantern 6 and the sweep hold |
| 14 Under the hood | 2:22 | 2:22 | 26.3 s | run the diagram about 8 s longer than the script |
| 15 Tests | 2:40 | 2:48 | 6.0 s | |
| 16 Close | 2:46 | 2:55 | 4.2 s | speech ends 2:59 |

The total lands about 1 s over the script's 2:58. If you need it shorter, the script's own trim order applies: "especially when the shift changes" (about 1.5 s), then the last sentence of the setup (about 4 s; keep it if you can, it is the honesty line), then the tests line.

```bash
LANTERN_TTS_PROJECT=<project with Text-to-Speech enabled> [AGENT_PROVIDER=<provider>] python3 demo-video/voice.py
```
The script prefers a human voice for the final cut; this track is for timing and a fallback.

## Not built yet

The live screen recording (needs the real agents and a person at the keyboard), lower thirds and progress strip, the code-made cards (title, room map, flow diagram, end card), the music bed and the six lantern chimes (their frames come from the recording). Ask for any of these once the recording exists.

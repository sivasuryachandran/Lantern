# Lantern × Wispr Flow

Two parts: how we **built** Lantern by voice, and how people **use** Lantern by voice. Nothing below is claimed as done until its row says so; the Insights screenshot (`docs/wispr-scorecard.png`) is the evidence for the build part.

> Feature descriptions come from Wispr's own pages as summarized in our planning notes. Confirm each one in your app version before you say it on camera.

## How a ward uses it

| Wispr Flow feature | In Lantern | Status |
| --- | --- | --- |
| Dictation in any app | Staff speak commands into the Mattermost rooms | to record |
| Whisper Mode | Ana whispers the 7:00 AM handoff at the nurse station | to record |
| Snippets | A spoken trigger inserts the exact command prefix, so the parser always gets valid syntax | to set up |
| Dictionary with replacements | "at intake" → `@intake`, so an @mention of an agent is a voice action | to set up |
| Auto-editing | A rambling handoff arrives as clean text | to record |
| Command Mode (Pro) | Highlight dictated notes, say "turn this into I-PASS bullets", **review, then send**. The AI never posts for her | optional |
| "Press enter" (paid, experimental) | Hands-free send | optional |
| Mobile | The bedside tablet message is dictated by the patient | optional |
| Other languages | Only claim this if you test one non-English message | optional |
| Privacy Mode | **On.** Without it Wispr says dictation may be used to improve its models. A real ward would need an enterprise agreement; this demo uses fictional data only | do first |
| Insights | The scorecard screenshot for the prize | at the end |

## Dictating in another language

A patient can dictate in their own language with Wispr Flow on the bedside tablet and Wispr types it into the room; Lantern's interpreter agent then translates it for the nurse. Say that on camera only if you actually dictate in Spanish.

## Snippets (what to say → what is inserted)

The parser is strict: `HANDOFF Case <n> open: <text>`, `CONFIRM Case <n>`, `ACCEPT Case <n>`, `DECIDE Case <n> v<k> <topic>=<value>` then a new line `EXPLAIN: <text>`, `GIVEN Case <n> <what> <HH:MM>`, `DONE T-…`. Snippets supply the fixed part; you say the rest.

| Say | Inserts | Then say |
| --- | --- | --- |
| "lantern confirm" | `CONFIRM Case ` | "eighteen" |
| "lantern handoff" | `HANDOFF Case ` | "eighteen open colon confirm she ate without nausea" |
| "lantern accept" | `ACCEPT Case ` | "eighteen" |
| "lantern decide" | `DECIDE Case ` | "eighteen v3 diet equals regular" |
| "lantern explain" | a new line and `EXPLAIN: ` | the explanation in Dr. Lee's own words |
| "lantern remind" | `REMIND Case ` | "seventeen in twenty minutes check she ate", or "seventeen eleven a m check she ate". Record-bot posts it back into the case thread when due and asks the care-coordinator to add it to the owner's calendar |
| "lantern advice" | `ADVICE Case ` | "eighteen she can have a regular diet today". Records advice only; record-bot offers a draft DECIDE for the doctor to check and send herself |
| "lantern given" | `GIVEN Case ` | "seventeen pain relief 06:05" |
| "lantern done" | `DONE ` | the task id |
| "I-PASS" | a structured handoff template (Illness severity, Patient summary, Action list, Situation awareness, Synthesis) | |

**Careful:** the handoff must include `open:` or the parser ignores it ("lantern handoff seventeen, confirm she ate" is not valid). Check each phrase against `lantern/service.py` before you rely on it.

## Dictionary and replacements

Custom words: `@intake`, `@care-coordinator`, `@dr-lee`, `NPO`, `Dr. Lee`, `nurse-ana`, `nurse-ben`, `ord-diet-1`, `ord-activity-1`, `proc-1`, `Case 17`, `Case 18`, `Lantern`, `Switch`, `Mattermost`.
Replacements: "at intake" → `@intake`, "at care coordinator" → `@care-coordinator`, "N P O" → `NPO`, "doctor Lee" → `Dr. Lee`, "T dash" → `T-`.

## Set-up checklist (about 45 minutes)

1. Wispr Flow is **already installed** on the demo MacBook; hold the **Fn** key to dictate into whichever app has focus. Still to do: turn on **Privacy Mode** and **Whisper Mode**.
2. Add the snippets and dictionary above.
3. Set the Mattermost style to concise.
4. Dictate the rest of the work from now on: prompts, agent instructions, README, blog, voice-over script, commits, the #HowISwitch post. The Insights scorecard should show real use.
5. Save the Insights screenshot as `docs/wispr-scorecard.png`.

## The 15-second beat in the demo (inside the 7:00 AM handoff)

Ana, whispering: "lantern handoff eighteen open colon confirm she ate without nausea, press enter." Ben: "at care coordinator, what's open?" then "lantern accept eighteen, press enter." Caption: "Dictated live with Wispr Flow: Whisper Mode, a snippet, a dictionary @mention, Press Enter." Everything else in the video is played by `scripts/demo_driver.py`; say so in the verification note. If you do not record this beat for real, cut it.

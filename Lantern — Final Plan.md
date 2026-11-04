# Lantern — Final Plan

Nov 2, 2026 · @Siva Surya Chandran

**Lantern — What was said. What was confirmed. Who owns what's next.**

*Video title card:* **No concern left in the dark.**

Lantern keeps a shared record of concerns, decisions and handoffs beside the clinical chart, so a patient's words, a clinician's confirmed answer, and the next shift's owner never drift apart.

## Decision

We're building **Lantern** for the Flip the Switch hackathon, Best Business Workflow track. When what a patient says conflicts with their chart, the concern goes from the patient's room to the nurse, then the doctor, and comes back to the patient as an answer a clinician has confirmed. The next nurse then has to accept the follow-up at shift change.

- **Event window (Pacific):** opens Tue Nov 3, 10:31 AM. Submission closes **Sat Nov 7, 10:29 AM**. That's Saturday *morning*.
- **Pitch:** the tagline and sentence at the top of this doc. The rule underneath it: only a clinician's verified decision changes the record.
- **Why this over Blast Radius:** it's a story anyone gets in 5 seconds, it uses Switch rooms more centrally, and it doesn't need a GitHub webhook or merge-blocking. It reuses the Switch mechanics we already tested: the move into another room (T2), the human decision coming back (T3), and room access being enforced (T4).
- **Judging:** the official [DevTools Academy page](https://www.devtoolsacademy.com/hackathons/flip-the-switch) gives the weights: **Use of Switch 30%** ("would the project stop working without it?"), **Technical execution 25%** ("could someone clone the repo and reproduce it?"), **Creativity and impact 25%**, **Presentation 20%**. Switch's role is the biggest single factor.
- **Fallback:** if the agent-only loop (patient-101 → nurse-station → doctor-review → patient-101) doesn't work live by **Tue 8 PM PT**, switch to Blast Radius Wednesday morning. Its [team brief](https://claude.ai/artifact/HnjD3wYy1D739H8wUqRUDY), spec v2.1 and Claude Code prompt are all ready.
- **Order of work:** the core loop first. Voice, Google Calendar and Jira only come in after the Wednesday milestone works (see the integrations section).

**Checked against the official page, this is still the pick.** Lantern is the more reproducible of the two: it needs only the bundled Mattermost, with no GitHub repos or tokens. It's also further from the organizers' own examples, which are a triage pair and an incident room, both developer workflows. Blast Radius sits much closer to those.

**The build-during-the-event rule:** the FAQ allows existing agents and libraries, but says the Switch setup and the workflow have to be built during the event. The rule doesn't require deleting the Nov 2 test rooms and agents. We'll recreate them after Tue 10:31 AM PT anyway, because it takes about 20 minutes and removes any doubt.

**Before 10:31 AM Tue:** put a name next to every role in the Roles section. A plan without owners isn't a plan yet.

## Problem and pitch

Patients hear things from one clinician that haven't reached the chart yet. Nurses promise to check back, and then the shift changes. When the patient's understanding and the record disagree, nobody clearly owns sorting it out. A handoff should pass on responsibility, not just information, and the person receiving it needs a chance to ask questions and confirm.

**What we claim:** a discrepancy between what the patient said and what the chart says becomes a conversation with clear owners across separate Switch rooms. The agent pulls out the claim and routes it. A deterministic record service only changes the chart when a verified doctor decides, and only that service says "resolved." The patient gets the clinician's own words back, and the next nurse explicitly accepts what's still open.

**What we don't claim:**

- An AI medical record, a better scribe, or a replacement for Abridge or Epic. Abridge already captures nursing conversations and carries context across shifts, and Epic offers patient questions answered from the chart.
- Clinical readiness, HIPAA compliance, or medical advice of any kind. **All people and data are fictional.**
- That the agent understands medicine. It extracts, routes and quotes. Clinicians decide.

**How we're different:** existing tools document what was said. Ours closes the loop when what was said, what was promised and what's on the record don't match. Say this in the first 15 seconds of the video.

## What Lantern is

Lantern is **one shared record that patients, nurses and doctors all work from**, with Switch rooms as the place where people and agents discuss and act on its entries. In a real hospital, Lantern would be the source of truth for **concerns, decisions and who owns each follow-up**, while the hospital chart stays the authority on clinical orders. **In this demo the "chart" is a small simulated chart inside Lantern**, so when the service "updates the chart to v4," that's the simulated chart. We say so in the README and label it *simulated chart* on screen. We never call Lantern "the patient record," so judges don't compare it to Epic.

| Entry type | What it stores | In this build |
| --- | --- | --- |
| Patient timeline | Concerns, questions and quoted excerpts, each with its source post | **Built** (dictated messages) |
| Orders | What a doctor currently ordered, with version and author | **Built** (simulated diet order and procedure schedule) |
| Medication given | What a nurse actually gave, when and who recorded it, **kept separate from the order** | **Built, one live entry:** the outgoing nurse records a fictional anti-nausea dose with `GIVEN`; author and time show in the timeline. No dosing logic, no advice |
| Care tasks | What's left to do, who owns it, whether it was accepted at handoff | **Built**, and **the patient sees who owns their follow-up** |
| Decisions | What a clinician confirmed, linked to the concern and its source | **Built** |
| Handoffs | What the outgoing nurse passed on and what the incoming nurse accepted | **Built:** the outgoing nurse posts `HANDOFF` listing what's open, then the incoming nurse posts `ACCEPT` |

**Who uses it how:** the patient sees what's been confirmed and who's following up. A nurse sees what changed and what's still open. A doctor reviews a concern against the current orders and the recorded events.

**Not in this build, and not claimed:** continuous bedside audio, a complete medication record, full clinical history, open-ended patient Q&A, coverage of a whole hospital. Those are the long-term vision. The demo uses deliberate voice input and events staff enter themselves. **We never say "everything is recorded."**

## The demo: Case 17

One fictional patient, one conflict, three clinicians, one confirmed answer. We use a **diet order** rather than a medication, because it's just as clear to viewers and keeps the agent well away from drug advice.

**Setup:** Patient 101's chart has diet order `NPO (nothing by mouth), for procedure`, version 3. That morning, fictional Dr. Lee told the patient the procedure had moved to Thursday. The chart hasn't been updated. `patient-101` and `patient-102` are **bedside tablet channels**, a patient-facing screen at the bed shown as a Mattermost channel. **We say this in the first scene.**

| Time | Room | What happens |
| --- | --- | --- |
| 0:00–0:15 | `patient-101` (bedside tablet) | The patient dictates **in passing**: "Can't wait for breakfast. Dr. Lee said it's fine now that my procedure moved." |
| 0:15–0:30 | `nurse-station` | record-bot forwards the message, keeping the original post id. **intake** posts a **possible discrepancy** card: the exact quote next to the active NPO order (v3). It never claims the conflict is confirmed |
| 0:30–0:40 | `nurse-station` + `patient-101` | The service checks the quote against the original post and **opens Case 17**: record-bot posts the Case 17 thread in nurse-station. **Only now** does the patient see: "Your care team is checking this (Case 17). They'll answer here." |
| 0:40–0:55 | `nurse-station` | **In the Case 17 thread**, intake asks the nurse to confirm what the patient meant. The nurse replies `CONFIRM`: the patient believes they're cleared to eat. The nurse escalates |
| 0:55–1:20 | `doctor-review` | On escalation, record-bot opens Case 17's doctor thread. **care-coordinator** posts the summary inside it: the quote, the nurse's confirmation, the active NPO order. Dr. Lee asks, "When did the procedure move?" It answers from the chart and cites its source: *"Moved from Tue 9:00 to Thu 9:00, changed Tue 7:40 by Dr. Lee (chart: proc-1, v3)"* |
| 1:20–1:35 | `doctor-review` | Dr. Lee **checks the schedule herself and places the new order**: diet regular, plus an explanation for the patient. The service verifies her and updates the **simulated chart** to v4. Nobody infers the change from the patient's words |
| 1:35–1:50 | `patient-101` | record-bot posts Dr. Lee's explanation **word for word**, attributed to her, followed by **"Following up: nurse-ana"** |
| 1:50–2:25 | `nurse-station` | Shift change. The outgoing nurse records `GIVEN` (fictional anti-nausea dose, 18:10), then posts `HANDOFF Case 17: confirm the patient ate without nausea; anti-nausea given 18:10`. care-coordinator shows the incoming nurse everything open. The incoming nurse posts `ACCEPT`. In `patient-101`, the owner line updates to **"Following up: nurse-ben"** |
| 2:25–2:35 | Calendar + Jira | *Only if built:* a follow-up event and a task, both carrying Case 17 |
| 2:35–2:50 | `patient-102` | Patient 102's tablet account can't open patient-101's channel, and asking about Case 17 gets the service's refusal |
| 2:50–3:00 | Record | The shared timeline, read by role: what was **said**, what the **simulated chart** says, what was **given**, what a clinician **confirmed**, and **who owns** what's still open |

**Rules for recording:** every scene comes from a real run. Speed up waiting in editing, never fake a step. Do at least 3 clean runs before the final take, and say "fictional data" on screen.

## Rooms, people and authority

Four Switch rooms with deliberately chosen members. Switch room membership is the first boundary, and the record service checks roles again as the second.

&#91;embedded content: Case 17 flow · 4 rooms, 1 record service\]

The concern moves 1 → 5 through Switch rooms. Patient 102's room never connects to Case 17.

| Room | Members | Purpose |
| --- | --- | --- |
| `patient-101` | Patient 101 (bedside tablet), record-bot. **No agents** | Patient messages come in; fixed acknowledgments and the doctor's words go out |
| `patient-102` | Patient 102 (bedside tablet), record-bot. **No agents** | Shows isolation |
| `nurse-station` | Outgoing nurse, incoming nurse, intake, care-coordinator, record-bot | Forwarded patient messages, case cards, nurse confirmation, handoff acceptance |
| `doctor-review` | Dr. Lee, assigned nurse, care-coordinator, record-bot | Doctor decisions |

| Actor | Can | Cannot |
| --- | --- | --- |
| Patient (bedside tablet) | Mention a concern, read confirmed answers | See other patients' channels or cases |
| intake (Switch agent, nurse-station only) | Flag a **possible discrepancy** between a forwarded patient message and the chart, quoting the patient exactly; ask the nurse to confirm what the patient meant | Post in any patient room (it isn't a member); call a discrepancy confirmed; give clinical answers |
| care-coordinator (Switch agent, nurse-station + doctor-review) | **Carry the case between the staff rooms through Switch**; post the evidence summary in the doctor's thread; answer staff questions from the chart; remind the incoming nurse | Change the chart; say "resolved"; post in patient rooms |
| Nurse | Confirm or reject what the patient meant, escalate, accept a handoff | Change an order |
| Doctor | Check the facts, place the new order and a patient-facing explanation in doctor-review | Approve from any other room |
| record-bot + record service | Forward patient messages; post the case threads in both staff rooms and store their ids; post fixed acknowledgments and the doctor's words to patients; verify author, role, room, thread and chart version; update the chart; write the timeline | Treat anything an agent wrote as a decision |

**Why Switch is essential, and how the video shows it:** a bot moving text from room to room isn't the story. The video spends most of its staff scenes on **Switch agents working alongside people**: intake asking the nurse to confirm, care-coordinator carrying the case into doctor-review, answering Dr. Lee from the chart, and reminding the incoming nurse. Room membership enforces patient isolation, and no agent can reach a patient room. record-bot only handles the patient-facing edge and the threads that make decisions checkable.

## Trust model and safety rules

Agents extract and route. A small deterministic **record service** is the only thing that changes the chart or announces a resolution. This is what makes the core checkable by code and keeps the agent and the database from contradicting each other on camera.

**The record keeps five kinds of entry separate**, and never merges them:

1. **Said:** a patient or staff statement, with its exact quote and source (message id, or timestamp for audio)
2. **Chart:** a synthetic order or fact, with a version number
3. **Draft:** an agent's extraction, marked unverified until a nurse confirms it
4. **Decision:** a verified clinician decision, linked to the chart version it changed
5. **Task:** a follow-up with an owner (handoffs transfer the owner)

**A decision counts only if** it's a Mattermost post by a user listed as `doctor` in `roles.yaml`, in `doctor-review`, as a reply in that case's thread, in the `DECIDE` format, unedited, and naming the chart version that's current right now. Otherwise it's ignored. A stale version is rejected with a message.

| Case state | Meaning | Who moves it on |
| --- | --- | --- |
| POSSIBLE\_DISCREPANCY | intake flagged it, with a quote the service has checked | Nurse confirms or rejects what the patient meant |
| CONFIRMED\_CONFLICT | Nurse confirmed the patient's belief really differs from the active order | Doctor decides |
| REJECTED | Nurse says there's no real conflict | Closed, with the reason logged |
| RESOLVED | Verified decision applied, chart version bumped, explanation sent | Follow-up task stays open |
| HANDED\_OFF | Incoming nurse accepted | Owner changes |

**Safety rules, enforced in agent instructions *and* tested:**

- **No agent is a member of any patient room, so no agent can post there.** Switch membership enforces this, not a prompt.
- Every message a patient sees comes from record-bot: a fixed template ("Your care team is checking this (Case N). They'll answer here.") or the doctor's own words, attributed to the doctor.
- Agents are still told never to give clinical answers, but nothing they write can reach a patient.
- A patient's statement never changes the chart, however confident it sounds.
- The record service, not an agent, checks that a patient has access to a case.

## Data and message formats

The data is small and synthetic, kept in the repo so anyone can reproduce the demo. Everything lives in SQLite, seeded from these files.

**Synthetic chart (`data/patient-101.json`):**

```json
{"patient_id": "101", "display_name": "Patient 101 (fictional)",
 "chart_version": 3,
 "orders": [{"id": "ord-diet-1", "type": "diet", "value": "NPO", "reason": "procedure proc-1", "status": "active"}],
 "schedule": [{"id": "proc-1", "type": "procedure", "name": "Fictional procedure",
               "scheduled_for": "2026-11-05T09:00", "previously": "2026-11-03T09:00",
               "changed_at": "2026-11-03T07:40", "changed_by": "dr-lee"}],
 "medication_given": [{"id": "med-1", "what": "anti-nausea medicine (fictional)", "given_at": "2026-11-03T06:10", "recorded_by": "nurse-ana"}],
 "care_team": {"doctor": "dr-lee", "nurse": "nurse-ana"}}
```

The care-coordinator's answers to staff must cite a chart entry id and version (e.g. `proc-1, v3`). An answer that cites nothing doesn't belong in the demo.

**Agent claim (the intake agent posts this as a card in nurse-station; the service checks it):**

```json
{"patient_id": "101", "topic": "diet", "status": "possible_discrepancy",
 "patient_says": "believes eating is allowed",
 "quote": "Dr. Lee said it's fine now that my procedure moved",
 "source": {"room": "patient-101", "original_post_id": "...", "forwarded_post_id": "..."},
 "conflicts_with": {"order_id": "ord-diet-1", "chart_version": 3}}
```

The service rejects the card unless `quote` is an **exact substring of the original patient post**, looked up by `original_post_id`. It compares `topic` against the active order of that type **deterministically**. The LLM only fills in the fields and never sets a status beyond `possible_discrepancy`.

**Case threads:** record-bot posts the Case 17 root message in `nurse-station` when the case opens, and in `doctor-review` when the nurse escalates. The service stores **both Mattermost root post ids**. Agents and humans reply inside those threads, and decisions only count there. Because the service creates the roots, it never has to search for a post an agent made.

**Human commands (replies in the case thread):**

```text
Nurse:     CONFIRM Case 17      |  REJECT Case 17 <reason>
Doctor:    DECIDE Case 17 v3 diet=regular
           EXPLAIN: Your procedure moved to Thursday, so you can eat normally today. — Dr. Lee
Outgoing:  GIVEN Case 17 anti-nausea (fictional) 18:10
           HANDOFF Case 17 open: confirm patient ate without nausea
Incoming:  ACCEPT Case 17
```

**Wednesday stretch goal: buttons instead of typed commands.** Typed commands look clunky on video. If there's time, record-bot posts Mattermost interactive buttons (*Confirm* / *Reject*, *Approve diet change*), and the service receives each click with the clicker's `user_id`, which Mattermost verifies. Prove this in Stage 0 first. If it doesn't work locally, keep the typed commands.

**Roles (`roles.yaml`):** Mattermost usernames mapped to `patient-101`, `patient-102`, `nurse`, `doctor`, plus who's on which shift. These are resolved to `user_id`s at startup, and the service only ever matches on `user_id`.

## Voice, Calendar and Jira

Integrations make the entry stronger only if they come *after* the loop works. Added earlier, the video turns into a tour of integrations instead of a resolved problem. Each one gets one action, and each one carries the case ID.

**Priority:** the live GIVEN entry, the outgoing HANDOFF and the owner shown to the patient all come **before** any tier here. Those three prove Lantern is a shared record used by all three roles, and that matters more than Calendar, Jira or audio polish.

| Tier | What | When it's allowed in | Done when |
| --- | --- | --- | --- |
| 1 (core) | **Dictated voice:** the patient speaks using OS dictation or Wispr Flow, and the text lands in `patient-101` | Day 1 | The claim cites the exact post and quote |
| 2 | **Recorded clip:** a short fictional bedside exchange with a visible start and stop, transcribed with timestamps; claims link to a timestamp | Only after the Wed milestone | The nurse can click a claim's source and hear the matching moment |
| 3a | **Google Calendar:** after RESOLVED, the coordinator creates one follow-up event ("Case 17: check patient ate without nausea") on the care-team calendar | After tier 1 is recorded working | The event shows Case 17 and the owner |
| 3b | **Jira:** one task ("Case 17: confirm the patient received Dr. Lee's explanation") with owner and status. ACCEPT moves the owner to the incoming nurse | After 3a, or in parallel if someone's free | The task's owner changes on ACCEPT |

**Rules for integrations:**

- Calendar is for scheduling and Jira is for tracking work. **Neither is the medical record, and neither approves anything.**
- Switch lists Google Workspace and Jira as agent tools. Confirm on **Wednesday** that Console 0.40.1 actually offers the specific actions we need (create event, create and update issue) and the access grants they require, before planning around them. If they're missing, have the record service call the APIs directly.
- Use test accounts and a test calendar and Jira project. No real people or data.
- **Recording real patients is out of scope entirely.** Recording raises consent, privacy and storage requirements far beyond a hackathon.

## Build plan

The agent-only loop has to work by Tuesday at 8 PM PT, or we switch back to Blast Radius. The version where the service verifies decisions is due by the end of Wednesday. Everything else waits until both work.

**Stage 0 (Tue, from 10:31 AM PT, about 2 hours):**

1. Assign owners. Recreate the rooms and agents fresh, rather than reusing the Nov 2 test setup.
2. Create the 4 rooms, the 2 agents (intake in nurse-station; care-coordinator in nurse-station and doctor-review) and the accounts: patient-101, patient-102, nurse-ana, nurse-ben, dr-lee, and record-bot with a token. **Don't add agents to the patient rooms.**
3. **Forwarding:** record-bot reads a new post in patient-101 through the Mattermost API and reposts it in nurse-station, mentioning intake and keeping the original post id. intake replies in nurse-station.
4. **Thread roots:** record-bot posts a `Case TEST` root in nurse-station and in doctor-review, and the service stores both post ids. **Check that both agents can reply inside a thread that record-bot started**, and that the service can read those replies with author, channel and root id.
5. **Switch hop:** care-coordinator, addressed in nurse-station, posts in doctor-review's Case TEST thread.
6. **Isolation:** the patient-102 account can't read patient-101's channel, and Switch refuses when intake tries to connect to patient-101.
7. **No loops:** record-bot's posts don't set off an agent reply chain.
8. *(Optional)* **Buttons:** an interactive button posted by record-bot sends its click, with the `user_id`, to the service.

**Day by day:**

1. **Tue:** Stage 0, then the agent-only loop: patient message → forwarded → case card → nurse → doctor → the doctor's words back to the patient. A hand-run script can stand in for record-bot today. If behind, share one nurse account until Wednesday. **Fallback check at 8 PM PT.**
2. **Wed:** record service: SQLite, chart seeding, CONFIRM/DECIDE checks, chart versions, RESOLVED, the doctor's words relayed word for word. **Book the nurse review call (required, before Thursday).** **Milestone, end of Wednesday:** the full Case 17 loop works live with the service doing the checking. Record a rough take.
3. **Thu:** nurse call done and quoted in the README. One live GIVEN entry, outgoing HANDOFF plus incoming ACCEPT, the follow-up owner shown to the patient (all three come before Calendar and Jira), the isolation scene, the timeline view, all 7 must-pass tests, then tier 3a/3b if time allows.
4. **Fri:** recorded clip (tier 2) only if everything above is done. Then README, setup script, blog post, final video. A second person reproduces the demo from the README.
5. **Sat morning:** buffer only. Submit by 10:29 AM PT.

**Seven must-pass tests:**

- [ ] Three casual mentions each open a **possible discrepancy** against the NPO order, and none are marked confirmed: "can't wait for breakfast, Dr. Lee said it's fine", "the doctor cleared me to eat today", "I'll have lunch when it comes"
- [ ] A card whose quote isn't an exact substring of the original post is rejected, and the patient gets **no** acknowledgment until a case actually opens
- [ ] No agent can post in a patient room (Switch refuses intake connecting to patient-101), and a patient's question only ever gets the fixed template
- [ ] DECIDE from a nurse, a bot or an agent, from outside the doctor-review case thread, or naming a stale chart version, is ignored or rejected with a message
- [ ] Patient 102 can't see Case 17, whether through Switch or the service
- [ ] Restarting the service creates no duplicate case, thread root or patient message
- [ ] GIVEN and HANDOFF only count from the outgoing on-shift nurse, and GIVEN never changes an order. ACCEPT only counts from the incoming nurse after a HANDOFF, and the patient's "Following up" line changes only then

**Stack:** Python 3.11+, standard library plus PyYAML, SQLite, the Mattermost REST API. No web framework. The timeline view is a generated Markdown/HTML page or a room post.

## Roles

One owner per part of the system. Fill in names at kickoff.

| Role | Owns | Delivers | Owner |
| --- | --- | --- | --- |
| Record service lead | `record.py`: SQLite, chart versions, case states, decision verification, timeline | Wed milestone; tests 2, 3, 5, 6 | TBD |
| Switch lead | Rooms, members, the 2 agents' instructions (intake, care-coordinator), addressing rules, record-bot, thread seam | Stage 0 items 2–6; Tue loop; tests 1, 4 | TBD |
| Story + data lead | Synthetic charts, `roles.yaml`, Case 17 script, nurse reviewer contact, video | Demo script; final video; checks with a nurse | TBD |
| Integrations + docs lead | Calendar and Jira (tier 3), recorded clip (tier 2), README, setup script, blog, #HowISwitch | Tier 3a/3b; reproducible setup | TBD |

**With fewer people:** two people means one takes Record + Integrations and the other takes Switch + Story. Solo means follow the day plan in order and cut tier 2 and tier 3b first.

**One rule:** only the record service lead changes how a decision gets accepted, and every change to that logic gets reviewed by someone else.

## Brief fit: two weak spots and the fixes

Lantern meets every requirement of the brief. Two points are only just met, and the video has to make the case for them.

| Requirement | Weak spot | Fix |
| --- | --- | --- |
| Switch connects the agent and the team | record-bot calls Mattermost directly for patient messages, thread starts and checks. If the video is mostly record-bot posts, Lantern looks like a bot app with Switch as an extra. | Keep record-bot quiet on screen: short plain lines only (forwarded message, ✓ or ⚠, verdict). Most staff scenes show agents and people in the threads. The README says it plainly: *agents do the teamwork through Switch; code handles the patient edge and the checks.* |
| A real task, done | It is fictional, so "real" depends on believability. | Quote the nurse reviewer in the README and in the video's last 10 seconds (real quote, with permission, by role). |

**Evidence receipts** are presented as how a good teammate works: every claim the agent makes comes with its source, which the system checks (lookup log plus a ✓ or ⚠ card). They are not presented as distrust.

## Risks and cut line

The biggest risk is scope: the full vision (always-on bedside microphones, a hospital-wide record, assistants for every role) would give us an impressive mockup and an unconvincing workflow. When time runs short, cut an integration, never the loop.

| Risk | Effect | Fallback |
| --- | --- | --- |
| Agent-only loop not working by Tue 8 PM | No foundation | Switch to Blast Radius Wed morning |
| An agent answers a clinical question to a patient | Safety credibility gone | **Can't happen by design:** agents aren't members of patient rooms |
| intake misses the conflict in a casual mention | The case never opens on camera | Test 1 with 3 phrasings before every take; a stronger model for recording |
| Patients in a chat app look unrealistic | Judges doubt it's a real workflow | Present patient channels as bedside tablets in the first scene |
| The service can't find the case card in Mattermost | Can't check decisions | Search nurse-station for `Case N` from intake's account; worst case, record-bot posts the card itself |
| Nobody on the team knows clinical work | Judges question realism | **Required:** a 15-minute nurse review before Thursday, quoted in the README |
| Calendar or Jira tools not available in Console 0.40.1 | Tier 3 slips | The service calls the APIs directly, or drop tier 3 |
| Judges see it as "Abridge in Slack" | Low creativity score | Open with the conflict, not with capture; say the difference in the first 15 seconds |

**Cut order when behind:** tier 2 recorded clip → tier 3b Jira → tier 3a Calendar → timeline view polish → isolation scene (keep the test, cut the scene).

**Never in scope:** continuous recording, speaker recognition, real patient data, medication recommendations, an EHR integration, a separate patient web app.

## Submission checklist

Submit by **Sat Nov 7, 10:29 AM PT**. Aim for Friday night.

- [ ] Public repo, README: the problem, a 30-second GIF of Case 17, setup steps, the room diagram, trust model, a "fictional data, not for clinical use" banner
- [ ] README section "What breaks without Switch"
- [ ] Demo video, 2:30–2:45, every scene from a real run
- [ ] Blog post (Best Blog prize): closing the loop when a patient's words and the chart disagree
- [ ] \#HowISwitch post (keyboard prize)
- [ ] Any Switch bug we fix goes in as a PR to `sandbox-quantum/switch` (Core Contribution prize)
- [ ] Wispr Flow: if we build by voice, check that prize's rules and keep evidence
- [ ] Final pass: every claim in the README and video matches what the running code does

## Sources

- [Flip the Switch event page](https://luma.com/switchai) · [Hackathon rules and judging](https://www.wemakedevs.org/hackathons/switch)
- [Switch repository](https://github.com/sandbox-quantum/switch) · [Switch rooms](https://www.switchagents.ai/rooms)
- [Abridge for nursing](https://www.abridge.com/platform/nursing) · [Healthcare IT News: Abridge ambient AI for nurses](https://www.healthcareitnews.com/news/abridge-releases-ambient-ai-tech-nurses) · [Epic Emmie](https://www.epic.com/software/emmie/)
- [AHRQ TeamSTEPPS handoff tool](https://www.ahrq.gov/teamstepps-program/curriculum/communication/tools/handoff.html)
- [HHS telehealth privacy and security](https://telehealth.hhs.gov/providers/best-practice-guides/privacy-and-security-telehealth/develop-privacy-and-security)
- Fallback plan: [Blast Radius team brief](https://claude.ai/artifact/HnjD3wYy1D739H8wUqRUDY)

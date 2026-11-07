# Lantern dashboard: everything the UI can show (spec for Stitch)

One screen for staff, read-only, polling every 1.5 s. Served by the record service at `http://127.0.0.1:8099/`. The UI **cannot change anything**; it never POSTs. All data is fictional and the page must always show "Fictional data, not for clinical use".

Primary use: it sits next to Mattermost in the demo video so a viewer can see state changing while people and agents post in threads.

## 1. Paste this into Stitch

> Design a dark, high-trust "mission control" web dashboard for a hospital care-coordination demo called **Lantern** (fictional data). Desktop 1440x900 first, then a 390px mobile layout. Audience: judges watching a 2-minute screen recording, so it must read at a glance and look polished and calm, not sci-fi. Layout: top bar, left rail of cases, a center stage showing a horizontal 6-step pipeline for the selected case plus two live feeds (evidence ledger, case timeline), a right rail with the simulated chart and a command audit. Colors: deep navy background, one warm amber accent for the brand and "pending", green for verified/done, cyan for current/active, red only for refused/stale, violet for handoff. Use clear status chips, a subtle glow on the active pipeline step, and a flash on newly arrived rows. Include a presentation mode with larger type. Content and states are listed below.

(then paste sections 2 to 6 below)

## 2. Screen regions and their data

### Top bar
- Logo "LANTERN" + "mission control"
- Live indicator: green pulsing dot + "live 20:22:06" / red dot + "offline (reason)" when the service is unreachable
- Presentation-mode toggle (key **P**)
- Fixed banner: "Fictional data, not for clinical use"
- Optional: patient picker (101, 102, 103, 104), role switch (nurse / doctor view of the timeline)

### Left rail: Case list (newest first)
Each case card: `Case 17`, state chip, patient id, topic (diet / activity), owner, short patient quote. Selected card highlighted. Count of open cases is an optional header badge.
States and suggested color: `POSSIBLE_DISCREPANCY` amber, `CONFIRMED_CONFLICT` cyan, `RESOLVED` green, `HANDED_OFF` violet, `REJECTED` red.

### Center top: Case pipeline (6 steps, left to right)
1. **Patient says** (patient room)
2. **intake** (agent claim card)
3. **Nurse** (CONFIRM)
4. **care-coordinator** (agent, cited facts)
5. **Doctor** (DECIDE)
6. **Owner** (handoff / ACCEPT)

Step states: *not reached* (dim), *current* (glow), *done* (green), *blocked/rejected* (red, used at step 3 when the nurse REJECTs; later steps stay dim). Connecting wires animate when the step before is done.
Under it: "Case 17 - HANDED OFF - owner nurse-ben", the patient's exact quote in italics, "conflicts with ord-diet-1 at chart v3".

### Center middle: Evidence ledger
One row per lookup an agent made, from the service's own log: `lookup #31`, agent (`care-coordinator`), entry (`ord-diet-1`), chart version read, label (`Diet order`), value (`NPO`), time, and a badge **✓ current** or **⚠ STALE** (stale when the chart has moved past the version read). Optional: a banner line "2 of 2 cited facts verified" (from the timeline's AGENT CLAIM CHECK row). Empty state: "no agent has fetched anything yet".

### Center bottom: Case timeline
Rows never merge kinds. Columns: time, kind label, actor, text, source. Kind labels and meaning:

| kind | label | meaning |
| --- | --- | --- |
| said | SAID | the patient's own words |
| draft | DRAFT (unverified) | an agent's claim before confirmation |
| nurse | NURSE CONFIRMED | nurse confirmed or rejected |
| agent | AGENT CLAIM CHECK | record-bot checked an agent's cited facts |
| fetch | LOOKUP | a chart lookup (with a STALE marker if outdated) |
| chart | SIMULATED CHART | chart version change, e.g. v3 -> v4 |
| decision | CLINICIAN CONFIRMED | the doctor's decision and explanation |
| given | GIVEN | medication recorded as given (order unchanged) |
| handoff | HANDOFF | outgoing nurse handed off, what is still open |
| task | OWNER | who owns the follow-up now |

Optional toggle: nurse view / doctor view, and a "patient view" preview showing only SAID, CLINICIAN CONFIRMED, OWNER (what the patient may see).

### Right top: Simulated chart
Header: patient display name, `chart v4`. List of **orders** (type, value, status `active` or `superseded` shown struck through, reason), **schedule** entries (name, scheduled time, previously, changed by), **medication given** (what, when, recorded by), **care team** (doctor, nurse). Below: **version history** chips `v3 seed`, `v4 dr-lee` with the current one highlighted. Optional: a diff view between two versions.

### Right bottom: Command audit (newest at bottom)
Every command the service accepted or refused: action (`CONFIRM`, `DECIDE`, `GIVEN`, `HANDOFF`, `ACCEPT`, `REJECT`, `claim_card`, `patient_message`, `claim_check`), user, room, outcome chip (**accepted** green, **rejected** red, **ignored** grey), and the reason text (for example "only a verified doctor can decide", "not a reply in that case's doctor thread", "edited posts never count", "stale chart version").

## 3. Ideas the data supports (pick what looks good)
- Room map: four rooms (`patient-101`, `patient-102`, `nurse-station`, `doctor-review`) with who is in which, agents shown only in the two staff rooms, a lock icon on patient rooms.
- "Who can do what" legend: patient says, nurse confirms, doctor decides, only code changes the chart.
- Trust meter: count of ✓ verified vs ⚠ unverified citations.
- Case duration timer from first SAID to RESOLVED.
- Handoff card: from nurse, open items, accepted by, pending state.
- Empty states for every panel; error state for "service offline".
- Refusal toast that pops when a new red audit row arrives.

## 4. Interactions (all read-only)
- Click a case: reloads pipeline, ledger, timeline and chart for that case's patient.
- Hover a lookup or timeline source: tooltip with the raw ids.
- Press **P** or click Present: larger type, hide raw ids.
- Newly arrived rows flash for about 1 second.
- Optional: filter audit by outcome; filter timeline by kind.
- Optional URL params: `?key=<api key>` (if the service requires one), `?api=http://host:8099` (when the page is opened as a file).

## 5. Data contract (what the page can read; field names are exact)

| Endpoint | Returns |
| --- | --- |
| `GET /api/patients` | `[{patient_id, display_name, chart_version}]` |
| `GET /api/patients/<id>/chart` | `{patient_id, display_name, chart_version, orders:[{id,type,value,reason,status}], schedule:[{id,type,name,scheduled_for,previously,changed_at,changed_by}], medication_given:[{id,what,given_at,recorded_by}], care_team:{doctor,nurse}}` |
| `GET /api/patients/<id>/chart/versions` | `[{version, changed_by, ts}]` |
| `GET /api/cases[?patient=&state=]` | `[{id, patient_id, state, topic, quote, patient_says, order_id, chart_version, owner, ts, ...}]` |
| `GET /api/cases/<n>` | `{case, events:[{id,patient_id,case_id,kind,actor,text,source,ts}], decision:[{doctor,from_version,to_version,change,explanation,ts}], task:[{text,owner,accepted}], handoffs:[{from_nurse,open_text,accepted_by,ts}], medication_given:[{what,given_at,recorded_by}]}` |
| `GET /api/lookups[?agent=]` | `[{id, ts, agent, patient_id, entry, version, label, value}]` |
| `GET /api/audit[?limit=]` | `[{id, user_id, room, action, outcome, reason, ts}]` |
| `GET /api/timeline/<id>?role=nurse\|doctor[&format=html]` | Markdown or HTML, role-scoped |
| `GET /healthz` | `{status, cases}` |

`ts` values are Unix seconds. Patients 101 and 102 have live chat accounts; 103 and 104 are backend data only.

## 6. Constraints for the design
- Read-only: no buttons that look like they change a case. Any "Confirm" or "Decide" button would be misleading.
- Static HTML/CSS/JS in a single file or small folder, no build step, no framework required, system fonts or one Google Font.
- Must work as `http://127.0.0.1:8099/` and as a file. Dark theme first; light theme optional.
- Contrast good enough to read in a compressed screen recording; minimum 13px body text, 18px in presentation mode.
- Keep the fictional-data banner visible at all times.

## 7. Handing the Stitch design back
Export the HTML/CSS (or screenshots plus the Stitch link) and give it to Claude Code with: "Rebuild `lantern/ui.html` from this design. Keep the data wiring (`tick()`, the `/api` calls, `BASE`, `?key=`) and the `P` shortcut. Do not add any write calls." Run the tests after (`python -m unittest discover -s tests`); one test checks the banner text and that the page never POSTs.

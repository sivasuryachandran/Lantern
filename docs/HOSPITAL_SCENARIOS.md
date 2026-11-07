# Lantern as a whole ward: scenarios, agents, and what is tracked where

**Rule for every scenario:** agents notice and route, people decide and close, code enforces and records. Every open item has an owner and a way to be closed, and the record shows who closed it and when.

Status words are literal: **built** = in the code and covered by tests (and run against a local Mattermost with scripted stand-ins); **designed** = described here, not implemented; **not supported** = the code refuses it today.

## Rooms (all private Switch/Mattermost rooms; membership in `config/roles.yaml`)

| Room | Who | Status |
| --- | --- | --- |
| `patient-101` to `patient-104` | the patient and record-bot; never an agent | built |
| `nurse-station` | nurses, intake, care-coordinator, record-bot | built |
| `doctor-review` | Dr. Lee, Nurse Ana, care-coordinator, record-bot | built |
| `orders` | write-only feed of every simulated chart change | built |
| `medication` | write-only feed of every `GIVEN`, apart from orders | built |
| `room-service` | Sam and Rita (room service), nurses, record-bot. Tray and turnover tasks; staff close them with `DONE <task id>` | built |
| `pharmacy`, `lab`, `transport`, `bed-management`, `discharge` | designed (below) | designed |

## Data the ward holds (`data/rooms.json`, fictional)

Each ward room (`4W-101` to `4W-104`) records who is there now, **who was there before** (reference, discharge time, precautions, diet, notes) and the **turnover checklist** for that earlier stay with its state: done (by whom, when) or still open. Example: `4W-102`'s previous occupant was on contact precautions (a fictional example); the terminal clean and linen are done, the equipment sanitizing and sharps check are **still open**. `GET /api/rooms`, `/api/rooms/<room>`, `/api/tasks?status=open`, and the dashboard's "Rooms & turnover" panel show it.

## Agents

**Built and used:** `intake` (nurse-station), `care-coordinator` (nurse-station + doctor-review). See `docs/agents/`.

**Internal agents (plain code, no model; every use is logged):**

| Internal agent | What it does | Status |
| --- | --- | --- |
| chart-lookup | `GET /chart/<patient>/<entry>`: returns a fact and logs a numbered lookup | built |
| receipt-checker | compares each cited fact to the lookup log: ✓ verified, ⚠ unverified or stale | built |
| room-ledger | read-only room and task state (`/api/rooms`, `/api/tasks`) | built |
| task-tracker | opens a room task when a decision needs follow-up (a tray change), closes it on `DONE`, mirrors it to Jira if configured | built (Jira unit-tested only) |
| scheduler | Google Calendar follow-up event on a resolved case | built (unit-tested only, not run live) |
| audit-log | every accepted, rejected and ignored command with the reason | built |

**Designed Switch agents (instructions written, none created in Console, none run):** `housekeeping-coordinator`, `dietary-coordinator`, `pharmacy-liaison`, `bed-manager`, `discharge-planner`, `handoff-briefer`. See `docs/agents/`.

## Scenarios

| # | Scenario | Agent that notices or routes | Person who decides or closes | Recorded as | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | Patient says breakfast is fine; chart says NPO | intake, care-coordinator | nurse confirms, Dr. Lee decides | said, draft, nurse confirmed, lookup, decision, chart v3 → v4, owner | built |
| 2 | Patient says they can walk alone; order says assist required | intake | nurse confirms; Dr. Lee decides (left open in the demo) | same record kinds | built (data for 102) |
| 3 | A diet decision changes what the tray should be | task-tracker | room service closes with `DONE` | `orders` feed, `room-service` feed, room task, ROOM SERVICE timeline row, Jira task if configured | built |
| 4 | A nurse gives a medicine | none | outgoing nurse posts `GIVEN` | `medication` feed, GIVEN row, order unchanged | built |
| 5 | Shift change for a resolved case | care-coordinator briefs | outgoing `HANDOFF`, incoming `ACCEPT` | owner changes everywhere | built |
| 6 | Shift change for a case still waiting on the doctor | care-coordinator | would need a handoff | | **not supported**: `HANDOFF` requires a resolved case; the case stays with its owner |
| 7 | Nurse tries to change an order | none | refused by code | audit row, no chart change | built |
| 8 | Stale or uncited fact from an agent | receipt-checker | the doctor sees ⚠ | lookup log, audit | built |
| 9 | Patient asks about another patient's case | record-bot | refused | fixed template, audit | built |
| 10 | Turnover: which cleanup tasks are done or open for the room's previous stay | room-ledger | room service closes tasks | rooms and tasks tables, dashboard panel | built (read and close); creating tasks at discharge is designed |
| 11 | New patient assigned to a room whose previous occupant had precautions | bed-manager | charge nurse | would warn if turnover for that precaution is still open | designed |
| 12 | A turnover task stays open too long | housekeeping-coordinator | room service or charge nurse | escalation message | designed |
| 13 | Tray conflicts with an allergy or an NPO order | dietary-coordinator | nurse, Dr. Lee | would cite the diet order and allergy entry | designed |
| 14 | A medicine is due or was given twice | pharmacy-liaison | pharmacist or nurse | `medication` feed | designed |
| 15 | Discharge: follow-up, transport, room turnover | discharge-planner | doctor signs, nurse closes | tasks, calendar | designed |
| 16 | Follow-up check after a resolved case | scheduler | the owning nurse | Calendar event | built (unit-tested only) |

## What is tracked where

| Where | What | Status |
| --- | --- | --- |
| Lantern database (SQLite) | charts, cases, events, decisions, lookups, audit, rooms, room tasks | built, tested |
| Mattermost rooms and threads | every conversation and every feed | built, run locally |
| Jira | one task per resolved case, and one per room task Lantern opens | built; unit-tested against a fake HTTP layer; **not run against a real Jira** |
| Google Calendar | a follow-up event on a resolved case | built; **not run live** |
| Switch room documents (for example a handoff sheet) | not written by us | designed only; I have not verified Switch's room-document feature here |
| Scheduled or recurring checks (for example aging tasks) | not built | designed |

Nothing in the Jira or Calendar hooks is the medical record or approves anything, and a failing integration never blocks the loop.

## What room service did (from a local run, fictional)

After Dr. Lee's decision on Case 18, record-bot opened `T-101-D18` ("Update the tray: diet NPO → regular"). A nurse's `DONE` was **refused** (only room service can close it); Sam's was accepted and recorded, and `4W-101` showed one open task left. Sam also closed `T-102-3`, so `4W-102` went from 2 of 4 to 3 of 4 turnover tasks done.

# Closing the loop when a patient's words and the chart disagree

*Draft for the Best Blog prize. Fictional data throughout. Fill in the bracketed parts from the real build and the nurse call.*

A patient tells their bedside tablet that Dr. Lee said breakfast is fine. The chart says nothing by mouth. Both can be true: the procedure moved, the doctor said so, and the order hasn't caught up. Whose job is it to sort that out?

Lantern is a small workflow built on Switch where that question always has an answer.

## The rule

Agents extract and route. A small deterministic record service is the only thing that changes the (simulated) chart. A decision counts only if it comes from a doctor, in the right room and thread, unedited, naming the current chart version.

## What Switch does

- **Rooms are the boundary.** Four rooms, and no agent is a member of any patient room, so no agent can post there. Patient 102 cannot open patient 101.
- **Agents work alongside people.** intake asks the nurse what the patient meant. care-coordinator, a real coding agent, answers the doctor from the live chart.
- **The service checks the agents.** Every `(chart: id, vN)` citation is verified. Invented ones are flagged in the thread.

## What I'd tell the next builder

The pattern isn't medical: *only a verified owner can change shared state, and agents route.* [One paragraph on what you learned, including anything that broke.]

## What it is not

Not an AI medical record, not clinical software, not HIPAA-ready. It is a workflow demo with fictional data. [Quote from the nurse review.]

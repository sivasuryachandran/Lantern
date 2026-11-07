# Closing the loop when a patient's words and the chart disagree

*Draft for the Best Blog prize. Fictional data throughout. Fill in the bracketed parts from the real build and the nurse call.*

A patient tells their bedside tablet that Dr. Lee said breakfast is fine. The chart says nothing by mouth. Both can be true: the procedure moved, the doctor said so, and the order hasn't caught up. Whose job is it to sort that out?

Lantern is a small workflow built on Switch where that question always has an answer.

## The rule

Agents extract and route. A small deterministic record service is the only thing that changes the (simulated) chart. A decision counts only if it comes from a doctor, in the right room and thread, unedited, naming the current chart version.

## What Switch does

- **Rooms are the boundary.** Four rooms, and no agent is a member of any patient room, so no agent can post there. Patient 102 cannot open patient 101.
- **Agents work alongside people.** intake asks the nurse what the patient meant. care-coordinator, a real coding agent, answers the doctor from the live chart.
- **The service checks the agents.** Every citation like `[proc-1 v3 · lookup #31 = Thu 9:00]` is checked against the lookup log, and the thread shows what the log says, not what the agent said. A missing, wrong or stale one gets a warning instead of a check mark.

## What I'd tell the next builder

The pattern isn't medical: *only a verified owner can change shared state, and agents route.* What broke along the way, once real agents were involved: Switch's own message ids (`sw_...`) are not Mattermost ids, so intake could not cite the forwarded post until we gave it a lookup for the real one; Switch's "Working..." progress posts looked like unverified claims until the receipt check learned to ignore them; and care-coordinator answered in the channel instead of the case thread until its instructions said to reply in the thread. Each fix went into the agent's instructions or a small lookup endpoint, never into a weaker check.

## What it is not

Not an AI medical record, not clinical software, not HIPAA-ready. It is a workflow demo with fictional data.

## Voice is how a ward talks

[Write after the Wispr set-up is done: why we built Lantern by voice, and for voice. Mention Privacy Mode, and only claim what you actually dictated. See docs/WISPR.md.]

"""Voice-over beats for the 3-minute demo: (start seconds, text). Text is the script's VO, split at its shot boundaries.
The slot of a beat ends where the next one starts. AGENT_PROVIDER (e.g. "OpenCode") names the provider; unset, the video says "coding agents"."""
import os

PROVIDER = os.environ.get("AGENT_PROVIDER", "").strip()
AGENTS = f"{PROVIDER} agents" if PROVIDER else "coding agents"
END = 178.0

BEATS = [
    (0.0, "It's early morning on a hospital ward. Patient 101 has just heard that her procedure moved to Thursday, and to her that means breakfast."),
    (6.0, "Her chart still says nothing by mouth."),
    (12.0, "This happens on every shift. What a patient was told, what's on the chart, and who's handling the difference drift apart, especially when the shift changes. Lantern keeps those three things together, inside the chat the care team already uses."),
    (24.0, "Here's the setup. Four Mattermost rooms: a bedside tablet room for each patient, a nurse station, and a doctor review room. Two AI agents join through Switch, and only the staff rooms. Everything after this point is a live run. The human lines are played from a script so anyone can reproduce it."),
    (38.0, "She mentions it in passing. She isn't asking anything. Lantern passes her message to the nurse station..."),
    (46.0, "...and the intake agent notices it clashes with the diet order. It quotes her exactly and calls it a possible discrepancy. It doesn't decide anything."),
    (56.0, "Only once the case is open does she hear back, and it's a fixed message, not an AI guess."),
    (60.0, "Nurse Ana confirms what the patient meant, right in the thread."),
    (68.0, "Now the coordinator agent carries the case into the doctor's room through Switch. Watch the receipts. When it says when the procedure moved, it cites a lookup number and the chart version it read. Lantern checks that the fact really matches the chart at that version, and only then marks it verified. The check proves the source is right. The medical decision still belongs to the doctor."),
    (92.0, "Here Ana tries to change the order herself. Lantern refuses. Only a verified doctor, in the doctor's thread, can change it. That's enforced in code, not in a prompt."),
    (102.0, "Dr. Lee checks the schedule and makes the call. The simulated chart moves from version three to version four."),
    (112.0, "The patient gets Dr. Lee's own words, not an AI rewrite, and the name of the nurse following up."),
    (120.0, "At seven, the shift changes. Ana records the dose she gave, kept separate from the orders, and hands off what's still open. The coordinator walks Ben through it, Ben accepts, and the patient can see that he owns it now. That's the last light."),
    (142.0, f"Under the hood, it's simple on purpose. The two agents are {AGENTS}, connected through Switch Console. Switch decides who's in which room, who can address which agent, and keeps every reply in its thread. A small Python service with a SQLite record does everything that has to be exact: it forwards messages, opens case threads, logs every chart lookup, and checks every decision for the right person, room, thread and chart version."),
    (160.0, "And we test the parts that matter: refused decisions, stale facts, sealed patient rooms."),
    (166.0, "Agents notice. People decide. Code enforces. Lantern."),
]

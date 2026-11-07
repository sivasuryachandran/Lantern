"""Voice-over beats for the 3-minute demo: (start seconds, text). Text is the script's VO, split at its shot boundaries.
The slot of a beat ends where the next one starts. AGENT_PROVIDER (e.g. "OpenCode") names the provider; unset, the video says "coding agents"."""
import os

PROVIDER = os.environ.get("AGENT_PROVIDER", "").strip()
AGENTS = f"{PROVIDER} agents" if PROVIDER else "coding agents"
END = 180.0

BEATS = [
    (0.0, "At shift change, a nurse doesn't hand over one question. She hands over patients, medicines already given, decisions still waiting. Lantern keeps all of it in one shared record, inside the team's chat."),
    (15.0, "Here's one concern, end to end. Patient 101 mentions breakfast in passing. The intake agent, working through Switch, notices her chart still says nothing by mouth, quotes her exactly, and flags it as possible. It doesn't decide."),
    (30.0, "Ana confirms what the patient meant. The coordinator agent carries the case into the doctor's room and cites the chart with a receipt. Lantern checks that the cited value matches the lookup it logged at that chart version, and only then marks it verified."),
    (58.0, "A nurse can't change the order here. Only a verified doctor can. Dr. Lee decides, the simulated chart moves to version four, and the patient gets her exact words, not an AI rewrite."),
    (82.0, "One decision reaches the whole ward. The orders room logs the new chart version. Room service gets a tray task, only room service can close it, and the record shows who did and when. Medication keeps what was given separate from what was ordered."),
    (100.0, "Everything lands in one record, and nothing gets blurred together. What she said, what the chart said, what was checked, what was decided, and who owns what's next. Each role sees the same record through its own window."),
    (115.0, "And it isn't just Patient 101. Patient 102's question about walking alone is confirmed and waiting on the doctor, and Ana still owns it."),
    (125.0, "Seven o'clock. Ana hands over everything that's still open, across both patients. The coordinator walks Ben through it, with sources. Ben accepts, and the whole ward knows he owns it now."),
    (150.0, f"Two {AGENTS} in Switch rooms do the noticing and the legwork. A small service enforces the rules and keeps the record."),
    (165.0, "Agents notice. People decide. Code enforces. Lantern."),
]

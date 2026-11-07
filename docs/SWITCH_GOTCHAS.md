# Switch gotchas (for the blog's "how I set up Switch" section)

All of these were hit while building Lantern on Switch Console 0.40.1 (Windows) with Claude Code agents. Each was fixed in Switch configuration or in Lantern, never by loosening a check.

1. **A new agent is owner-only.** Our service account (record-bot) posted `@intake` and got: "I only take instructions from my owner, and this chat account isn't linked to a Switch user yet." Fix: in the agent's settings, "Who can talk to your agent" is the addressing policy. Do not stop at "Anyone" (gotcha 2).
2. **Switch puts agents in Mattermost's default channels.** Both agents were in Town Square, where our patient accounts are members and Mattermost cannot remove anyone. With "Anyone", a patient could `@intake` there. Fix: custom rules (users any, agents none, rooms only the agent's staff rooms). After that `@intake` in Town Square got: "You're not permitted to direct messages to me in this room — my operator has restricted who can address me here."
3. **Agent ids are not Mattermost ids.** intake put Switch's own message id (`sw_...`) where the card needs the Mattermost post id, and the card was rejected. Fix: a plain-code lookup (`/forwarded/<post id>`) the agent calls and copies from, so the check stays strict.
4. **Agents post progress messages.** "Starting a session...", "Working... 13s" and "Queued..." are posts. A checker that replies to every agent post, then re-triggers the agent, loops. Fix: ignore progress posts; they carry no claims.
5. **Agents may answer top-level.** care-coordinator posted its summary as a new channel message instead of a reply, so the thread check never saw it. Fix: say "reply inside that same thread" in the agent's instructions.
6. **Agents are slow and queue.** A reply takes 15 to 70 seconds, and a backlog drains after you reset things. Wait for the agents to go idle before a recorded run.
7. **The Console only lists rooms an agent is in.** Private patient rooms with no agent do not appear, which is the point, but it means "Switch refuses an agent in a patient room" could not be demonstrated from the Console.
8. **Mattermost's port is random.** Switch Console runs it in Docker on a chosen port (we saw 64096), so set `MM_URL` accordingly.
9. **Windows:** Lantern's `%-H` time format and `.venv/bin` paths broke; fixed in the repo.

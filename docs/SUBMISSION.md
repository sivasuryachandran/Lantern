# Submission checklist (closes Sat Nov 7, 10:29 AM PT; aim for Friday night)

Done (verified Nov 4 to 6; details in the README "Verification status"):

- [x] intake and care-coordinator created in Switch Console, usernames match `config/roles.yaml`, addressing restricted to their staff rooms
- [x] `scripts/check_intake.py` passes (three casual phrasings) against the real agent
- [x] `scripts/live_e2e.py` passes (Nov 6, scripted stand-in agents; rerun after any change)
- [x] `python -m unittest discover -s tests` passes (51 tests)
- [x] Full Case 17 with the real agents, four runs, plus live refusals (nurse, patient, top-level, stale version) and the GIVEN / HANDOFF / ACCEPT scene
- [x] README: problem, setup, room diagram, trust model, "fictional data, not for clinical use" banner
- [x] README "How Switch is used (and what breaks without it)" matches what the running code does
- [x] Nurse review: not done; the README says so plainly and the video has no quote card (decision made; do not invent a quote)
- [x] Fresh `git clone` + README setup, tests and offline demo passed on Nov 6 on one machine

Still open:

- [ ] Roles in the plan filled in (one owner per part)
- [ ] 30-second GIF of Case 17 in the README (needs a screen recording)
- [ ] Demo video, 2:30 to 2:45, from real runs (`docs/DEMO_SCRIPT.md`); record-bot kept quiet on screen; staff scenes show agents and people in threads. Reset `lantern.db` first so the case is Case 17. Generated B-roll, if used, is only cutaways (`docs/BROLL_PROMPTS.md`) and is disclosed as generated.
- [ ] Blog post (`docs/BLOG.md`) published
- [ ] #HowISwitch post (`docs/HOWISWITCH.md`)
- [ ] Code with Wispr: dictated prompts, agent instructions and docs; **Insights scorecard screenshot** saved as `docs/wispr-scorecard.png` and added to the submission (`docs/VOICE_LOG.md`)
- [ ] Any Switch bug fixed upstream as a PR to `sandbox-quantum/switch` (none confirmed yet; candidates: Switch adds agents to Mattermost's Town Square, and a new agent ignores its creator until they link an account)
- [ ] A second person reproduces the demo from the README (the Nov 6 fresh-clone run was one machine; still needs a real second person)
- [ ] Delete the `lantern-admin` Mattermost account and its tokens after the final recording

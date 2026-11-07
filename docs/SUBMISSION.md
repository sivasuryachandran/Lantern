# Submission checklist (closes Sat Nov 7, 10:29 AM PT; aim for Friday night)

- [ ] Roles in the plan filled in (one owner per part)
- [ ] intake and care-coordinator created in Switch Console, usernames match `config/roles.yaml`
- [ ] `scripts/check_intake.py` passes (three casual phrasings) against the real agent
- [x] `scripts/live_e2e.py` passes against the final setup (Nov 6, stand-in agents; rerun after any change)
- [x] `python -m unittest discover -s tests` passes
- [x] Nurse review: not done; README says so plainly and the video has no quote card (decision made; do not invent a quote)
- [ ] Video: record-bot kept quiet on screen; staff scenes show agents and people in threads
- [ ] Public repo with README: problem, 30-second GIF of Case 17, setup, room diagram, trust model, "fictional data, not for clinical use" banner
- [ ] README "What breaks without Switch" matches what the running code does
- [ ] Demo video, 2:30 to 2:45, from real runs (`docs/DEMO_SCRIPT.md`)
- [ ] Blog post (`docs/BLOG.md`) published
- [ ] #HowISwitch post (`docs/HOWISWITCH.md`)
- [ ] Code with Wispr: dictated prompts, agent instructions and docs; **Insights scorecard screenshot** saved as `docs/wispr-scorecard.png` and added to the submission (`docs/VOICE_LOG.md`)
- [ ] Any Switch bug fixed upstream as a PR to `sandbox-quantum/switch`
- [ ] A second person reproduces the demo from the README (a fresh `git clone` + README setup, tests and offline demo passed on Nov 6 on one machine; still needs a real second person)

# Switch / Mattermost setup (Stage 0)

Rebuild this fresh after the event opens (Tue Nov 3, 10:31 AM PT); it takes about 20 minutes.

1. Start Switch and its bundled Mattermost. Note the Mattermost URL and create an admin personal access token.
2. In the Switch console create the two agents with the instructions in `docs/agents/`:
   - `intake`: nurse-station only
   - `care-coordinator`: nurse-station and doctor-review
   Their Mattermost usernames must match `config/roles.yaml` (or edit that file).
3. Create users and the ten private rooms (four patient rooms, nurse-station, doctor-review and three write-only ward feeds) (membership comes from `config/roles.yaml`):

   ```bash
   MM_URL=http://localhost:8065 MM_ADMIN_TOKEN=<admin token> MM_TEAM=switch .venv/bin/python scripts/setup_mattermost.py
   ```

   Copy the `export ...` line it prints (it contains record-bot's token). If the server has personal access tokens disabled, enable them in System Console > Integrations first.
4. Start the record service and bot:

   ```bash
   .venv/bin/python -m lantern run
   ```

5. Stage 0 checks (all manual, in Mattermost):
   - Post in `patient-101` as patient-101: record-bot forwards it to `nurse-station` mentioning `@intake`.
   - intake replies with a JSON card; record-bot opens a `Case 17` thread and acknowledges the patient.
   - Both agents can reply inside a thread record-bot started.
   - The patient-102 account cannot open `patient-101`. Switch refuses when intake is asked to join it.
   - record-bot's own posts do not trigger an agent reply loop (the service ignores bot posts; check the agents are not set to answer every message).
6. Run `.venv/bin/python scripts/check_intake.py` to post the three casual phrasings from test 1 against the live agent.

7. Lookup tool check: with the bot running, `curl -s "http://127.0.0.1:8099/chart/101/proc-1?agent=care-coordinator"` should return JSON with a `lookup` number, and an unknown agent name should return 403.

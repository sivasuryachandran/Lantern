# Shotlist as actually recorded

One real run of `scripts/ward_scenarios.py` (take 2; take 1 was discarded because a first-login overlay covered the screen). Mattermost was captured with the read-only `ward-viewer` account at 1920x1080, and the dashboard at the same time. Nothing was edited out of the run; the video is the run sped up 1.15x (Video A) or at 1.0x (Video B). Voice is synthetic (Google Chirp 3 HD "Aoede"); no team member's voice.

## What was live and what was not
- Live: the record service (`record-bot`), Mattermost, the dashboard, every refusal, chart change, task close and owner change.
- Humans (patients, Ana, Ben, Dr. Lee, Sam, Rita): played by the scenario script. Captioned throughout.
- Agents (intake, care-coordinator, interpreter, scribe): **stand-in mode (tests)**. The two real OpenCode agents in Switch Console did not receive Mattermost messages at recording time, so they are not in this footage. Captioned throughout.

| Planned scene | Recorded? | Notes |
|---|---|---|
| 1 Concept clip + title | Yes | 10 s AI concept clip, labelled; title card |
| 2 Ward and sidebar | Partly | nine rooms visible in the sidebar throughout |
| 3 [SIVA] Switch Console | **No** | not recorded; no Console footage is claimed |
| 4 Patient 101 message | Yes | |
| 5 Intake flag | Yes | stand-in mode |
| 6 Ana CONFIRM (Wispr dictation) | CONFIRM yes; Wispr **no** | typed by the driver, not dictated |
| 7 Care-coordinator + receipts | Yes | stand-in mode; checks posted by record-bot |
| 8 Refused DECIDE, then Dr. Lee DECIDE v3 to v4 | Yes | |
| 9 Room-service tray task | Yes | nurse DONE refused, Sam DONE accepted |
| 10 Patient 103 Spanish | Yes | translations both ways (no read-aloud audio) |
| 11 Whispered HANDOFF, ACCEPT | Partly | handoff in the nurse-station thread for Cases 17, 18, 19 (not whispered) |
| 12 Proof card | Yes | final dashboard frame with the fictional-data badge |

Jira and Calendar appear only as tracking rows on the dashboard (created through the integration hooks). The Jira workspace URL and the Google account email are not visible in any frame. The "Welcome to Mattermost" card is covered with a plain mask; Mattermost dimming from its first-login tour remains visible.


## Update (final edit)
The Wispr bubbles are an animated re-enactment labelled 'Illustration · typed in this recording'. The agents are stand-ins (captioned). The Switch Console scene is not in the final cut. The refusal of Ana's DECIDE shows as the refused-by-code count and audit on the dashboard; the chat shows no reply message. See `cutlist.md`.

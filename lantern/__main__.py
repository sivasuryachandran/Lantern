"""python -m lantern run | timeline <patient> <role> [--html] | chart <patient> | lookup <patient> <entry> <agent> | clip <patient> <clip.json> | simagents [intake] [care-coordinator]"""
import json
import sys
from pathlib import Path

from . import bot, timeline


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "run"
    if cmd == "run":
        bot.run()
    elif cmd in ("timeline", "chart", "lookup"):
        svc = bot.readonly()            # database only: no chat server needed, safe for an agent to call
        pid = argv[2] if len(argv) > 2 else "101"
        if cmd == "lookup":    # lookup <patient> <entry> <agent> -> JSON incl. the lookup number and citation
            res = svc.lookup(argv[4], pid, argv[3])
            print(json.dumps(res) if res else "NO DATA: unknown entry")
        elif cmd == "chart":
            print(svc.chart_excerpt(pid))
        else:
            role = argv[3] if len(argv) > 3 else "nurse"
            fn = timeline.render_html if "--html" in argv else timeline.render
            print(fn(svc.db, svc, pid, role))
    elif cmd == "simagents":            # scripted stand-ins for intake and care-coordinator; needs MM_URL, MM_TEAM, LANTERN_TEST_PASSWORD
        from . import simagents
        simagents.main(tuple(argv[2:]) or ("intake", "care-coordinator", "interpreter", "scribe"))
    elif cmd == "shiftreport":
        from . import shiftreport
        svc = bot.readonly()
        print((shiftreport.render_html if "--html" in argv else shiftreport.render)(svc))
    elif cmd == "clip":                 # clip.json: {"clip_id": "c1", "segments": [{"t": 12.5, "text": "..."}]}
        _, svc = bot.build()
        data = json.loads(Path(argv[3]).read_text())
        svc.ingest_clip(argv[2], data["clip_id"], data["segments"])
    else:
        raise SystemExit(__doc__)


main(sys.argv)

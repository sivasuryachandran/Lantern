"""Local HTTP endpoint for the record service.

  GET  /chart/<patient>/<entry>?agent=<name>   chart lookup tool: returns the entry and logs a numbered lookup
  GET  /forwarded/<original_post_id>?agent=<name>   returns the Mattermost id of record-bot's forwarded message
  GET  /api/...  /healthz                      read-only backend over the database (see lantern/api.py)
  POST /action                                 Mattermost interactive-button clicks (user_id is verified by Mattermost)

Bound to 127.0.0.1 by default. Set LANTERN_BIND=0.0.0.0 if Mattermost (e.g. in Docker) must reach the button URL,
LANTERN_LOOKUP_KEY to require an `X-Lookup-Key` header on lookups, and LANTERN_API_KEY to require `X-Api-Key` on /api. Without a key, the agent name is
self-declared, so treat the lookup log as evidence of what was fetched on this machine, not as authentication.
"""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import api


def serve(svc, host="127.0.0.1", port=8099):
    lock = threading.Lock()      # the bot loop and HTTP handlers share one SQLite connection

    class H(BaseHTTPRequestHandler):
        def _send(self, code, obj, ctype="application/json"):
            out = obj.encode() if isinstance(obj, str) else json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        def do_GET(self):
            url = urlparse(self.path)
            parts = url.path.strip("/").split("/")
            if parts[0] in ("api", "healthz"):
                api_key = os.environ.get("LANTERN_API_KEY")
                if api_key and self.headers.get("X-Api-Key") != api_key:
                    return self._send(403, {"error": "bad api key"})
                with lock:
                    code, ctype, body = api.route(svc, url.path, parse_qs(url.query))
                return self._send(code, body, ctype)
            key = os.environ.get("LANTERN_LOOKUP_KEY")
            if len(parts) == 2 and parts[0] == "forwarded":
                if key and self.headers.get("X-Lookup-Key") != key:
                    return self._send(403, {"error": "bad lookup key"})
                agent = (parse_qs(url.query).get("agent") or [self.headers.get("X-Agent", "")])[0]
                user = svc.roles.by_name(agent) if svc.roles else None
                if user is None or user.role != "agent":
                    return self._send(403, {"error": "unknown agent"})
                with lock:
                    fwd = svc.forwarded_id(parts[1])
                return self._send(200, {"original_post_id": parts[1], "forwarded_post_id": fwd}) if fwd                     else self._send(404, {"error": "no forwarded message for that post"})
            if len(parts) != 3 or parts[0] != "chart":
                return self._send(404, {"error": "use /chart/<patient>/<entry>?agent=<name>"})
            if key and self.headers.get("X-Lookup-Key") != key:
                return self._send(403, {"error": "bad lookup key"})
            agent = (parse_qs(url.query).get("agent") or [self.headers.get("X-Agent", "")])[0]
            user = svc.roles.by_name(agent) if svc.roles else None
            if user is None or user.role != "agent":
                return self._send(403, {"error": "unknown agent"})
            with lock:
                res = svc.lookup(agent, parts[1], parts[2])
            self._send(200, res) if res else self._send(404, {"error": "NO DATA: unknown entry"})

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            with lock:
                text = svc.handle_action(body.get("user_id", ""), body.get("context", {}))
            self._send(200, {"ephemeral_text": text})

        def log_message(self, *a):
            pass

    server = ThreadingHTTPServer((host, port), H)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, lock

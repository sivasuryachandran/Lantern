"""Chat adapters. The service talks to the Chat protocol; Mattermost is one implementation."""
import json
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class Post:
    id: str
    room: str
    user_id: str
    message: str
    root_id: str = ""
    edited: bool = False


class MattermostChat:
    def __init__(self, url, token, team):
        self.url = url.rstrip("/")
        self.token = token
        self.team = team
        self._channels = {}
        self._rooms = {}

    def _req(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            f"{self.url}/api/v4{path}", data=data, method=method,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Mattermost {method} {path} -> {e.code}: {e.read().decode()[:300]}") from e

    def channel_id(self, room):
        if room not in self._channels:
            ch = self._req("GET", f"/teams/name/{self.team}/channels/name/{room}")
            self._channels[room] = ch["id"]
            self._rooms[ch["id"]] = room
        return self._channels[room]

    def user_id(self, username):
        try:
            return self._req("GET", f"/users/username/{username}")["id"]
        except RuntimeError:
            return None

    def post(self, room, message, root_id="", props=None):
        body = {"channel_id": self.channel_id(room), "message": message}
        if props:
            body["props"] = props
        if root_id:
            body["root_id"] = root_id
        return self._req("POST", "/posts", body)["id"]

    def new_posts(self, room, since_ms):
        """Posts created or updated at/after since_ms, oldest first, plus the next cursor."""
        res = self._req("GET", f"/channels/{self.channel_id(room)}/posts?since={since_ms}")
        posts = sorted(res.get("posts", {}).values(), key=lambda p: p["create_at"])
        out, cursor = [], since_ms
        for p in posts:
            cursor = max(cursor, p.get("update_at", 0) + 1, p["create_at"] + 1)
            out.append(Post(p["id"], room, p["user_id"], p["message"], p.get("root_id", ""),
                            edited=p.get("edit_at", 0) > 0))
        return out, cursor

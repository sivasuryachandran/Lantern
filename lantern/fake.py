"""In-memory chat used by the tests and the offline demo."""
import itertools

from .chat import Post


class FakeChat:
    def __init__(self):
        self.posts = []          # every post, including the bot's: dicts
        self._ids = itertools.count(1)

    def user_id(self, username):
        return f"uid-{username}"

    def _add(self, room, user, message, root_id):
        pid = f"p{next(self._ids)}"
        self.posts.append({"id": pid, "room": room, "user": user, "message": message, "root_id": root_id})
        return pid

    # What record-bot calls
    def post(self, room, message, root_id="", props=None):
        pid = self._add(room, "record-bot", message, root_id)
        self.posts[-1]["props"] = props
        return pid

    # What a person or agent does; returns a Post to feed to Service.handle
    def say(self, user, room, message, root_id="", edited=False):
        pid = self._add(room, user, message, root_id)
        return Post(pid, room, f"uid-{user}", message, root_id, edited)

    def bot_posts(self, room=None):
        return [p for p in self.posts if p["user"] == "record-bot" and (room is None or p["room"] == room)]

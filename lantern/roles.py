from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class User:
    username: str
    user_id: str
    role: str
    display: str
    patient_id: str = ""
    shift: str = ""


class Roles:
    def __init__(self, path, chat):
        cfg = yaml.safe_load(Path(path).read_text())
        self.rooms = cfg["rooms"]
        self.first_case_number = int(cfg.get("first_case_number", 1))
        self._by_id, self._by_name = {}, {}
        for name, spec in cfg["users"].items():
            uid = chat.user_id(name)
            if uid is None:
                raise SystemExit(f"roles.yaml user '{name}' does not exist in the chat server")
            u = User(name, uid, spec["role"], spec.get("display", name),
                     str(spec.get("patient_id", "")), spec.get("shift", ""))
            self._by_id[uid] = u
            self._by_name[name] = u

    def by_id(self, user_id):
        return self._by_id.get(user_id)

    def by_name(self, username):
        return self._by_name.get(username)

    def agents_in_patient_rooms(self):
        """Config check: names of agents/bots-that-aren't-record-bot listed in any patient room."""
        bad = []
        for room, members in self.rooms.items():
            if room.startswith("patient-"):
                bad += [m for m in members if self._by_name[m].role == "agent"]
        return bad

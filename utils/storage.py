"""
utils/storage.py
-----------------
A tiny JSON-file "database". No external DB service required, so the bot
runs anywhere with just a writable disk. Thread/async-safe enough for a
single-process polling bot via a simple in-process lock.

Structure of the JSON file:
{
  "bot_enabled": true,
  "users": {"<user_id>": {"username": "...", "first_name": "...", "joined": "..."}},
  "codes": {"<code>": {"used": false, "used_by": null, "created_by": <admin_id>}},
  "projects": {
      "<user_id>": {
          "<project_name>": {
              "main_file": "bot.py",
              "folder": "path",
              "pid": null,
              "created": "..."
          }
      }
  }
}
"""

import json
import os
import threading
import datetime
import random
import string

from config import DB_FILE

_lock = threading.Lock()

_DEFAULT_DB = {
    "bot_enabled": True,
    "users": {},
    "codes": {},
    "projects": {},
}


def _load():
    if not os.path.exists(DB_FILE):
        _save(_DEFAULT_DB)
        return json.loads(json.dumps(_DEFAULT_DB))
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return json.loads(json.dumps(_DEFAULT_DB))


def _save(data):
    tmp = DB_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, DB_FILE)


def db():
    """Context manager style helper: read-modify-write under lock."""
    return _DBHandle()


class _DBHandle:
    def __enter__(self):
        _lock.acquire()
        self.data = _load()
        return self.data

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            _save(self.data)
        _lock.release()


# ---------- convenience helpers ----------

def register_user(user_id: int, username: str, first_name: str):
    with db() as d:
        uid = str(user_id)
        if uid not in d["users"]:
            d["users"][uid] = {
                "username": username or "",
                "first_name": first_name or "",
                "joined": datetime.datetime.utcnow().isoformat(),
            }


def is_bot_enabled() -> bool:
    with db() as d:
        return d.get("bot_enabled", True)


def set_bot_enabled(value: bool):
    with db() as d:
        d["bot_enabled"] = value


def generate_code(admin_id: int) -> str:
    code = "".join(random.choices(string.digits, k=6))
    with db() as d:
        while code in d["codes"]:
            code = "".join(random.choices(string.digits, k=6))
        d["codes"][code] = {"used": False, "used_by": None, "created_by": admin_id}
    return code


def redeem_code(code: str, user_id: int) -> bool:
    with db() as d:
        entry = d["codes"].get(code)
        if not entry or entry["used"]:
            return False
        entry["used"] = True
        entry["used_by"] = user_id
        return True


def code_stats():
    with db() as d:
        total = len(d["codes"])
        used = sum(1 for c in d["codes"].values() if c["used"])
        return total, used, total - used


def get_user_projects(user_id: int) -> dict:
    with db() as d:
        return d["projects"].get(str(user_id), {})


def project_name_taken(user_id: int, name: str) -> bool:
    return name in get_user_projects(user_id)


def add_project(user_id: int, name: str, folder: str, main_file: str):
    with db() as d:
        uid = str(user_id)
        d["projects"].setdefault(uid, {})
        d["projects"][uid][name] = {
            "main_file": main_file,
            "folder": folder,
            "pid": None,
            "created": datetime.datetime.utcnow().isoformat(),
        }


def update_project_pid(user_id: int, name: str, pid):
    with db() as d:
        uid = str(user_id)
        if uid in d["projects"] and name in d["projects"][uid]:
            d["projects"][uid][name]["pid"] = pid


def delete_project(user_id: int, name: str):
    with db() as d:
        uid = str(user_id)
        if uid in d["projects"] and name in d["projects"][uid]:
            del d["projects"][uid][name]


def all_user_ids():
    with db() as d:
        return [int(u) for u in d["users"].keys()]


def stats_summary():
    with db() as d:
        total_users = len(d["users"])
        total_projects = sum(len(p) for p in d["projects"].values())
        running = 0
        for user_projects in d["projects"].values():
            for proj in user_projects.values():
                if proj.get("pid"):
                    running += 1
        return {
            "total_users": total_users,
            "total_projects": total_projects,
            "running": running,
        }

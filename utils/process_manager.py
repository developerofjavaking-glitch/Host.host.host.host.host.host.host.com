"""
utils/process_manager.py
-------------------------
Starts, tracks and terminates the background subprocesses that run each
user's hosted script. In-memory registry (fast) is mirrored into the JSON
DB (survives a bot restart lookup, though the OS process itself will not
survive a platform redeploy - that's inherent to process-based hosting).
"""

import os
import sys
import subprocess

# {(user_id, project_name): Popen}
_running = {}


def start_script(user_id: int, project_name: str, script_path: str, cwd: str):
    """
    Launches script_path as a detached background subprocess.
    Returns (pid, error) - error is None on success.
    """
    key = (user_id, project_name)
    stop_script(user_id, project_name)  # stop any previous instance first

    log_path = os.path.join(cwd, "output.log")
    try:
        log_file = open(log_path, "a", encoding="utf-8")
    except Exception:
        log_file = subprocess.DEVNULL

    try:
        proc = subprocess.Popen(
            [sys.executable, script_path],
            cwd=cwd,
            stdout=log_file,
            stderr=log_file,
        )
    except Exception as e:
        return None, str(e)

    _running[key] = proc
    return proc.pid, None


def stop_script(user_id: int, project_name: str) -> bool:
    key = (user_id, project_name)
    proc = _running.pop(key, None)
    if proc is None:
        return False
    try:
        proc.terminate()
    except Exception:
        pass
    return True


def is_running(user_id: int, project_name: str) -> bool:
    key = (user_id, project_name)
    proc = _running.get(key)
    if proc is None:
        return False
    return proc.poll() is None

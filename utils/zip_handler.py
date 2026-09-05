"""
utils/zip_handler.py
---------------------
Safe zip extraction (guards against path traversal / zip-slip) and optional
automatic `pip install -r requirements.txt` for the extracted project.
"""

import os
import zipfile
import subprocess
import sys


def safe_extract(zip_path: str, dest_dir: str):
    """
    Extracts zip_path into dest_dir, refusing any entry that would escape
    dest_dir (zip-slip protection). Returns (ok, message).
    """
    os.makedirs(dest_dir, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.namelist():
                member_path = os.path.join(dest_dir, member)
                abs_dest = os.path.abspath(dest_dir)
                abs_member = os.path.abspath(member_path)
                if not abs_member.startswith(abs_dest + os.sep) and abs_member != abs_dest:
                    return False, f"❌ Blocked unsafe path in zip: {member}"
            zf.extractall(dest_dir)
    except zipfile.BadZipFile:
        return False, "❌ That file is not a valid ZIP archive."
    except Exception as e:
        return False, f"❌ Error extracting zip: {e}"
    return True, "ok"


def install_requirements_if_present(project_dir: str, timeout: int = 180):
    """
    Looks for requirements.txt anywhere at the top level of project_dir and
    pip-installs it. Returns (ran: bool, ok: bool, output: str).
    """
    req_path = None
    for root, _dirs, files in os.walk(project_dir):
        if "requirements.txt" in files:
            req_path = os.path.join(root, "requirements.txt")
            break

    if not req_path:
        return False, True, ""

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", req_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        ok = result.returncode == 0
        output = (result.stdout or "") + (result.stderr or "")
        return True, ok, output[-2000:]
    except subprocess.TimeoutExpired:
        return True, False, "pip install timed out."
    except Exception as e:
        return True, False, str(e)


def find_file(project_dir: str, filename: str):
    """Search project_dir recursively for filename, return absolute path or None."""
    for root, _dirs, files in os.walk(project_dir):
        if filename in files:
            return os.path.join(root, filename)
    return None

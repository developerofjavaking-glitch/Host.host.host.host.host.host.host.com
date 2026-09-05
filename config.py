"""
config.py
---------
Every deployment-specific value is read from environment variables so the
exact same code runs on Render, Railway, Pella, Replit, a VPS, or your own
laptop. Nothing here is hard-coded.

See .env.example / README.md for the full list of variables.
"""

import os

def _get_int_list(raw: str):
    ids = []
    if not raw:
        return ids
    for part in raw.replace(" ", "").split(","):
        if part:
            try:
                ids.append(int(part))
            except ValueError:
                pass
    return ids


# ---- Required ----
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ---- Admin / Owner ----
# ADMIN_IDS: comma separated Telegram numeric user IDs allowed to use /admin
ADMIN_IDS = _get_int_list(os.getenv("ADMIN_ID", os.getenv("ADMIN_IDS", "")))

# OWNER_LINK: full t.me link (or any URL) used by the "Contact Owner" button
OWNER_LINK = os.getenv("OWNER_LINK", "https://t.me/")

# CHANNEL_LINK: full t.me link used by the "Updates Channel" button
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/")

# ---- Branding ----
BOT_NAME = os.getenv("BOT_NAME", "Boom Host Bot")

# ---- Behaviour / limits ----
MAX_FILES_PER_USER = int(os.getenv("MAX_FILES_PER_USER", "10"))
MAX_UPLOAD_MB = float(os.getenv("MAX_UPLOAD_MB", "20"))
REQUIRE_CODE = os.getenv("REQUIRE_CODE", "true").lower() in ("1", "true", "yes")

# ---- Storage paths ----
# On Render the persistent disk (if attached) should be mounted at DATA_DIR.
# Without a persistent disk, data resets on every redeploy/restart - that is
# a platform limitation, not a bot limitation. See README "Persistence" section.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(DATA_DIR, "upload_bots"))
DB_FILE = os.path.join(DATA_DIR, "database.json")

# ---- Web keep-alive (only needed if the platform requires a bound PORT,
# e.g. Render "Web Service" instead of "Background Worker") ----
ENABLE_KEEPALIVE = os.getenv("ENABLE_KEEPALIVE", "true").lower() in ("1", "true", "yes")
PORT = int(os.getenv("PORT", "8080"))

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

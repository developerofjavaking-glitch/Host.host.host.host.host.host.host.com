# Boom Host Bot 🤖

A Telegram bot that lets your users upload and run their own Python (`.py`),
JavaScript (`.js`), or zipped project (`.zip`), directly from Telegram —
similar to a mini Heroku/Render, but inside a chat.

Every deployment-specific value (bot token, admin ID, owner link, channel
link, etc.) is read from **environment variables**. Nothing is hard-coded,
so the same code runs unmodified on Render, Railway, Pella, Replit, Fly.io,
a VPS, or your own laptop.

---

## ✨ Features

- **/start dashboard** — shows the user's ID, username, tier, and how many
  projects they've hosted.
- **Upload File** — accepts `.py`, `.js`, or `.zip`. Zips are safely
  extracted (zip-slip protected) and `requirements.txt` is auto-installed.
- **Syntax pre-check** — `.py` files are `compile()`-checked before they're
  launched, so users get a clear error (file, line, message) instead of a
  silently dead process.
- **Check Files** — list projects, see 🟢 running / 🔴 stopped, stop or
  delete a project.
- **Bot Speed** / **Statistics** — quick health and usage info.
- **One-time hosting codes** (optional) — gate project creation behind
  admin-issued 6-digit codes, one code = one project. Turn off with
  `REQUIRE_CODE=false` if you want open access instead.
- **/admin panel** — generate codes, see code/usage stats, toggle the whole
  bot on/off, and broadcast a message/photo/document to every user.
- **No external database** — a small JSON file is used for storage, so
  there's nothing extra to provision.

---

## 📁 Project structure

```
boom-host-bot/
├── bot.py                 # entry point
├── config.py               # reads all environment variables
├── keep_alive.py            # optional HTTP ping server (for web-service style hosts)
├── handlers/
│   ├── start.py             # /start dashboard
│   ├── buttons.py           # Check Files / Speed / Statistics / project actions
│   ├── upload.py            # code → project name → file upload → launch
│   └── admin.py              # /admin panel, codes, broadcast, toggle
├── utils/
│   ├── storage.py            # JSON-file "database"
│   ├── syntax_check.py       # compile() pre-check for .py uploads
│   ├── zip_handler.py        # safe zip extraction + pip install
│   └── process_manager.py    # start/stop hosted subprocesses
├── requirements.txt
├── runtime.txt
├── Procfile
├── render.yaml
├── .env.example
└── README.md
```

---

## 🔧 Environment variables

| Variable              | Required | Default            | Description |
|------------------------|:--------:|---------------------|-------------|
| `BOT_TOKEN`            | ✅       | —                   | Token from [@BotFather](https://t.me/BotFather) |
| `ADMIN_ID`              | ✅ for /admin | —              | Comma-separated numeric Telegram user IDs, e.g. `7453801393,111222333` |
| `OWNER_LINK`            |          | `https://t.me/`     | Used by the "📞 Contact Owner" button |
| `CHANNEL_LINK`          |          | `https://t.me/`     | Used by the "📢 Updates Channel" button |
| `BOT_NAME`              |          | `Boom Host Bot`     | Display name used in messages |
| `REQUIRE_CODE`          |          | `true`              | If `true`, users need an admin-issued code before hosting a project |
| `MAX_FILES_PER_USER`    |          | `10`                | Max concurrent projects per user |
| `MAX_UPLOAD_MB`         |          | `20`                | Max upload size in MB |
| `DATA_DIR`              |          | `./data`            | Where the JSON database + uploaded projects live |
| `ENABLE_KEEPALIVE`      |          | `true`              | Runs a tiny HTTP server on `PORT` (needed by some "web service" style hosts) |
| `PORT`                  |          | `8080`              | Port for the keep-alive server |

Copy `.env.example` for reference — most platforms let you paste these into
a dashboard instead of using a `.env` file.

---

## 🚀 Setup (get your token & admin ID first)

1. Message [@BotFather](https://t.me/BotFather) → `/newbot` → follow the
   prompts → copy the token it gives you. That's your `BOT_TOKEN`.
2. Message [@userinfobot](https://t.me/userinfobot) (or similar) to get
   your own numeric Telegram user ID. That's your `ADMIN_ID`.
3. (Optional) Create an updates channel and get its `https://t.me/...` link
   for `CHANNEL_LINK`.
4. Decide your `OWNER_LINK` — usually `https://t.me/your_username`.

---

## ▶️ Run locally

```bash
git clone <your-repo-url>
cd boom-host-bot
pip install -r requirements.txt

export BOT_TOKEN="123456:ABC..."
export ADMIN_ID="7453801393"
export OWNER_LINK="https://t.me/King_Boom_69"
export CHANNEL_LINK="https://t.me/your_channel"
export ENABLE_KEEPALIVE=false     # not needed on your own machine

python bot.py
```

---

## ☁️ Deploy on Render

1. Push this project to a GitHub repo.
2. Render dashboard → **New → Background Worker** (preferred — no port
   needed) or **Web Service** if you want a URL/health check.
3. Build command: `pip install -r requirements.txt`
   Start command: `python bot.py`
4. Add the environment variables from the table above in **Environment**.
   - If you used **Web Service**, leave `ENABLE_KEEPALIVE=true` (default).
   - If you used **Background Worker**, set `ENABLE_KEEPALIVE=false`.
5. (Optional) Attach a **Persistent Disk** mounted at e.g. `/data` and set
   `DATA_DIR=/data` — otherwise uploaded projects and the database reset on
   every redeploy, since Render's local filesystem is ephemeral.
6. Deploy. `render.yaml` in this repo can also be used for a one-click
   Blueprint deploy.

---

## ☁️ Deploy on Pella

1. Create a new Python project on Pella and upload/push this repo.
2. Set the start command to `python bot.py`.
3. Add the same environment variables in Pella's environment/secrets tab.
4. If Pella requires a bound port for your process to stay alive, keep
   `ENABLE_KEEPALIVE=true` (default); otherwise you may set it to `false`.
5. Check whether your Pella plan gives persistent storage; if not, treat
   `DATA_DIR` as ephemeral the same as Render's free tier.

---

## ☁️ Deploy anywhere else (Railway, Replit, Fly.io, a VPS, Docker...)

Because everything is environment-variable driven and there's no external
database, this runs the same way anywhere that can:

- run Python 3.10+,
- set environment variables,
- keep a long-running process alive (`python bot.py`).

General recipe:

```bash
pip install -r requirements.txt
BOT_TOKEN=... ADMIN_ID=... OWNER_LINK=... CHANNEL_LINK=... python bot.py
```

For a simple **systemd** service on a VPS, or a **Docker** container, just
wrap the same start command — no code changes needed.

### Node.js note for `.js` hosting

Running user-uploaded `.js` files requires `node` to be available on the
host's `$PATH`. Render/Railway images usually don't include Node by default
in a Python environment — if you need JS hosting, either pick a platform/
image with both runtimes, or install Node via the platform's build step.

---

## 💾 Persistence

This bot stores its state (users, codes, project records) in a single JSON
file at `DATA_DIR/database.json`, and hosted projects' files under
`DATA_DIR/upload_bots/<user_id>/<project_name>/`. On platforms with an
**ephemeral filesystem** (most free tiers), this data is wiped on every
redeploy or restart. To persist it, attach a persistent volume/disk and
point `DATA_DIR` at it.

---

## 🔐 Notes on running user-uploaded code

This bot executes files that users upload, which is inherently powerful —
treat it the way you'd treat any code-hosting platform:

- Only give `ADMIN_ID` to people you trust with the `/admin` broadcast and
  maintenance-toggle powers.
- Keep `REQUIRE_CODE=true` in production so hosting isn't fully open to
  anyone who finds the bot.
- Consider running the bot itself inside a container/sandboxed VM, since
  hosted scripts run with the same OS-level permissions as the bot process.

---

## 🩹 Troubleshooting

**Deploy crashes immediately with `RuntimeError: There is no current event
loop in thread 'MainThread'` and `coroutine 'Updater.start_polling' was
never awaited`:**
This happens when the host runs the bot on Python 3.13/3.14, where
`asyncio.get_event_loop()` no longer auto-creates a loop the way older
`python-telegram-bot` versions expect. This project already pins
`python-telegram-bot==22.8` (which fixes this natively) and `bot.py` also
sets up a loop defensively before starting. If you still hit this:
- Make sure the platform actually installed from `requirements.txt` (check
  the build log for `Successfully installed python-telegram-bot-22.8`).
- If your platform ignores `runtime.txt`, set a `PYTHON_VERSION` environment
  variable (Render, Railway, etc. often read this) to `3.11.9` or `3.12.x`
  as a fallback, though it should no longer be necessary with PTB 22.8.

---

## 🛠 Admin commands

- `/admin` — opens the admin panel (Generate Code, Code Stats, Toggle
  Bot On/Off, Broadcast).
- `/cancel` — cancel whatever multi-step flow you're currently in
  (works for both regular users and admins).

---

## License

Use and modify freely for your own hosting bot.

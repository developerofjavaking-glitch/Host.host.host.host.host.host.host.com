import os
import shutil

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import config
from utils import storage, process_manager
from utils.syntax_check import check_python_syntax
from utils.zip_handler import safe_extract, install_requirements_if_present, find_file

ALLOWED_EXT = (".py", ".js", ".zip")


def _user_dir(user_id: int) -> str:
    d = os.path.join(config.UPLOAD_DIR, str(user_id))
    os.makedirs(d, exist_ok=True)
    return d


async def upload_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered by the 'Upload File' menu button."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if not storage.is_bot_enabled() and user_id not in config.ADMIN_IDS:
        await query.message.reply_text("🚧 The bot is currently under maintenance.")
        return

    projects = storage.get_user_projects(user_id)
    if len(projects) >= config.MAX_FILES_PER_USER:
        await query.message.reply_text(
            f"⚠️ You've reached your limit of {config.MAX_FILES_PER_USER} hosted projects. "
            "Delete one from *Check Files* before adding another.",
            parse_mode="Markdown",
        )
        return

    context.user_data.clear()

    if config.REQUIRE_CODE:
        context.user_data["state"] = "await_code"
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("📞 Get a code from Owner", url=config.OWNER_LINK)]]
        )
        await query.message.reply_text(
            "🔑 **Enter your one-time hosting code:**\n"
            "(Ask the owner/admin for a code if you don't have one.)",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    else:
        context.user_data["state"] = "await_project_name"
        await query.message.reply_text(
            "📝 **Choose a name for this project** (letters/numbers/underscore only):",
            parse_mode="Markdown",
        )


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the plain-text steps of the flow: code, project name, main file name."""
    state = context.user_data.get("state")
    if not state:
        return  # not in a flow - ignore, let other handlers/no-op

    user_id = update.effective_user.id
    text = (update.message.text or "").strip()

    if state == "await_code":
        if storage.redeem_code(text, user_id):
            context.user_data["state"] = "await_project_name"
            await update.message.reply_text(
                "✅ **Code accepted!**\n📝 Now choose a name for this project "
                "(letters/numbers/underscore only):",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                "❌ Invalid or already-used code. Please try again, or /start to cancel."
            )
        return

    if state == "await_project_name":
        name = "".join(ch for ch in text if ch.isalnum() or ch == "_")
        if not name:
            await update.message.reply_text("❌ Invalid name. Use letters, numbers or underscore only.")
            return
        if storage.project_name_taken(user_id, name):
            await update.message.reply_text("❌ You already have a project with that name. Choose another:")
            return
        context.user_data["project_name"] = name
        context.user_data["state"] = "await_upload"
        await update.message.reply_text(
            f"📥 **Project `{name}` reserved.**\nNow send your `.py`, `.js`, or `.zip` file.",
            parse_mode="Markdown",
        )
        return

    if state == "await_main_file":
        project_dir = context.user_data.get("project_dir")
        filename = text.strip()
        path = find_file(project_dir, filename) if project_dir else None
        if not path:
            await update.message.reply_text(
                f"❌ Couldn't find `{filename}` in your uploaded project. Check the exact filename and try again:",
                parse_mode="Markdown",
            )
            return
        await _launch_and_save(update, context, path, filename, project_dir)
        return


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    if state != "await_upload":
        return  # ignore unsolicited files

    user_id = update.effective_user.id
    document = update.message.document
    file_name = document.file_name or "file"

    if not file_name.lower().endswith(ALLOWED_EXT):
        await update.message.reply_text("❌ Unsupported format. Please send `.py`, `.js`, or `.zip`.")
        return

    size_mb = (document.file_size or 0) / (1024 * 1024)
    if size_mb > config.MAX_UPLOAD_MB:
        await update.message.reply_text(
            f"❌ File is {size_mb:.1f} MB, which exceeds the {config.MAX_UPLOAD_MB} MB limit."
        )
        return

    project_name = context.user_data.get("project_name")
    if not project_name:
        await update.message.reply_text("⚠️ Session expired. Please tap *Upload File* again.", parse_mode="Markdown")
        context.user_data.clear()
        return

    project_dir = os.path.join(_user_dir(user_id), project_name)
    os.makedirs(project_dir, exist_ok=True)

    tg_file = await context.bot.get_file(document.file_id)
    local_path = os.path.join(project_dir, file_name)
    await tg_file.download_to_drive(local_path)

    await update.message.reply_text(f"✅ **Downloaded `{file_name}`. Processing...**", parse_mode="Markdown")

    if file_name.lower().endswith(".zip"):
        ok, msg = safe_extract(local_path, project_dir)
        os.remove(local_path)
        if not ok:
            await update.message.reply_text(msg)
            shutil.rmtree(project_dir, ignore_errors=True)
            context.user_data.clear()
            return

        ran, install_ok, output = install_requirements_if_present(project_dir)
        if ran:
            note = "✅ `requirements.txt` installed." if install_ok else f"⚠️ Dependency install had issues:\n```\n{output[-500:]}\n```"
            await update.message.reply_text(note, parse_mode="Markdown")

        context.user_data["project_dir"] = project_dir
        context.user_data["state"] = "await_main_file"
        await update.message.reply_text(
            "📄 **Which file should I run?** (e.g. `bot.py` or `index.js`)",
            parse_mode="Markdown",
        )
        return

    # single .py or .js file - it IS the entry point
    await _launch_and_save(update, context, local_path, file_name, project_dir)


async def _launch_and_save(update, context, entry_path: str, entry_name: str, project_dir: str):
    user_id = update.effective_user.id
    project_name = context.user_data.get("project_name")

    if entry_name.lower().endswith(".py"):
        ok, err = check_python_syntax(entry_path)
        if not ok:
            await update.message.reply_text(
                f"❌ **Error in script pre-check for `{entry_name}`:**\n```text\n{err}\n```",
                parse_mode="Markdown",
            )
            shutil.rmtree(project_dir, ignore_errors=True)
            context.user_data.clear()
            return
        pid, launch_err = process_manager.start_script(user_id, project_name, entry_path, project_dir)
    elif entry_name.lower().endswith(".js"):
        pid, launch_err = process_manager.start_script(user_id, project_name, entry_path, project_dir)
        # process_manager always uses sys.executable(python); override for JS:
        if launch_err is None:
            process_manager.stop_script(user_id, project_name)
            import shutil as _sh
            node_bin = _sh.which("node")
            if not node_bin:
                await update.message.reply_text(
                    "⚠️ `node` was not found on this host, so the JS file was saved but not started. "
                    "Make sure the platform's buildpack/image includes Node.js."
                )
                pid = None
            else:
                import subprocess
                proc = subprocess.Popen([node_bin, entry_path], cwd=project_dir)
                process_manager._running[(user_id, project_name)] = proc
                pid = proc.pid
    else:
        pid, launch_err = None, "Unsupported entry file type."

    storage.add_project(user_id, project_name, project_dir, entry_name)
    if pid:
        storage.update_project_pid(user_id, project_name, pid)
        await update.message.reply_text(
            f"✅ **`{entry_name}` started!**\n🆔 **PID:** `{pid}`\n📦 **Project:** `{project_name}`",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            f"⚠️ Project `{project_name}` saved, but it did not start automatically"
            + (f": {launch_err}" if launch_err else "."),
            parse_mode="Markdown",
        )

    context.user_data.clear()

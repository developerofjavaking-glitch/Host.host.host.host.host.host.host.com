import shutil
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from utils import storage, process_manager
from handlers.start import START_TIME, main_menu_keyboard


def _projects_keyboard(user_id: int):
    projects = storage.get_user_projects(user_id)
    rows = []
    for name in projects:
        running = process_manager.is_running(user_id, name)
        dot = "🟢" if running else "🔴"
        rows.append([InlineKeyboardButton(f"{dot} {name}", callback_data=f"proj_{name}")])
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="menu_back")])
    return InlineKeyboardMarkup(rows)


def _project_detail_keyboard(name: str):
    rows = [
        [
            InlineKeyboardButton("⏹ Stop/Restart", callback_data=f"stop_{name}"),
            InlineKeyboardButton("🗑 Delete", callback_data=f"delete_{name}"),
        ],
        [InlineKeyboardButton("⬅️ Back to Files", callback_data="menu_check_files")],
    ]
    return InlineKeyboardMarkup(rows)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "menu_back":
        from handlers.start import dashboard_text
        await query.message.edit_text(
            dashboard_text(query.from_user), parse_mode="Markdown", reply_markup=main_menu_keyboard()
        )
        return

    if data == "menu_check_files":
        projects = storage.get_user_projects(user_id)
        if not projects:
            await query.message.edit_text(
                "📁 **You have no hosted projects yet.**\nUse *Upload File* from /start to host one.",
                parse_mode="Markdown",
                reply_markup=_projects_keyboard(user_id),
            )
            return
        await query.message.edit_text(
            "📁 **Your hosted projects:**\n🟢 running   🔴 stopped",
            parse_mode="Markdown",
            reply_markup=_projects_keyboard(user_id),
        )
        return

    if data.startswith("proj_"):
        name = data[len("proj_"):]
        projects = storage.get_user_projects(user_id)
        info = projects.get(name)
        if not info:
            await query.message.edit_text("⚠️ That project no longer exists.")
            return
        running = process_manager.is_running(user_id, name)
        status = "🟢 Running" if running else "🔴 Stopped"
        text = (
            f"📦 **Project:** `{name}`\n"
            f"🚀 **Main file:** `{info['main_file']}`\n"
            f"📶 **Status:** {status}\n"
            f"🕒 **Created:** {info['created']}"
        )
        await query.message.edit_text(
            text, parse_mode="Markdown", reply_markup=_project_detail_keyboard(name)
        )
        return

    if data.startswith("stop_"):
        name = data[len("stop_"):]
        stopped = process_manager.stop_script(user_id, name)
        storage.update_project_pid(user_id, name, None)
        msg = f"⏹ **`{name}` stopped.**" if stopped else f"ℹ️ `{name}` was not running."
        await query.message.edit_text(msg, parse_mode="Markdown", reply_markup=_projects_keyboard(user_id))
        return

    if data.startswith("delete_"):
        name = data[len("delete_"):]
        projects = storage.get_user_projects(user_id)
        info = projects.get(name)
        process_manager.stop_script(user_id, name)
        if info and info.get("folder"):
            shutil.rmtree(info["folder"], ignore_errors=True)
        storage.delete_project(user_id, name)
        await query.message.edit_text(
            f"🗑 **Project `{name}` deleted.**", parse_mode="Markdown", reply_markup=_projects_keyboard(user_id)
        )
        return

    if data == "menu_speed":
        started = time.monotonic()
        ping_ms = round((time.monotonic() - started) * 1000, 1)
        uptime = int(time.time() - START_TIME)
        h, rem = divmod(uptime, 3600)
        m, s = divmod(rem, 60)
        await query.message.reply_text(
            "⚡ **Bot Speed & Status:**\n\n"
            f"⏱ **Response Time:** {ping_ms} ms\n"
            f"🟢 **Bot Status:** Online\n"
            f"⏳ **Uptime:** {h}h {m}m {s}s",
            parse_mode="Markdown",
        )
        return

    if data == "menu_stats":
        summary = storage.stats_summary()
        await query.message.reply_text(
            "📊 **Server Statistics:**\n\n"
            f"👤 **Total Users:** {summary['total_users']}\n"
            f"📦 **Total Projects:** {summary['total_projects']}\n"
            f"🟢 **Currently Running:** {summary['running']}",
            parse_mode="Markdown",
        )
        return

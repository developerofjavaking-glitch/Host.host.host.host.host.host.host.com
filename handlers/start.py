import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import config
from utils import storage

START_TIME = time.time()


def main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📥 Upload File", callback_data="menu_upload"),
            InlineKeyboardButton("📁 Check Files", callback_data="menu_check_files"),
        ],
        [
            InlineKeyboardButton("⚡ Bot Speed", callback_data="menu_speed"),
            InlineKeyboardButton("📊 Statistics", callback_data="menu_stats"),
        ],
        [InlineKeyboardButton("📞 Contact Owner", url=config.OWNER_LINK)],
        [InlineKeyboardButton("📢 Updates Channel", url=config.CHANNEL_LINK)],
    ]
    return InlineKeyboardMarkup(keyboard)


def dashboard_text(user) -> str:
    projects = storage.get_user_projects(user.id)
    return (
        f"〽️ **Welcome to {config.BOT_NAME}, {user.first_name}!**\n\n"
        f"🆔 **Your User ID:** `{user.id}`\n"
        f"❇️ **Username:** @{user.username if user.username else 'N/A'}\n"
        f"🔰 **Status:** `FREE` Free User\n"
        f"📂 **Projects Hosted:** {len(projects)} / {config.MAX_FILES_PER_USER}\n\n"
        f"🤖 Host & run Python (`.py`) or JS (`.js`) scripts, or a full `.zip` project.\n"
        f"👇 Use the buttons below or type /start anytime."
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data.clear()  # reset any half-finished flow

    storage.register_user(user.id, user.username, user.first_name)

    if not storage.is_bot_enabled() and user.id not in config.ADMIN_IDS:
        await update.message.reply_text(
            "🚧 The bot is currently under maintenance. Please check back soon."
        )
        return

    text = dashboard_text(user)
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())
    elif update.callback_query:
        await update.callback_query.message.reply_text(
            text, parse_mode="Markdown", reply_markup=main_menu_keyboard()
        )

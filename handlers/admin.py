from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import config
from utils import storage


def _is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


def _admin_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔑 Generate Code", callback_data="admin_gencode"),
                InlineKeyboardButton("📊 Code Stats", callback_data="admin_codestats"),
            ],
            [InlineKeyboardButton("🔌 Toggle Bot On/Off", callback_data="admin_toggle")],
            [InlineKeyboardButton("📣 Broadcast", callback_data="admin_broadcast")],
        ]
    )


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not _is_admin(user_id):
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        return
    await update.message.reply_text(
        "🛠 **Admin Panel**", parse_mode="Markdown", reply_markup=_admin_keyboard()
    )


async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if not _is_admin(user_id):
        await query.answer("⛔ Not authorized.", show_alert=True)
        return
    await query.answer()
    data = query.data

    if data == "admin_gencode":
        code = storage.generate_code(user_id)
        await query.message.reply_text(f"🔑 **New hosting code:**\n`{code}`", parse_mode="Markdown")
        return

    if data == "admin_codestats":
        total, used, unused = storage.code_stats()
        summary = storage.stats_summary()
        await query.message.reply_text(
            "📊 **Admin Statistics**\n\n"
            f"🔑 Codes — total: {total}, used: {used}, live: {unused}\n"
            f"👤 Users: {summary['total_users']}\n"
            f"📦 Projects: {summary['total_projects']}\n"
            f"🟢 Running: {summary['running']}",
            parse_mode="Markdown",
        )
        return

    if data == "admin_toggle":
        current = storage.is_bot_enabled()
        storage.set_bot_enabled(not current)
        state_text = "🟢 ENABLED" if not current else "🔴 DISABLED"
        await query.message.reply_text(f"🔌 Bot is now {state_text} for regular users.")
        return

    if data == "admin_broadcast":
        context.user_data["state"] = "await_broadcast"
        await query.message.reply_text(
            "📣 Send the message (text, photo, or document) you want to broadcast to all users, "
            "or /cancel to abort."
        )
        return


async def broadcast_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the actual content once an admin is in the 'await_broadcast' state."""
    user_id = update.effective_user.id
    if context.user_data.get("state") != "await_broadcast" or not _is_admin(user_id):
        return

    context.user_data.clear()
    targets = storage.all_user_ids()
    sent, failed = 0, 0

    for uid in targets:
        try:
            await update.message.copy(chat_id=uid)
            sent += 1
        except Exception:
            failed += 1

    await update.message.reply_text(f"📣 Broadcast complete. ✅ Sent: {sent}  ❌ Failed: {failed}")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❎ Cancelled.")

"""
bot.py — entry point.

Run with:  python bot.py
All configuration comes from environment variables (see config.py / README.md).
"""

import asyncio
import logging
import sys

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

import config
import keep_alive
from handlers.start import start
from handlers.buttons import button_handler
from handlers.upload import upload_entry, text_router, handle_document
from handlers.admin import admin_panel, admin_button_handler, broadcast_router, cancel

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def route_text(update, context):
    """A user can be mid-broadcast (admin) or mid-hosting-flow (any user)."""
    if context.user_data.get("state") == "await_broadcast":
        await broadcast_router(update, context)
        return
    await text_router(update, context)


async def route_document(update, context):
    """A document can be an admin's broadcast attachment or a hosting-flow upload."""
    if context.user_data.get("state") == "await_broadcast":
        await broadcast_router(update, context)
        return
    await handle_document(update, context)


def main():
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN is not set. Add it as an environment variable and restart.")
        sys.exit(1)

    if not config.ADMIN_IDS:
        logger.warning("ADMIN_ID is not set — /admin will be unusable until you set it.")

    keep_alive.start()

    # Belt-and-suspenders fix for platforms whose default Python (3.13+/3.14+)
    # no longer auto-creates an event loop in the main thread. python-telegram-bot
    # >=22.3 already handles this internally, but explicitly setting a loop here
    # keeps bot.py working even on older/newer PTB versions or odd host setups.
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())

    app = Application.builder().token(config.BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("cancel", cancel))

    # Menu callback buttons
    app.add_handler(CallbackQueryHandler(upload_entry, pattern="^menu_upload$"))
    app.add_handler(
        CallbackQueryHandler(
            button_handler,
            pattern="^(menu_check_files|menu_back|menu_speed|menu_stats|proj_.*|stop_.*|delete_.*)$",
        )
    )
    app.add_handler(CallbackQueryHandler(admin_button_handler, pattern="^admin_.*$"))

    # Multi-step text flow (code / project name / main file / broadcast text)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_text))

    # File uploads
    app.add_handler(MessageHandler(filters.Document.ALL, route_document))

    # Broadcast can also forward a photo/document — catch those too
    app.add_handler(MessageHandler((filters.PHOTO | filters.VIDEO) & ~filters.COMMAND, broadcast_router))

    logger.info("%s starting (polling)...", config.BOT_NAME)
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()

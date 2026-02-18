"""Сборка и запуск приложения бота."""
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from app_config import get_bot_token, get_telegram_proxy
from .handlers import start, command_brands, handle_callback, handle_message
from .services import run_periodic_ads


def main() -> None:
    token = get_bot_token()
    builder = (
        Application.builder()
        .token(token)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .pool_timeout(15.0)
    )
    proxy = get_telegram_proxy()
    if proxy:
        builder = builder.proxy(proxy)
    app = builder.build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("brands", command_brands))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        scheduler.add_job(run_periodic_ads, "interval", minutes=15, id="avito_ads")
        scheduler.start()
    except ImportError:
        pass

    app.run_polling()

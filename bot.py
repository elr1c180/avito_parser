import os
import re
import django
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from asgiref.sync import sync_to_async
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

from core.models import TelegramUser, Brand

PENDING_PASSWORD = {}
USER_STATE = {}


def get_user_by_chat_or_username(chat_id: int, username: str | None) -> TelegramUser | None:
    q = TelegramUser.objects.filter(chat_id=chat_id)
    if q.exists():
        return q.first()
    if username:
        q = TelegramUser.objects.filter(username=username)
        if q.exists():
            return q.first()
    return None


def get_user_by_password(password: str) -> TelegramUser | None:
    q = TelegramUser.objects.filter(password=password)
    return q.first() if q.exists() else None


def get_brands_keyboard(selected_ids: set) -> InlineKeyboardMarkup:
    brands = Brand.objects.all().order_by("name")
    buttons = []
    row = []
    for b in brands:
        prefix = "✓ " if b.id in selected_ids else ""
        row.append(InlineKeyboardButton(f"{prefix}{b.name}", callback_data=f"brand_{b.id}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("Готово", callback_data="brands_done")])
    return InlineKeyboardMarkup(buttons)


async def ask_brands(update: Update, context: ContextTypes.DEFAULT_TYPE, user: TelegramUser):
    chat_id = update.effective_chat.id
    USER_STATE[chat_id] = {"state": "brands", "selected": set()}
    msg = "Выберите марки автомобилей:"
    keyboard = await sync_to_async(get_brands_keyboard)(set())
    await context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    username = update.effective_user.username if update.effective_user else None

    if chat_id in PENDING_PASSWORD:
        del PENDING_PASSWORD[chat_id]

    user = await sync_to_async(get_user_by_chat_or_username)(chat_id, username)
    if user:
        if not user.chat_id or user.chat_id != chat_id:
            user.chat_id = chat_id
        if username and user.username != username:
            user.username = username
        await sync_to_async(user.save)()
        await update.message.reply_text("Привет! Я бот для подбора автомобилей с Авито.")
        await ask_brands(update, context, user)
    else:
        PENDING_PASSWORD[chat_id] = username
        await update.message.reply_text(
            "Привет! Я бот для подбора автомобилей с Авито.\nВведите пароль для входа:"
        )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    data = query.data

    if data == "brands_done":
        state = USER_STATE.get(chat_id, {})
        if state.get("state") != "brands":
            return
        user = await sync_to_async(get_user_by_chat_or_username)(
            chat_id, update.effective_user.username if update.effective_user else None
        )
        if not user:
            return
        selected = state.get("selected", set())
        await sync_to_async(user.selected_brands.set)(list(selected))
        del USER_STATE[chat_id]
        await query.edit_message_text("Введите максимальный порог цены (руб):")
        USER_STATE[chat_id] = {"state": "price", "user": user}
        return

    if data.startswith("brand_"):
        bid = int(data.split("_")[1])
        state = USER_STATE.get(chat_id, {})
        if state.get("state") != "brands":
            return
        selected = state.get("selected", set())
        if bid in selected:
            selected.discard(bid)
        else:
            selected.add(bid)
        state["selected"] = selected
        keyboard = await sync_to_async(get_brands_keyboard)(selected)
        await query.edit_message_reply_markup(reply_markup=keyboard)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    username = update.effective_user.username if update.effective_user else None
    text = update.message.text.strip() if update.message.text else ""

    if chat_id in PENDING_PASSWORD:
        user = await sync_to_async(get_user_by_password)(text)
        if user:
            user.chat_id = chat_id
            user.username = username or user.username
            await sync_to_async(user.save)()
            del PENDING_PASSWORD[chat_id]
            await update.message.reply_text("Вход выполнен.")
            await ask_brands(update, context, user)
        else:
            await update.message.reply_text("Неверный пароль. Попробуйте снова:")
        return

    state = USER_STATE.get(chat_id, {})
    if state.get("state") == "price":
        match = re.search(r"[\d\s]+", text)
        if match:
            num_str = re.sub(r"\s", "", match.group())
            if num_str:
                price = int(num_str)
                if price > 0:
                    state["user"].max_price = price
                    await sync_to_async(state["user"].save)()
                    del USER_STATE[chat_id]
                    await update.message.reply_text(f"Порог цены сохранён: {price} ₽\n\nНачинаем подбор объявлений")
                    return
        await update.message.reply_text("Введите число (например: 500000):")
        return

    user = await sync_to_async(get_user_by_chat_or_username)(chat_id, username)
    if not user:
        PENDING_PASSWORD[chat_id] = username
        await update.message.reply_text("Введите пароль для входа:")


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise ValueError("Установите TELEGRAM_BOT_TOKEN в переменных окружения или .env")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()

"""Обработчики команд и сообщений бота."""
import re
import asyncio
from typing import Optional

from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest, TimedOut as TelegramTimedOut

from core.models import Brand, CarModel, City, TelegramUser

from .keyboards import get_brands_keyboard, get_cities_keyboard, get_models_keyboard
from .services import send_ads_for_user
from .state import PENDING_PASSWORD, USER_STATE


def get_user_by_chat_or_username(chat_id: int, username: Optional[str]) -> Optional[TelegramUser]:
    q = TelegramUser.objects.filter(chat_id=chat_id)
    if q.exists():
        return q.first()
    if username:
        q = TelegramUser.objects.filter(username=username)
        if q.exists():
            return q.first()
    return None


def get_user_by_password(password: str) -> Optional[TelegramUser]:
    q = TelegramUser.objects.filter(password=password)
    return q.first() if q.exists() else None


async def ask_city(update: Update, context: ContextTypes.DEFAULT_TYPE, user: TelegramUser) -> None:
    """Показать выбор города (первая страница)."""
    chat_id = update.effective_chat.id
    USER_STATE[chat_id] = {"state": "city", "user": user}
    keyboard = await sync_to_async(get_cities_keyboard)(0)
    await context.bot.send_message(chat_id=chat_id, text="Выберите город:", reply_markup=keyboard)


async def ask_brands(update: Update, context: ContextTypes.DEFAULT_TYPE, user: TelegramUser) -> None:
    chat_id = update.effective_chat.id
    USER_STATE[chat_id] = {"state": "brands", "selected": set()}
    keyboard = await sync_to_async(get_brands_keyboard)(set())
    await context.bot.send_message(chat_id=chat_id, text="Выберите марки автомобилей:", reply_markup=keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        await ask_city(update, context, user)
    else:
        PENDING_PASSWORD[chat_id] = username
        await update.message.reply_text(
            "Привет! Я бот для подбора автомобилей с Авито.\nВведите пароль для входа:"
        )


async def command_brands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /brands — изменить выбор марок автомобилей."""
    chat_id = update.effective_chat.id
    username = update.effective_user.username if update.effective_user else None
    if chat_id in PENDING_PASSWORD:
        await update.message.reply_text("Сначала введите пароль для входа.")
        return

    user = await sync_to_async(get_user_by_chat_or_username)(chat_id, username)
    if not user:
        PENDING_PASSWORD[chat_id] = username
        await update.message.reply_text("Введите пароль для входа:")
        return

    await ask_city(update, context, user)


async def command_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /city — изменить город."""
    chat_id = update.effective_chat.id
    username = update.effective_user.username if update.effective_user else None
    if chat_id in PENDING_PASSWORD:
        await update.message.reply_text("Сначала введите пароль для входа.")
        return

    user = await sync_to_async(get_user_by_chat_or_username)(chat_id, username)
    if not user:
        PENDING_PASSWORD[chat_id] = username
        await update.message.reply_text("Введите пароль для входа:")
        return

    await ask_city(update, context, user)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    try:
        await query.answer()
    except (TelegramTimedOut, BadRequest):
        # TimedOut — сеть; BadRequest — «query too old» (пользователь нажал кнопку давно)
        pass
    chat_id = update.effective_chat.id
    data = query.data

    if data.startswith("city_page_"):
        page = int(data.split("_")[2])
        state = USER_STATE.get(chat_id, {})
        if state.get("state") != "city":
            return
        keyboard = await sync_to_async(get_cities_keyboard)(page)
        await query.edit_message_text("Выберите город:", reply_markup=keyboard)
        return

    if data.startswith("city_"):
        try:
            city_id = int(data.split("_")[1])
        except (IndexError, ValueError):
            return
        state = USER_STATE.get(chat_id, {})
        if state.get("state") != "city":
            return
        user = state.get("user")
        if not user:
            return

        def _save_city():
            user.city_id = city_id
            user.save(update_fields=["city_id"])

        await sync_to_async(_save_city)()
        city = await sync_to_async(City.objects.get)(id=city_id)
        USER_STATE[chat_id] = {"state": "brands", "selected": set()}
        keyboard = await sync_to_async(get_brands_keyboard)(set())
        await query.edit_message_text(
            f"Город: {city.name_ru}. Выберите марки автомобилей:",
            reply_markup=keyboard,
        )
        return

    if data == "brands_done":
        state = USER_STATE.get(chat_id, {})
        if state.get("state") != "brands":
            return
        user = await sync_to_async(get_user_by_chat_or_username)(
            chat_id, update.effective_user.username if update.effective_user else None
        )
        if not user:
            return
        selected_ids = state.get("selected", set())

        def _save_brands():
            user.selected_brands.set(Brand.objects.filter(id__in=list(selected_ids)))

        await sync_to_async(_save_brands)()
        brand_ids = list(selected_ids)
        USER_STATE[chat_id] = {"state": "models", "selected": set(), "brand_ids": brand_ids, "page": 0}
        keyboard = await sync_to_async(get_models_keyboard)(brand_ids, set(), 0)
        await query.edit_message_text(
            "Выберите модели (или «Готово» — тогда все модели выбранных марок):",
            reply_markup=keyboard,
        )
        return

    if data.startswith("model_page_"):
        page = int(data.split("_")[2])
        state = USER_STATE.get(chat_id, {})
        if state.get("state") != "models":
            return
        brand_ids = state.get("brand_ids", [])
        selected = state.get("selected", set())
        state["page"] = page
        keyboard = await sync_to_async(get_models_keyboard)(brand_ids, selected, page)
        await query.edit_message_reply_markup(reply_markup=keyboard)
        return

    if data.startswith("model_"):
        try:
            model_id = int(data.split("_")[1])
        except (IndexError, ValueError):
            return
        state = USER_STATE.get(chat_id, {})
        if state.get("state") != "models":
            return
        selected = state.get("selected", set())
        if model_id in selected:
            selected.discard(model_id)
        else:
            selected.add(model_id)
        state["selected"] = selected
        brand_ids = state.get("brand_ids", [])
        page = state.get("page", 0)
        keyboard = await sync_to_async(get_models_keyboard)(brand_ids, selected, page)
        await query.edit_message_reply_markup(reply_markup=keyboard)
        return

    if data == "models_done":
        state = USER_STATE.get(chat_id, {})
        if state.get("state") != "models":
            return
        user = await sync_to_async(get_user_by_chat_or_username)(
            chat_id, update.effective_user.username if update.effective_user else None
        )
        if not user:
            return
        selected_ids = state.get("selected", set())

        def _save_models():
            user.selected_models.set(CarModel.objects.filter(id__in=list(selected_ids)))

        await sync_to_async(_save_models)()
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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    username = update.effective_user.username if update.effective_user else None
    text = (update.message.text or "").strip()

    if chat_id in PENDING_PASSWORD:
        user = await sync_to_async(get_user_by_password)(text)
        if user:
            user.chat_id = chat_id
            user.username = username or user.username
            await sync_to_async(user.save)()
            del PENDING_PASSWORD[chat_id]
            await update.message.reply_text("Вход выполнен.")
            await ask_city(update, context, user)
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
                    await update.message.reply_text(
                        f"Порог цены сохранён: {price} ₽\n\nНачинаю подбор объявлений по выбранным маркам…"
                    )
                    asyncio.create_task(send_ads_for_user(update, context, state["user"].id))
                    return
        await update.message.reply_text("Введите число (например: 500000):")
        return

    user = await sync_to_async(get_user_by_chat_or_username)(chat_id, username)
    if not user:
        PENDING_PASSWORD[chat_id] = username
        await update.message.reply_text("Введите пароль для входа:")

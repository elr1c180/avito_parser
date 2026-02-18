"""
Рассылка объявлений: по запросу и по расписанию (каждые 15 мин).
Одно сообщение на объявление; формат: Марка / Модель / Цена / Дата публикации; при наличии — фото.
При ошибке парсинга пользователю — только «Требуется замена прокси»; полная ошибка пишется в лог.
"""
import asyncio
import html as html_lib
import logging
import time
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import ContextTypes

from app_config import get_bot_token, get_proxy_config
from core.avito_search import AvitoAd, search_ads
from core.models import Brand, SeenAd, TelegramUser

PROXY_ERROR_MSG = "Требуется замена прокси. Проверьте config.toml (секция [avito])."
LIMIT_PER_BRAND = 20
MAX_AGE_MINUTES = 60
# Пауза между отправкой объявлений (чтобы не спамить и не грузить прокси)
SEND_INTERVAL_SEC = 3
# Пауза между парсингом разных марок (снижает риск блокировки прокси)
PAUSE_BETWEEN_BRANDS_SEC = 8
MSK = ZoneInfo("Europe/Moscow")


def _format_published_at(dt: Optional[datetime]) -> str:
    if dt is None:
        return "—"
    try:
        return dt.astimezone(MSK).strftime("%d.%m.%Y, %H:%M")
    except Exception:
        return "—"


def _ad_caption(brand_name: str, ad: AvitoAd) -> str:
    """Текст одного объявления: жирные подписи Марка/Модель/Цена/Дата, данные обычным."""
    price_str = f"{ad.price} ₽" if ad.price is not None else "—"
    date_str = _format_published_at(ad.published_at)
    parts = [
        "<b>Марка</b>",
        html_lib.escape(brand_name),
        "<b>Модель</b>",
        html_lib.escape(ad.title),
        "<b>Цена</b>",
        html_lib.escape(price_str),
        "<b>Дата публикации</b>",
        html_lib.escape(date_str),
        "",
        html_lib.escape(ad.url),
    ]
    return "\n".join(parts)


def _send_telegram_message(token: str, chat_id: int, text: str) -> bool:
    try:
        import requests
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=15,
        )
        return r.status_code == 200
    except Exception:
        logging.exception("Ошибка отправки сообщения в Telegram")
        return False


def _send_telegram_photo(token: str, chat_id: int, photo_url: str, caption: str) -> bool:
    try:
        import requests
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendPhoto",
            json={
                "chat_id": chat_id,
                "photo": photo_url,
                "caption": caption,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        return r.status_code == 200
    except Exception:
        logging.exception("Ошибка отправки фото в Telegram")
        return False


async def send_ads_for_user(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    chat_id = update.effective_chat.id
    user = await sync_to_async(
        lambda: TelegramUser.objects.prefetch_related("selected_brands").get(id=user_id)
    )()
    brands = list(user.selected_brands.all())
    if not brands:
        await context.bot.send_message(chat_id=chat_id, text="Марки не выбраны. Нажмите /start или /brands.")
        return

    max_price = user.max_price
    proxy_string, proxy_change_url = get_proxy_config()

    for brand in brands:
        if not brand.avito_url:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Для марки «{brand.name}» не задана ссылка поиска в админке. Пропускаю.",
            )
            continue

        await context.bot.send_message(chat_id=chat_id, text=f"Ищу {brand.name}… (объявления за последний час)")
        try:
            ads = await asyncio.to_thread(
                search_ads,
                url=brand.avito_url,
                max_price=max_price,
                pages=1,
                max_age_minutes=MAX_AGE_MINUTES,
                proxy_string=proxy_string,
                proxy_change_url=proxy_change_url,
            )
        except Exception:
            logging.exception("Парсинг Avito (по запросу пользователя): %s", brand.name)
            await context.bot.send_message(chat_id=chat_id, text=PROXY_ERROR_MSG)
            continue

        if not ads:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"По {brand.name} объявлений за последний час не найдено. Проверьте ссылку и порог цены ({max_price or '—'} ₽).",
            )
            continue

        ad_ids = [a.avito_id for a in ads]
        seen_ids = set(
            await sync_to_async(
                lambda: list(SeenAd.objects.filter(user=user, avito_id__in=ad_ids).values_list("avito_id", flat=True))
            )()
        )
        fresh = [a for a in ads if a.avito_id not in seen_ids][:LIMIT_PER_BRAND]
        if not fresh:
            await context.bot.send_message(chat_id=chat_id, text=f"По {brand.name} новых объявлений за последний час пока нет.")
            continue

        def _mark_seen():
            objs = [SeenAd(user=user, avito_id=a.avito_id, price=a.price) for a in fresh]
            SeenAd.objects.bulk_create(objs, ignore_conflicts=True)

        await sync_to_async(_mark_seen)()

        for a in fresh:
            caption = _ad_caption(brand.name, a)
            if a.image_url:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=a.image_url,
                    caption=caption,
                    parse_mode="HTML",
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=caption,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            await asyncio.sleep(SEND_INTERVAL_SEC)


def run_periodic_ads() -> None:
    """Каждые 15 минут: парсинг по маркам, рассылка только свежих. При ошибке — тихо пропуск."""
    try:
        token = get_bot_token()
    except Exception:
        logging.exception("Не удалось получить токен бота для рассылки")
        return
    proxy_string, proxy_change_url = get_proxy_config()
    brands = list(Brand.objects.filter(avito_url__isnull=False).exclude(avito_url=""))
    if not brands:
        return

    for brand in brands:
        users = list(TelegramUser.objects.filter(selected_brands=brand).exclude(chat_id__isnull=True))
        if not users:
            continue
        try:
            ads = search_ads(
                url=brand.avito_url,
                max_price=None,
                pages=1,
                max_age_minutes=MAX_AGE_MINUTES,
                proxy_string=proxy_string,
                proxy_change_url=proxy_change_url,
            )
        except Exception:
            logging.exception("Парсинг Avito (по расписанию), марка: %s", brand.name)
            continue
        if not ads:
            continue

        for user in users:
            max_price = user.max_price
            ad_ids = [a.avito_id for a in ads]
            seen_ids = set(SeenAd.objects.filter(user=user, avito_id__in=ad_ids).values_list("avito_id", flat=True))
            fresh = [a for a in ads if a.avito_id not in seen_ids]
            if max_price is not None:
                fresh = [a for a in fresh if a.price is None or a.price <= max_price]
            fresh = fresh[:LIMIT_PER_BRAND]
            if not fresh:
                continue
            SeenAd.objects.bulk_create(
                [SeenAd(user=user, avito_id=a.avito_id, price=a.price) for a in fresh],
                ignore_conflicts=True,
            )
            for a in fresh:
                caption = _ad_caption(brand.name, a)
                if a.image_url:
                    _send_telegram_photo(token, user.chat_id, a.image_url, caption)
                else:
                    _send_telegram_message(token, user.chat_id, caption)
                time.sleep(SEND_INTERVAL_SEC)

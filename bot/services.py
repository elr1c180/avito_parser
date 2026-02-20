"""
Рассылка объявлений: по запросу и по расписанию (каждые 5 мин). Только объявления за последние 10 минут.
Одно сообщение на объявление; формат: Марка / Модель / Цена / Дата публикации; при наличии — фото.
При ошибке парсинга пользователю — только «Требуется замена прокси»; полная ошибка пишется в лог.
"""
import asyncio
import html as html_lib
import logging
import time
from datetime import datetime
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from zoneinfo import ZoneInfo

from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import ContextTypes

from app_config import get_avito_timeout, get_block_threshold, get_bot_token, get_proxy_config, get_pause_between_requests, get_use_playwright
from core.avito_search import AvitoAd, search_ads
from core.models import Brand, CarModel, SeenAd, TelegramUser

# Формат Avito: если у марки в БД есть avito_url — используем его; иначе собираем без суффикса -ASgBAg...
AVITO_BASE = "https://www.avito.ru"
AVITO_CARS_SEGMENT = "avtomobili"
# Обязательные параметры поиска в каждой ссылке Avito
AVITO_QUERY_PARAMS = {"cd": "1", "localPriority": "0", "radius": "200", "s": "104", "searchRadius": "200"}
AVITO_QUERY = "&".join(f"{k}={v}" for k, v in AVITO_QUERY_PARAMS.items())


def _ensure_avito_query(url: str) -> str:
    """Добавляет/подменяет в URL параметры localPriority, radius, s, searchRadius."""
    if not url or not url.startswith("http"):
        return url
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    for k, v in AVITO_QUERY_PARAMS.items():
        params[k] = [v]
    new_query = urlencode(params, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))


def get_cities_for_user(user) -> list:
    """Список городов для поиска: выбранные города или один основной город."""
    selected = list(user.selected_cities.all()[:100])
    if selected:
        return selected
    if user.city_id and getattr(user, "city", None):
        return [user.city]
    return []


def _inject_city_into_avito_url(url: str, city_slug: str) -> str:
    """Подставляет город пользователя в путь Avito (первый сегмент после хоста)."""
    if not city_slug or not url.startswith("http"):
        return url
    city_slug = city_slug.strip().strip("/")
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return url
    parts[0] = city_slug
    new_path = "/" + "/".join(parts)
    return urlunparse((parsed.scheme, parsed.netloc, new_path, parsed.params, parsed.query, parsed.fragment))


def _build_search_url(user, brand, model=None, city=None) -> Optional[str]:
    """
    Если у марки в БД заполнена «Ссылка поиска Avito» (avito_url) — используем её,
    подставив город в путь. Иначе собираем URL по city/slug. city — для мульти-городов.
    """
    use_city = city or (user and getattr(user, "city", None))
    avito_url = getattr(brand, "avito_url", None)
    if avito_url and str(avito_url).strip():
        url = str(avito_url).strip()
        if not url.startswith("http"):
            return None
        if use_city and (getattr(use_city, "slug", None) or "").strip():
            url = _inject_city_into_avito_url(url, use_city.slug)
        return _ensure_avito_query(url)

    if not use_city or not getattr(brand, "slug", None) or not (brand.slug or "").strip():
        return None
    city_slug = (getattr(use_city, "slug", None) or "").strip().strip("/")
    brand_slug = (brand.slug or "").strip().strip("/")
    if not city_slug or not brand_slug:
        return None
    if model and getattr(model, "slug", None) and (model.slug or "").strip():
        model_slug = (model.slug or "").strip().strip("/")
        path = f"{city_slug}/{AVITO_CARS_SEGMENT}/{brand_slug}/{model_slug}"
    else:
        path = f"{city_slug}/{AVITO_CARS_SEGMENT}/{brand_slug}"
    return _ensure_avito_query(f"{AVITO_BASE}/{path}?{AVITO_QUERY}")


def _user_models_by_brand(user):
    """Возвращает dict: brand_id -> [названия выбранных моделей этой марки]."""
    result = {}
    for m in user.selected_models.select_related("brand").all():
        result.setdefault(m.brand_id, []).append(m.name)
    return result


PROXY_ERROR_MSG = "Требуется замена прокси. Проверьте config.toml (секция [avito])."
# Все объявления со страницы, без лимита
LIMIT_PER_BRAND = None
# Только объявления, опубликованные не более N минут назад
MAX_AGE_MINUTES = 10
# Пауза между отправкой объявлений (чтобы не спамить и не грузить прокси)
SEND_INTERVAL_SEC = 3
# Пауза между парсингом разных марок (снижает риск блокировки прокси)
PAUSE_BETWEEN_BRANDS_SEC = 8
MSK = ZoneInfo("Europe/Moscow")

# Пауза после смены IP мобильного прокси (как в debug-скрипте)
PROXY_CHANGE_SLEEP_SEC = 8


def _change_proxy_ip_before_avito(proxy_change_url: Optional[str], use_playwright: bool) -> None:
    """
    Один раз перед запросами к Avito дергает смену IP мобильного прокси (как в scripts/debug_avito_response.py).
    При использовании Playwright или без proxy_change_url ничего не делает.
    """
    if not proxy_change_url or use_playwright:
        return
    try:
        import requests
        logging.info("Смена IP мобильного прокси перед запросами к Avito…")
        requests.get(proxy_change_url, timeout=15)
        time.sleep(PROXY_CHANGE_SLEEP_SEC)
        logging.info("Смена IP мобильного прокси перед запросами к Avito… ок")
    except Exception as e:
        logging.warning("Смена IP перед Avito не удалась: %s", e)


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


def _search_tasks_for_user(user):
    """
    Список (brand, model_or_None, city) для поиска: по выбранным маркам и по каждому выбранному городу.
    """
    tasks = []
    cities = get_cities_for_user(user)
    if not cities:
        return tasks
    brands = list(user.selected_brands.all())
    selected_models = list(user.selected_models.select_related("brand").filter(slug__isnull=False).exclude(slug=""))
    models_by_brand = {}
    for m in selected_models:
        models_by_brand.setdefault(m.brand_id, []).append(m)

    for city in cities:
        for brand in brands:
            has_slug = (getattr(brand, "slug", None) or "").strip()
            has_url = (getattr(brand, "avito_url", None) or "").strip()
            if not has_slug and not has_url:
                continue
            models = models_by_brand.get(brand.id) or []
            if models:
                for m in models:
                    if (m.slug or "").strip():
                        tasks.append((brand, m, city))
            else:
                tasks.append((brand, None, city))
    return tasks


async def send_ads_for_user(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    chat_id = update.effective_chat.id
    user = await sync_to_async(
        lambda: TelegramUser.objects.prefetch_related("selected_brands", "selected_models", "selected_cities").select_related("city").get(id=user_id)
    )()
    tasks = await sync_to_async(_search_tasks_for_user)(user)
    if not tasks:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Нет ни одной пары марка+город. Выберите хотя бы один город (/city) и марки (/brands); у марок в админке должны быть slug.",
        )
        return

    max_price = user.max_price
    proxy_string, proxy_change_url = get_proxy_config()
    use_playwright = get_use_playwright()
    timeout = get_avito_timeout()
    block_threshold = get_block_threshold()
    pause_between = get_pause_between_requests()

    # Сначала смена IP (как в debug-скрипте), чтобы не получать ответ «редирект/бот» без каталога
    await asyncio.to_thread(_change_proxy_ip_before_avito, proxy_change_url, use_playwright)

    for i, (brand, model, city) in enumerate(tasks):
        if i > 0 and pause_between > 0:
            await asyncio.sleep(pause_between)
        url = _build_search_url(user, brand, model, city=city)
        if not url:
            continue
        label = f"{brand.name} {model.name}" if model else brand.name
        city_label = getattr(city, "name_ru", None) or str(city)
        label = f"{label} ({city_label})"
        logging.info("Парсинг Avito: %s → %s", label, url)
        print(f"[Avito] Поиск: {label}\n[Avito] Ссылка: {url}", flush=True)
        await context.bot.send_message(chat_id=chat_id, text=f"Ищу {label}…")
        try:
            ads = await asyncio.to_thread(
                search_ads,
                url=url,
                max_price=max_price,
                pages=1,
                max_age_minutes=MAX_AGE_MINUTES,
                timeout=timeout,
                block_threshold=block_threshold,
                proxy_string=proxy_string,
                proxy_change_url=proxy_change_url,
                use_playwright=use_playwright,
            )
        except Exception:
            logging.exception("Парсинг Avito (по запросу пользователя): %s. URL: %s", label, url)
            await context.bot.send_message(chat_id=chat_id, text=PROXY_ERROR_MSG)
            continue

        if not ads:
            print(f"[Avito] По {label} ничего не найдено. Ссылка: {url}", flush=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"По {label} новых объявлений за последние {MAX_AGE_MINUTES} мин не найдено. "
                    f"Порог цены: {max_price or '—'} ₽.\n\nСсылка поиска:\n{url}"
                ),
            )
            continue

        ad_ids = [a.avito_id for a in ads]
        seen_ids = set(
            await sync_to_async(
                lambda: list(SeenAd.objects.filter(user=user, avito_id__in=ad_ids).values_list("avito_id", flat=True))
            )()
        )
        fresh = [a for a in ads if a.avito_id not in seen_ids]
        if LIMIT_PER_BRAND is not None:
            fresh = fresh[:LIMIT_PER_BRAND]
        if not fresh:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"По {label} новых объявлений за последние {MAX_AGE_MINUTES} мин пока нет.\n\nСсылка: {url}",
            )
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
        await asyncio.sleep(PAUSE_BETWEEN_BRANDS_SEC)


def run_periodic_ads() -> None:
    """Каждые 5 минут: парсинг по URL, рассылка только объявлений за последние 10 минут."""
    try:
        token = get_bot_token()
    except Exception:
        logging.exception("Не удалось получить токен бота для рассылки")
        return
    proxy_string, proxy_change_url = get_proxy_config()
    use_playwright = get_use_playwright()
    timeout = get_avito_timeout()
    block_threshold = get_block_threshold()
    users = list(
        TelegramUser.objects.filter(selected_brands__isnull=False)
        .exclude(chat_id__isnull=True)
        .select_related("city")
        .prefetch_related("selected_brands", "selected_models", "selected_cities")
        .distinct()
    )
    if not users:
        return

    url_to_tasks = {}
    for user in users:
        for brand, model, city in _search_tasks_for_user(user):
            url = _build_search_url(user, brand, model, city=city)
            if url:
                url_to_tasks.setdefault(url, []).append((user, brand, model))

    # Сначала смена IP (как в debug-скрипте), чтобы не получать ответ «редирект/бот» без каталога
    _change_proxy_ip_before_avito(proxy_change_url, use_playwright)

    pause_between = get_pause_between_requests()
    for idx, (url, task_list) in enumerate(url_to_tasks.items()):
        if idx > 0 and pause_between > 0:
            time.sleep(pause_between)
        ads = None
        for attempt in range(2):  # как в parser_avito: при ошибке одна повторная попытка
            try:
                ads = search_ads(
                    url=url,
                    max_price=None,
                    pages=1,
                    max_age_minutes=MAX_AGE_MINUTES,
                    timeout=timeout,
                    block_threshold=block_threshold,
                    proxy_string=proxy_string,
                    proxy_change_url=proxy_change_url,
                    use_playwright=use_playwright,
                )
                break
            except Exception:
                logging.exception("Парсинг Avito (по расписанию), url: %s, попытка %s/2", url[:80], attempt + 1)
                if attempt == 0:
                    time.sleep(15)  # пауза перед повтором, как пауза между ссылками в parser_avito
        if ads is None:
            continue
        if not ads:
            continue

        for user, brand, model in task_list:
            max_price = user.max_price
            ad_ids = [a.avito_id for a in ads]
            seen_ids = set(SeenAd.objects.filter(user=user, avito_id__in=ad_ids).values_list("avito_id", flat=True))
            fresh = [a for a in ads if a.avito_id not in seen_ids]
            if max_price is not None:
                fresh = [a for a in fresh if a.price is None or a.price <= max_price]
            if LIMIT_PER_BRAND is not None:
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
        time.sleep(PAUSE_BETWEEN_BRANDS_SEC)

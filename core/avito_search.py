"""
Поиск объявлений на Avito по ссылке (свежие по дате из выдачи).
Использует пакет avito/ и единый config.toml для прокси.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import ValidationError

logger = logging.getLogger(__name__)

from avito.client import HttpClient
from avito.dto import AvitoConfig
from avito.extract import extract_state_json, get_next_page_url
from avito.models import Item, ItemsResponse
from avito.proxy_factory import build_proxy
from avito.utils import get_first_image


@dataclass(frozen=True)
class AvitoAd:
    avito_id: int
    title: str
    price: Optional[int]
    url: str
    location: Optional[str]
    image_url: Optional[str]
    published_at: Optional[datetime]  # UTC


def _log_avito_response_debug(html: str, state: dict, url: str) -> None:
    """При пустом каталоге выводит в лог, что именно пришло от Авито (для отладки)."""
    logger.warning(
        "[Avito DEBUG] Каталог не найден. URL: %s | Длина HTML: %s | state пустой: %s | Ключи state: %s",
        url,
        len(html),
        not state,
        list(state.keys()) if isinstance(state, dict) else type(state).__name__,
    )
    # Показать начало HTML (часто видно: это выдача или капча/блок)
    sample = (html[:800] + "..." if len(html) > 800 else html).replace("\n", " ")
    logger.warning("[Avito DEBUG] Начало ответа (первые ~800 символов): %s", sample)

def _parse_published_at(sort_time_stamp: Optional[int]) -> Optional[datetime]:
    """Преобразует sortTimeStamp (секунды или миллисекунды) в datetime UTC."""
    if sort_time_stamp is None:
        return None
    try:
        ts = int(sort_time_stamp)
        if ts >= 1e12:  # миллисекунды
            ts = ts / 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except (ValueError, OSError):
        return None


def _fetch_page_html(
    next_url: str,
    use_playwright: bool,
    proxy_string: Optional[str],
    proxy_change_url: Optional[str],
    timeout: int,
    max_retries: int,
    retry_delay: int,
) -> str:
    """Возвращает HTML страницы: через Playwright или через HttpClient."""
    if use_playwright:
        from avito.playwright_fetch import fetch_html
        logger.info("Парсинг Avito (Playwright), URL: %s", next_url[:80])
        return fetch_html(url=next_url, proxy_string=proxy_string or None, timeout=timeout * 1000)
    proxy = build_proxy(AvitoConfig(proxy_string=proxy_string or "", proxy_change_url=proxy_change_url or ""))
    client = HttpClient(proxy=proxy, timeout=timeout, max_retries=max_retries, retry_delay=retry_delay)
    response = client.request("GET", next_url)
    return response.text


def search_ads(
    *,
    url: str,
    max_price: Optional[int] = None,
    pages: int = 1,
    max_age_minutes: Optional[int] = 10,
    timeout: int = 120,
    max_retries: int = 5,
    retry_delay: int = 5,
    proxy_string: Optional[str] = None,
    proxy_change_url: Optional[str] = None,
    use_playwright: bool = False,
) -> List[AvitoAd]:
    """
    Поиск объявлений по ссылке Avito. При ошибке (блокировка, сеть) пробрасывает исключение.
    max_age_minutes: только объявления, опубликованные не более N минут назад (None — без фильтра).
    use_playwright: True — загрузка через браузер (обход 403 на сервере), как в parser_avito.
    """
    logger.info("Парсинг Avito, URL: %s", url)
    results: List[AvitoAd] = []
    next_url = url
    now_utc = datetime.now(timezone.utc)

    for page_num in range(max(1, pages)):
        if page_num > 0:
            logger.info("Парсинг Avito, страница %s, URL: %s", page_num + 1, next_url)
        html = _fetch_page_html(
            next_url, use_playwright, proxy_string, proxy_change_url, timeout, max_retries, retry_delay
        )
        state = extract_state_json(html)
        catalog = (
            state.get("data", {}).get("catalog")
            or state.get("listing", {}).get("data", {}).get("catalog")
            or {}
        )
        if not catalog:
            # Показать, что пришло от парсера при пустом каталоге
            _log_avito_response_debug(html, state, next_url)
            break

        try:
            items = ItemsResponse(**catalog).items
        except ValidationError:
            break

        if not items:
            break

        for it in items:
            if not it.id or not it.urlPath:
                continue
            price_value = None
            if it.priceDetailed and it.priceDetailed.value is not None:
                try:
                    price_value = int(it.priceDetailed.value)
                except (TypeError, ValueError):
                    pass
            if max_price is not None and price_value is not None and price_value > max_price:
                continue
            title = (it.title or "").strip()
            if not title:
                continue
            full_url = f"https://www.avito.ru{it.urlPath}"
            location_name = it.location.name if it.location else None
            image_url = get_first_image(it) if getattr(it, "images", None) else None
            ad_id = int(it.id) if isinstance(it.id, int) else int((it.id or {}).get("value", 0))
            published_at = _parse_published_at(getattr(it, "sortTimeStamp", None))
            if max_age_minutes is not None:
                if published_at is None:
                    continue
                age_seconds = (now_utc - published_at).total_seconds()
                if age_seconds > max_age_minutes * 60 or age_seconds < 0:
                    continue
            results.append(
                AvitoAd(
                    avito_id=ad_id,
                    title=title,
                    price=price_value,
                    url=full_url,
                    location=location_name,
                    image_url=image_url,
                    published_at=published_at,
                )
            )
        next_url = get_next_page_url(next_url)

    return results

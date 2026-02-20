#!/usr/bin/env python3
"""
Скрипт отладки: по ссылке Avito забирает страницу и выводит в консоль все объявления.

Режимы:
  HTTP (по умолчанию):
    python scripts/debug_avito_response.py [URL]
    python scripts/debug_avito_response.py --http [URL]
  Playwright (браузер):
    python scripts/debug_avito_response.py --playwright [URL]

Без URL используется ссылка по умолчанию (Москва, грузовики Toyota).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app_config import get_proxy_config
from avito.client import HttpClient
from avito.dto import AvitoConfig
from avito.extract import extract_state_json
from avito.models import ItemsResponse
from avito.proxy_factory import build_proxy
from avito.utils import get_first_image
from pydantic import ValidationError


DEFAULT_URL = "https://www.avito.ru/moskva/gruzoviki_i_spetstehnika/gruzoviki/toyota-ASgBAgICAkRUkAKOwA2aiTc?cd=1&radius=200&searchRadius=200"


def _parse_args():
    argv = sys.argv[1:]
    use_playwright = "--playwright" in argv or "-p" in argv
    use_http = "--http" in argv
    if use_playwright and use_http:
        print("Укажите один режим: --http или --playwright", file=sys.stderr)
        sys.exit(1)
    url_candidates = [a for a in argv if a.startswith("http")]
    url = url_candidates[0] if url_candidates else DEFAULT_URL
    return url, use_playwright


def _fetch_html_http(url: str) -> str:
    proxy_string, proxy_change_url = get_proxy_config()
    proxy = build_proxy(AvitoConfig(proxy_string=proxy_string or "", proxy_change_url=proxy_change_url or ""))
    if proxy_change_url:
        try:
            import requests
            requests.get(proxy_change_url, timeout=30)
        except Exception as e:
            print(f"Смена IP: {e}", file=sys.stderr)
    client = HttpClient(proxy=proxy, timeout=30, max_retries=10, retry_delay=5, block_threshold=3)
    response = client.request("GET", url)
    return response.text


def _fetch_html_playwright(url: str) -> str:
    from avito.playwright_fetch import fetch_html
    try:
        proxy_string, _ = get_proxy_config()
    except Exception:
        proxy_string = None
    return fetch_html(url=url, proxy_string=proxy_string, timeout=60000)


def _format_price(it) -> str:
    if not getattr(it, "priceDetailed", None):
        return "—"
    pd = it.priceDetailed
    if getattr(pd, "value", None) is not None:
        try:
            return f"{int(pd.value):,} ₽".replace(",", " ")
        except (TypeError, ValueError):
            pass
    return getattr(pd, "string", None) or "—"


def main():
    url, use_playwright = _parse_args()
    mode = "Playwright" if use_playwright else "HTTP"
    print(f"URL: {url}")
    print(f"Режим: {mode}\n")

    if use_playwright:
        print("Загрузка (Playwright)…", flush=True)
        html = _fetch_html_playwright(url)
    else:
        print("Загрузка (HTTP)…", flush=True)
        html = _fetch_html_http(url)

    print(f"HTML: {len(html)} символов\n")

    state = extract_state_json(html)
    catalog = (
        state.get("data", {}).get("catalog")
        or state.get("listing", {}).get("data", {}).get("catalog")
        or {}
    )

    if not catalog:
        keys = list(state.keys()) if isinstance(state, dict) else "—"
        print("Каталог не найден. Ключи state:", keys)
        if len(html) < 100_000 and not state:
            print("\nПохоже на капчу или блок (мало HTML, пустой state). На сервере попробуйте режим HTTP:")
            print("  python3 scripts/debug_avito_response.py \"<та же ссылка>\"")
        return

    try:
        items = ItemsResponse(**catalog).items
    except ValidationError as e:
        print("Ошибка валидации catalog:", e)
        return

    n = len(items)
    print(f"--- Объявления ({n} шт) ---\n")

    for i, it in enumerate(items, 1):
        if not getattr(it, "id", None) or not getattr(it, "urlPath", None):
            continue
        try:
            ad_id = int(it.id) if isinstance(it.id, int) else int((it.id or {}).get("value", 0))
        except (TypeError, ValueError, AttributeError):
            ad_id = 0
        title = (getattr(it, "title", None) or "").strip() or "(без названия)"
        price_str = _format_price(it)
        url_path = (it.urlPath or "").strip()
        full_url = f"https://www.avito.ru{url_path}" if url_path else ""
        location = getattr(it.location, "name", None) if getattr(it, "location", None) else None
        has_photo = " [фото]" if get_first_image(it) else ""
        loc = f" | {location}" if location else ""
        print(f"{i}. {title}")
        print(f"   {price_str}{loc}{has_photo}")
        print(f"   {full_url}")
        print()


if __name__ == "__main__":
    main()

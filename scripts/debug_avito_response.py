#!/usr/bin/env python3
"""
Скрипт отладки: по ссылке Avito забирает страницу и выводит в консоль все объявления.

Код HTTP-клиента, прокси и заголовков теперь 1-в-1 как в parser_avito.

  python scripts/debug_avito_response.py [URL]
  python scripts/debug_avito_response.py --http [URL]
  python scripts/debug_avito_response.py --playwright [URL]
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app_config import get_proxy_config
from avito.client import HttpClient
from avito.dto import AvitoConfig
from avito.extract import extract_state_json
from avito.models import ItemsResponse
from avito.proxy_factory import build_proxy
from pydantic import ValidationError


DEFAULT_URL = "https://www.avito.ru/moskva/gruzoviki_i_spetstehnika/gruzoviki/toyota-ASgBAgICAkRUkAKOwA2aiTc?cd=1&radius=200&searchRadius=200"


def _parse_args():
    argv = sys.argv[1:]
    use_playwright = "--playwright" in argv or "-p" in argv
    url_candidates = [a for a in argv if a.startswith("http")]
    url = url_candidates[0] if url_candidates else DEFAULT_URL
    return url, use_playwright


def _fetch_http(url: str) -> str:
    proxy_string, proxy_change_url = get_proxy_config()
    config = AvitoConfig(proxy_string=proxy_string or "", proxy_change_url=proxy_change_url or "")
    proxy = build_proxy(config)
    client = HttpClient(proxy=proxy, timeout=20, max_retries=5)
    response = client.request("GET", url)
    return response.text


def _fetch_playwright(url: str) -> str:
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
        html = _fetch_playwright(url)
    else:
        print("Загрузка (HTTP)…", flush=True)
        html = _fetch_http(url)

    print(f"HTML: {len(html)} символов\n")

    state = extract_state_json(html)
    catalog = state.get("data", {}).get("catalog") if isinstance(state, dict) else {}
    catalog = catalog or {}

    if not catalog:
        print("Каталог не найден. Ключи state:", list(state.keys()) if isinstance(state, dict) else "—")
        return

    try:
        items = ItemsResponse(**catalog).items
    except ValidationError as e:
        print("Ошибка валидации catalog:", e)
        return

    n = len(items)
    print(f"--- Объявления ({n} шт) ---\n")

    for i, it in enumerate(items, 1):
        if not getattr(it, "urlPath", None):
            continue
        title = (getattr(it, "title", None) or "").strip() or "(без названия)"
        price_str = _format_price(it)
        url_path = (it.urlPath or "").strip()
        full_url = f"https://www.avito.ru{url_path}" if url_path else ""
        location = getattr(it.location, "name", None) if getattr(it, "location", None) else None
        loc = f" | {location}" if location else ""
        print(f"{i}. {title}")
        print(f"   {price_str}{loc}")
        print(f"   {full_url}")
        print()


if __name__ == "__main__":
    main()

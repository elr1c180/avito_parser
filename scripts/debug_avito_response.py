#!/usr/bin/env python3
"""
Скрипт отладки: по ссылке Avito забирает страницу и выводит в консоль все объявления.

HTTP-режим использует код оригинального parser_avito (прокси + клиент + запрос) один в один.
Режим Playwright — наш (браузер).

  python scripts/debug_avito_response.py [URL]
  python scripts/debug_avito_response.py --http [URL]
  python scripts/debug_avito_response.py --playwright [URL]
"""
import html as html_module
import json
import sys
from pathlib import Path

# корень проекта и parser_avito в path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
PARSER_AVITO = ROOT / "parser_avito"
sys.path.insert(0, str(PARSER_AVITO))

from app_config import get_proxy_config

# Оригинальные parser_avito: прокси и клиент (как в parser_cls.py)
from dto import AvitoConfig
from parser.http.client import HttpClient
from parser.proxies.proxy_factory import build_proxy
from models import ItemsResponse
from pydantic import ValidationError
from bs4 import BeautifulSoup


DEFAULT_URL = "https://www.avito.ru/moskva/gruzoviki_i_spetstehnika/gruzoviki/toyota-ASgBAgICAkRUkAKOwA2aiTc?cd=1&radius=200&searchRadius=200"


def _parse_args():
    argv = sys.argv[1:]
    use_playwright = "--playwright" in argv or "-p" in argv
    url_candidates = [a for a in argv if a.startswith("http")]
    url = url_candidates[0] if url_candidates else DEFAULT_URL
    return url, use_playwright


def find_json_on_page(html_code: str, data_type: str = "mime") -> dict:
    """Как в parser_avito parser_cls.py — извлечение state из script type=mime/invalid."""
    soup = BeautifulSoup(html_code, "html.parser")
    try:
        for _script in soup.select("script"):
            script_type = _script.get("type")
            if data_type == "mime" and script_type == "mime/invalid":
                script_content = html_module.unescape(_script.text)
                parsed_data = json.loads(script_content)
                if "state" in parsed_data:
                    return parsed_data["state"]
                if "data" in parsed_data:
                    return parsed_data["data"]
                return parsed_data
    except Exception:
        pass
    return {}


def _fetch_http_parser_avito(url: str) -> str:
    """Запрос к Avito как в parser_avito: тот же build_proxy, тот же HttpClient, без превентивной смены IP."""
    proxy_string, proxy_change_url = get_proxy_config()
    config = AvitoConfig(
        urls=[url],
        proxy_string=proxy_string or "",
        proxy_change_url=proxy_change_url or "",
        max_count_of_retry=5,
    )
    proxy = build_proxy(config)
    client = HttpClient(
        proxy=proxy,
        cookies=None,
        timeout=20,
        max_retries=config.max_count_of_retry,
    )
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
    mode = "Playwright" if use_playwright else "HTTP (parser_avito)"
    print(f"URL: {url}")
    print(f"Режим: {mode}\n")

    if use_playwright:
        print("Загрузка (Playwright)…", flush=True)
        html = _fetch_playwright(url)
    else:
        print("Загрузка (HTTP, как parser_avito)…", flush=True)
        html = _fetch_http_parser_avito(url)

    print(f"HTML: {len(html)} символов\n")

    state = find_json_on_page(html)
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

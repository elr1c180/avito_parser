#!/usr/bin/env python3
"""
Разовый скрипт: по ссылке Avito делает GET, извлекает state и выводит структуру,
чтобы понять, где лежит каталог объявлений. Запуск из корня проекта:
  python scripts/debug_avito_response.py
"""
import json
import sys
from pathlib import Path

# корень проекта в path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app_config import get_proxy_config
from avito.client import HttpClient
from avito.dto import AvitoConfig
from avito.extract import extract_state_json
from avito.proxy_factory import build_proxy


def _keys_tree(obj, prefix="", depth=0, max_depth=4):
    """Рекурсивно вывести ключи словаря (до max_depth уровней)."""
    if depth > max_depth:
        return
    if not isinstance(obj, dict):
        return
    for k, v in obj.items():
        line = f"{prefix}{k}"
        if isinstance(v, dict):
            print(line, "->", list(v.keys())[:15])
            _keys_tree(v, prefix + "  ", depth + 1, max_depth)
        elif isinstance(v, list):
            print(line, f"-> list(len={len(v)})")
            if v and isinstance(v[0], dict):
                _keys_tree(v[0], prefix + "  ", depth + 1, max_depth)


DEFAULT_URL = "https://www.avito.ru/astrahan/avtomobili/toyota/camry?localPriority=0&radius=0&s=104&searchRadius=0"

def main():
    URL = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    print("Запрос:", URL)
    try:
        proxy_string, proxy_change_url = get_proxy_config()
    except Exception:
        proxy_string, proxy_change_url = None, None
    proxy = build_proxy(AvitoConfig(proxy_string=proxy_string or "", proxy_change_url=proxy_change_url or ""))
    print("Прокси из config.toml:", "да" if (proxy_string or proxy_change_url) else "нет")
    # Мобильный прокси: сменить IP перед запросом (часто с сервера старый IP уже в бане)
    if proxy_change_url:
        try:
            import requests
            print("Смена IP мобильного прокси…", end=" ", flush=True)
            requests.get(proxy_change_url, timeout=15)
            print("ок")
        except Exception as e:
            print("ошибка:", e)
    client = HttpClient(proxy=proxy, timeout=30, max_retries=3, retry_delay=5)
    response = client.request("GET", URL)
    print("Статус:", response.status_code, "Длина HTML:", len(response.text))

    state = extract_state_json(response.text)
    print("\n--- Ключи state (верхний уровень) ---")
    print(list(state.keys()))

    data = state.get("data") or {}
    print("\n--- state['data'] ключи ---")
    print(list(data.keys()) if isinstance(data, dict) else type(data))

    # Где может быть каталог
    catalog = data.get("catalog") if isinstance(data, dict) else None
    listing = data.get("listing") if isinstance(data, dict) else None
    print("\n--- state['data']['catalog'] есть?", catalog is not None)
    print("--- state['data']['listing'] есть?", listing is not None)
    if isinstance(listing, dict):
        print("--- state['data']['listing'] ключи:", list(listing.keys()))
        ld = listing.get("data") or {}
        if isinstance(ld, dict):
            print("--- state['data']['listing']['data'] ключи:", list(ld.keys()))
            print("--- catalog в listing.data?", "catalog" in ld)

    print("\n--- Дерево state (первые уровни) ---")
    _keys_tree(state, max_depth=3)

    # Текущая логика парсера
    catalog_used = (
        state.get("data", {}).get("catalog")
        or state.get("listing", {}).get("data", {}).get("catalog")
        or {}
    )
    print("\n--- Что парсер подставляет в catalog (сейчас) ---")
    print("Пусто?" if not catalog_used else f"Ключи: {list(catalog_used.keys())}")


if __name__ == "__main__":
    main()

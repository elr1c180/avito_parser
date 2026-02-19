"""
Загрузка страницы Avito через Playwright (реальный браузер).
Используется при use_playwright=true для обхода 403 на сервере, по аналогии с parser_avito.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _parse_proxy_for_playwright(proxy_string: Optional[str]) -> Optional[dict]:
    """Преобразует proxy_string вида user:pass@host:port в dict для Playwright."""
    if not proxy_string or not proxy_string.strip():
        return None
    s = proxy_string.strip()
    if "@" not in s:
        return {"server": f"http://{s}"}
    left, right = s.rsplit("@", 1)
    if ":" in left:
        username, _, password = left.partition(":")
        return {
            "server": f"http://{right}",
            "username": username,
            "password": password,
        }
    return {"server": f"http://{right}"}


def fetch_html(
    url: str,
    proxy_string: Optional[str] = None,
    timeout: int = 30000,
) -> str:
    """
    Загружает HTML страницы через Chromium (Playwright).
    При proxy_string формата user:pass@host:port использует прокси.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError("Установите playwright: pip install playwright && python -m playwright install chromium") from None

    proxy = _parse_proxy_for_playwright(proxy_string)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        try:
            context = browser.new_context(
                proxy=proxy,
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                locale="ru-RU",
            )
            page = context.new_page()
            page.goto(url, wait_until="load", timeout=timeout)
            # Ждём появления блока с данными каталога (script с state), иначе приходит пустая оболочка
            try:
                page.wait_for_selector("script[type='mime/invalid']", timeout=min(15000, timeout // 2))
            except Exception:
                pass
            html = page.content()
            context.close()
            return html
        finally:
            browser.close()


def fetch_html_safe(url: str, proxy_string: Optional[str] = None, timeout: int = 30000) -> Optional[str]:
    """Как fetch_html, но при ошибке возвращает None и пишет в лог."""
    try:
        return fetch_html(url=url, proxy_string=proxy_string, timeout=timeout)
    except Exception as e:
        logger.warning("Playwright fetch failed for %s: %s", url[:80], e)
        return None

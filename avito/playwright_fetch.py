"""
Загрузка страницы Avito через Playwright (реальный браузер).
Используется при use_playwright=true для обхода 403 на сервере.

Почему с Playwright бывают проблемы: Avito может отдавать другой HTML для headless
(редирект, пустая оболочка без каталога, «Доступ ограничен»). Если HTTP+прокси работают —
оставьте use_playwright=false.
"""
import logging
import random
import time
from typing import Optional

logger = logging.getLogger(__name__)

PLAYWRIGHT_DELAY_MIN, PLAYWRIGHT_DELAY_MAX = 2, 6
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"

# Снижение детекта headless (часть сайтов смотрит на эти признаки)
STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
"""


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
    if proxy:
        delay = random.uniform(PLAYWRIGHT_DELAY_MIN, PLAYWRIGHT_DELAY_MAX)
        logger.debug("Playwright: пауза %.1f сек перед запросом (как в parser_avito)", delay)
        time.sleep(delay)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ],
        )
        try:
            context = browser.new_context(
                proxy=proxy,
                viewport={"width": 1920, "height": 1080},
                user_agent=USER_AGENT,
                locale="ru-RU",
                ignore_https_errors=True,
                extra_http_headers={
                    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
                },
            )
            context.add_init_script(STEALTH_JS)
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            # Даём время подгрузить скрипт с state (на части окружений он появляется с задержкой)
            try:
                page.wait_for_selector("script[type='mime/invalid']", timeout=min(20000, timeout // 2))
            except Exception:
                pass
            # Небольшая пауза на случай, если контент дописывается после появления скрипта
            time.sleep(2)
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

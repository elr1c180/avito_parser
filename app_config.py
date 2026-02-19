"""
Единая загрузка конфигурации из config.toml.
Используется ботом, парсером и Django (settings).
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_CONFIG: Optional[Dict[str, Any]] = None
_CONFIG_PATH = Path(__file__).resolve().parent / "config.toml"


def _load() -> Dict[str, Any]:
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG
    try:
        import tomli
        with open(_CONFIG_PATH, "rb") as f:
            _CONFIG = tomli.load(f)
        return _CONFIG
    except Exception as e:
        raise RuntimeError(f"Не удалось загрузить {_CONFIG_PATH}: {e}") from e


def get_bot_token() -> str:
    """Токен Telegram-бота: [bot].token, или [avito].tg_token, или TELEGRAM_BOT_TOKEN."""
    import os
    data = _load()
    token = (data.get("bot", {}).get("token") or "").strip()
    if not token:
        token = (data.get("avito", {}).get("tg_token") or "").strip()
    if not token:
        token = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        raise ValueError(
            "Укажите токен бота: в config.toml [bot].token или [avito].tg_token, "
            "или переменная TELEGRAM_BOT_TOKEN"
        )
    return token


def get_telegram_proxy() -> Optional[str]:
    """Прокси для api.telegram.org (если нужен)."""
    data = _load()
    return (data.get("bot", {}).get("telegram_proxy") or "").strip() or None


def get_proxy_config() -> Tuple[Optional[str], Optional[str]]:
    """Прокси для Avito: (proxy_string, proxy_change_url)."""
    data = _load()
    avito = data.get("avito", {})
    ps = (avito.get("proxy_string") or "").strip() or None
    pu = (avito.get("proxy_change_url") or "").strip() or None
    return ps, pu


def get_use_playwright() -> bool:
    """Использовать Playwright (браузер) для запросов к Avito — обход 403 на сервере."""
    data = _load()
    avito = data.get("avito", {})
    val = avito.get("use_playwright")
    if val is None:
        val = avito.get("use_webdriver")
    return str(val).lower() in ("1", "true", "yes")


def get_django_settings() -> Dict[str, Any]:
    """Настройки для Django (secret_key, debug, allowed_hosts)."""
    data = _load()
    d = data.get("django", {})
    return {
        "SECRET_KEY": d.get("secret_key", "dev-secret-key"),
        "DEBUG": str(d.get("debug", True)).lower() in ("1", "true", "yes"),
        "ALLOWED_HOSTS": d.get("allowed_hosts") or ["*"],
    }

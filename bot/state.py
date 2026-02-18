"""Состояние пользователей в диалоге (пароль, выбор марок, цена)."""
from typing import Any, Dict

PENDING_PASSWORD: Dict[int, Any] = {}
USER_STATE: Dict[int, Dict[str, Any]] = {}

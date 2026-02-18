from dataclasses import dataclass
from typing import Optional


@dataclass
class AvitoConfig:
    """Минимальный конфиг для построения прокси и HTTP-клиента."""
    proxy_string: Optional[str] = None
    proxy_change_url: Optional[str] = None

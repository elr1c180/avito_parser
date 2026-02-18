from abc import ABC, abstractmethod
from typing import Optional

import requests


class Proxy(ABC):
    @abstractmethod
    def get_httpx_proxy(self) -> Optional[str]:
        pass

    @abstractmethod
    def handle_block(self) -> None:
        pass


class NoProxy(Proxy):
    def get_httpx_proxy(self) -> Optional[str]:
        return None

    def handle_block(self) -> None:
        pass


class ServerProxy(Proxy):
    def __init__(self, proxy: str) -> None:
        self.proxy = proxy

    def get_httpx_proxy(self) -> str:
        return f"http://{self.proxy}"

    def handle_block(self) -> None:
        pass


class MobileProxy(Proxy):
    def __init__(self, url: str, change_ip_url: str) -> None:
        self.url = url
        self.change_ip_url = change_ip_url

    def get_httpx_proxy(self) -> str:
        return f"http://{self.url}"

    def handle_block(self) -> None:
        requests.get(self.change_ip_url, timeout=10)

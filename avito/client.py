import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

from .proxy import Proxy

HEADERS = {
    "sec-ch-ua-platform": '"Windows"',
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
    "sec-ch-ua-mobile": "?0",
}


class HttpClient:
    def __init__(
        self,
        proxy: Proxy,
        timeout: int = 20,
        max_retries: int = 5,
        retry_delay: int = 5,
        block_threshold: int = 3,
    ) -> None:
        self.proxy = proxy
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.block_threshold = block_threshold
        self._block_attempts = 0

    def _build_client(self) -> httpx.Client:
        return httpx.Client(
            proxy=self.proxy.get_httpx_proxy(),
            timeout=self.timeout,
            headers=HEADERS,
            http2=False,
        )

    def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        last_exc = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with self._build_client() as client:
                    response = client.request(method, url, **kwargs)
                if response.status_code in (401, 403, 429):
                    self._block_attempts += 1
                    if self._block_attempts >= self.block_threshold:
                        self.proxy.handle_block()
                        self._block_attempts = 0
                    time.sleep(self.retry_delay)
                    continue
                response.raise_for_status()
                self._block_attempts = 0
                return response
            except httpx.RequestError as e:
                last_exc = e
                logger.warning("Avito request attempt %s/%s failed: %s", attempt, self.max_retries, e)
                time.sleep(self.retry_delay)
        logger.error("Avito request failed after %s retries: %s", self.max_retries, last_exc)
        raise RuntimeError("HTTP request failed after retries") from last_exc

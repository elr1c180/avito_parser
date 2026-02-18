import html as _html
import json
from urllib.parse import parse_qs, urlencode, urlunparse, urlparse

from bs4 import BeautifulSoup


def get_next_page_url(url: str) -> str:
    parts = urlparse(url)
    params = parse_qs(parts.query)
    page = int(params.get("p", [1])[0])
    params["p"] = [str(page + 1)]
    new_query = urlencode(params, doseq=True)
    return urlunparse((parts.scheme, parts.netloc, parts.path, parts.params, new_query, parts.fragment))


def extract_state_json(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.select("script"):
        if script.get("type") != "mime/invalid":
            continue
        try:
            raw = _html.unescape(script.text)
            data = json.loads(raw)
            if "state" in data:
                return data["state"]
            if "data" in data:
                return data["data"]
            return data
        except Exception:
            continue
    return {}

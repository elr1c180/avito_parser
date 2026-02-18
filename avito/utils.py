from typing import Optional

from .models import Item


def get_first_image(ad: Item) -> Optional[str]:
    if not getattr(ad, "images", None) or not ad.images:
        return None
    try:
        img = ad.images[0]
        best = max(
            img.root.keys(),
            key=lambda k: int(k.split("x")[0]) * int(k.split("x")[1]),
        )
        return str(img.root[best])
    except Exception:
        return None

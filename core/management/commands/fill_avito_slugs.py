"""
Заполнить slug для марок и моделей по названию (латиница для Avito URL).
Запуск: python manage.py fill_avito_slugs
"""
import re

from django.core.management.base import BaseCommand

from core.models import Brand, CarModel

try:
    from transliterate import translit
except ImportError:
    translit = None


def _to_slug(name: str) -> str:
    if not name:
        return ""
    s = name.strip()
    if translit:
        try:
            s = translit(s, "ru", reversed=True)
        except Exception:
            pass
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s[:80] or ""


class Command(BaseCommand):
    help = "Заполнить slug у Brand и CarModel для URL Авито"

    def handle(self, *args, **options):
        updated_b = 0
        for brand in Brand.objects.all():
            if not brand.slug:
                brand.slug = _to_slug(brand.name) or _to_slug(brand.name.replace(" ", ""))
                brand.save(update_fields=["slug"])
                updated_b += 1
        self.stdout.write(f"Обновлено марок (slug): {updated_b}")

        updated_m = 0
        for model in CarModel.objects.select_related("brand").all():
            if not model.slug:
                model.slug = _to_slug(model.name) or _to_slug(model.name.replace(" ", ""))
                model.save(update_fields=["slug"])
                updated_m += 1
        self.stdout.write(self.style.SUCCESS(f"Обновлено моделей (slug): {updated_m}"))

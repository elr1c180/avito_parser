"""
Загрузка марок и моделей автомобилей из JSON.
Формат: {"Марка": ["Модель1", "Модель2", ...], ...}
Либо с явным slug для Avito: {"Марка": [["A-Class", "a-klass"], "B-Class", ...], ...}
Элемент может быть строкой (название, slug сгенерируется) или парой [название, slug].
Использование:
  python manage.py load_car_models
  python manage.py load_car_models --file core/data/car_models.json
"""
import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand

from core.models import Brand, CarModel

try:
    from transliterate import translit
except ImportError:
    translit = None


def _to_slug(name: str) -> str:
    """Название -> slug для Avito (латиница, lowercase, дефисы)."""
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
    help = "Загрузить марки и модели автомобилей из JSON"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default=None,
            help="Путь к JSON: {\"Марка\": [\"Модель1\", ...], ...}",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Не сохранять в БД",
        )

    def handle(self, *args, **options):
        path = options["file"] or (
            Path(__file__).resolve().parent.parent.parent / "data" / "car_models.json"
        )
        path = Path(path)
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"Файл не найден: {path}"))
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        total_models = 0
        for brand_name, model_names in data.items():
            if not brand_name or not isinstance(model_names, list):
                continue
            if options["dry_run"]:
                self.stdout.write(f"  {brand_name}: {len(model_names)} моделей")
                total_models += len(model_names)
                continue
            brand_name = brand_name.strip()
            brand, created_b = Brand.objects.get_or_create(name=brand_name)
            if created_b or not brand.slug:
                brand.slug = _to_slug(brand_name) or _to_slug(brand_name.replace(" ", ""))
                brand.save(update_fields=["slug"])
            for item in model_names:
                if isinstance(item, list):
                    if len(item) < 1:
                        continue
                    name = item[0]
                    slug_from_json = item[1].strip() if len(item) > 1 and isinstance(item[1], str) else None
                elif isinstance(item, str):
                    name = item
                    slug_from_json = None
                else:
                    continue
                if not name or not isinstance(name, str):
                    continue
                name = name.strip()
                model, created = CarModel.objects.get_or_create(brand=brand, name=name)
                if slug_from_json:
                    model.slug = slug_from_json[:80]
                    model.save(update_fields=["slug"])
                elif created or not model.slug:
                    model.slug = _to_slug(name) or _to_slug(name.replace(" ", ""))
                    model.save(update_fields=["slug"])
                if created:
                    total_models += 1
        self.stdout.write(self.style.SUCCESS(f"Добавлено моделей: {total_models}"))

"""
Загрузка городов РФ из JSON или с GitHub (russian-cities) с транслитерацией.
Использование:
  python manage.py load_cities
  python manage.py load_cities --file core/data/cities.json
  python manage.py load_cities --from-github  # все города с транслитерацией name_en/slug
"""
import json
import re
from pathlib import Path

import requests
from django.core.management.base import BaseCommand
from transliterate import translit

from core.models import City


def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s)
    return s[:100] or "city"


class Command(BaseCommand):
    help = "Загрузить города РФ (из JSON или с GitHub с транслитерацией)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default=None,
            help="Путь к JSON: [{\"name_ru\": \"...\", \"name_en\": \"...\", \"slug\": \"...\"}]",
        )
        parser.add_argument(
            "--from-github",
            action="store_true",
            help="Скачать russian-cities.json с GitHub и создать города с транслитерацией",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Не сохранять в БД, только вывести что будет загружено",
        )

    def handle(self, *args, **options):
        if options["from_github"]:
            self._load_from_github(dry_run=options["dry_run"])
        else:
            path = options["file"] or (Path(__file__).resolve().parent.parent.parent / "data" / "cities.json")
            self._load_from_file(path, dry_run=options["dry_run"])

    def _load_from_file(self, path, dry_run=False):
        path = Path(path)
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"Файл не найден: {path}"))
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        created = 0
        for item in data:
            name_ru = (item.get("name_ru") or item.get("name", "")).strip()
            name_en = (item.get("name_en") or "").strip()
            slug = (item.get("slug") or "").strip()
            if not name_ru:
                continue
            if not name_en:
                try:
                    name_en = translit(name_ru, "ru", reversed=True)
                except Exception:
                    name_en = name_ru
            if not slug:
                slug = slugify(name_en)
            slug = slug[:100]
            if dry_run:
                self.stdout.write(f"  {name_ru} | {name_en} | {slug}")
                created += 1
                continue
            _, was_created = City.objects.get_or_create(
                slug=slug,
                defaults={"name_ru": name_ru, "name_en": name_en},
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Загружено городов: {created}"))

    def _load_from_github(self, dry_run=False):
        url = "https://raw.githubusercontent.com/pensnarik/russian-cities/master/russian-cities.json"
        self.stdout.write(f"Загрузка {url}...")
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Ошибка загрузки: {e}"))
            return
        seen_slugs = set()
        created = 0
        for item in data:
            name_ru = (item.get("name") or "").strip()
            if not name_ru:
                continue
            try:
                name_en = translit(name_ru, "ru", reversed=True)
            except Exception:
                name_en = name_ru
            slug = slugify(name_en)
            if slug in seen_slugs:
                slug = f"{slug}-{created}"
            seen_slugs.add(slug)
            slug = slug[:100]
            if dry_run:
                self.stdout.write(f"  {name_ru} | {name_en} | {slug}")
                created += 1
                continue
            _, was_created = City.objects.get_or_create(
                slug=slug,
                defaults={"name_ru": name_ru, "name_en": name_en},
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Загружено городов: {created}"))

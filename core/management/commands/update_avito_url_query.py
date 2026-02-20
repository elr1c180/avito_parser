"""
Заменить query-часть (?...) во всех сохранённых avito_url у марок на:
  ?cd=1&localPriority=0&radius=200&s=104&searchRadius=200

Запуск:
  python manage.py update_avito_url_query
  python manage.py update_avito_url_query --dry-run
"""
from urllib.parse import urlencode, urlparse, urlunparse

from django.core.management.base import BaseCommand

from core.models import Brand

TARGET_PARAMS = {"cd": "1", "localPriority": "0", "radius": "200", "s": "104", "searchRadius": "200"}
TARGET_QUERY = urlencode(TARGET_PARAMS, doseq=True)


class Command(BaseCommand):
    help = "Заменить query во всех avito_url на cd=1&localPriority=0&radius=200&s=104&searchRadius=200"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Не сохранять в БД, только вывести изменения",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        updated = 0
        skipped = 0
        for brand in Brand.objects.exclude(avito_url__isnull=True).exclude(avito_url=""):
            url = (brand.avito_url or "").strip()
            if not url.startswith("http"):
                skipped += 1
                continue
            parsed = urlparse(url)
            new_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                TARGET_QUERY,
                parsed.fragment,
            ))
            if url == new_url:
                skipped += 1
                continue
            if dry_run:
                self.stdout.write(f"  {brand.name}:")
                self.stdout.write(f"    было:  {url}")
                self.stdout.write(f"    станет: {new_url}")
            else:
                brand.avito_url = new_url
                brand.save(update_fields=["avito_url"])
            updated += 1
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Dry-run: обновлено бы {updated} ссылок, без изменений/пропущено: {skipped}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Обновлено: {updated}, без изменений/пропущено: {skipped}"))

"""
Проставить у каждой марки ссылку поиска Avito в формате:
  https://www.avito.ru/moskva/avtomobili/{slug}-ASgBAgICAUTgtg3GmSg?cd=1&localPriority=0&radius=200&s=104&searchRadius=200
Один суффикс для всех марок (из примера объявления). Меняется только slug марки перед дефисом.
При поиске город (moskva) подменяется на город пользователя в bot/services.

Запуск:
  python manage.py set_brand_avito_search_urls
  python manage.py set_brand_avito_search_urls --dry-run
"""
from django.core.management.base import BaseCommand

from core.models import Brand

AVITO_BASE = "https://www.avito.ru"
CITY_PLACEHOLDER = "moskva"
SEGMENT = "avtomobili"
QUERY = "cd=1&localPriority=0&radius=200&s=104&searchRadius=200"
# Один суффикс из примера объявления для раздела avtomobili
AVITO_SUFFIX = "ASgBAgICAUTgtg3GmSg"


class Command(BaseCommand):
    help = "Проставить avito_url у марок: avito.ru/moskva/avtomobili/{slug}-{suffix}?…"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Не сохранять в БД, только вывести ссылки",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        updated = 0
        skipped = 0
        for brand in Brand.objects.all().order_by("name"):
            slug = (brand.slug or "").strip()
            if not slug:
                self.stdout.write(self.style.WARNING(f"  {brand.name}: нет slug, пропуск"))
                skipped += 1
                continue
            path = f"{CITY_PLACEHOLDER}/{SEGMENT}/{slug}-{AVITO_SUFFIX}"
            url = f"{AVITO_BASE}/{path}?{QUERY}"
            if not dry_run:
                if brand.avito_url != url:
                    brand.avito_url = url
                    brand.save(update_fields=["avito_url"])
                    updated += 1
            self.stdout.write(f"  {brand.name}: {url[:70]}…")
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Dry-run: показаны ссылки для {updated + skipped} марок"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Обновлено: {updated}, пропущено (нет slug): {skipped}"))

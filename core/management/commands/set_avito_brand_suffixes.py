"""
Проставить суффиксы Avito для марок (чтобы URL совпадал с Avito).
Запуск: python manage.py set_avito_brand_suffixes
Суффиксы взяты из реальных ссылок avito.ru/.../avtomobili/{марка}/{модель}-SUFFIX
"""
from django.core.management.base import BaseCommand

from core.models import Brand

# Марка -> суффикс из URL Авито (из ссылки на раздел авто этой марки)
BRAND_AVITO_SUFFIXES = {
    "Audi": "ASgBAgICAkTgtg3elyjitg3inSg",
    "Mercedes-Benz": "ASgBAgICAkTgtg3omCjitg2enyg",
}


class Command(BaseCommand):
    help = "Проставить avito_suffix у марок (Audi, Mercedes-Benz и др.) для правильных ссылок"

    def handle(self, *args, **options):
        updated = 0
        for name, suffix in BRAND_AVITO_SUFFIXES.items():
            try:
                brand = Brand.objects.get(name=name)
                if brand.avito_suffix != suffix:
                    brand.avito_suffix = suffix
                    brand.save(update_fields=["avito_suffix"])
                    updated += 1
                    self.stdout.write(f"  {name}: avito_suffix = {suffix[:20]}…")
            except Brand.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  Марка «{name}» не найдена в БД"))
        self.stdout.write(self.style.SUCCESS(f"Обновлено марок: {updated}"))

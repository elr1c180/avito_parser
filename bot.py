"""
Точка входа: запуск Telegram-бота.
Конфигурация — только из config.toml (секции [bot], [avito], [django]).
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from bot.app import main

if __name__ == "__main__":
    main()

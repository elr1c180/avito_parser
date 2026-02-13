# Avito Parser

## Установка

```bash
pip install -r requirements.txt
```

## Настройка

1. Скопируй `.env.example` в `.env`
2. Укажи `TELEGRAM_BOT_TOKEN` — токен бота от @BotFather

## Django админ-панель

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Админка: http://127.0.0.1:8000/admin/

10 марок уже созданы: Mercedes, BMW, Toyota, Lada/VAZ, Lexus, Li Xiang, Geely, Changan, Hyundai, Nissan.

Пользователей Telegram создаёшь в админке (раздел «Пользователи Telegram») — укажи пароль, username и chat_id опциональны. При первом входе в бота пользователь введёт пароль, после чего бот сохранит его chat_id и username.

## Бот

```bash
python bot.py
```

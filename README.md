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

## Сервер (PM2)

На сервере с Node.js и PM2:

1. `pip install -r requirements.txt`
2. `python manage.py migrate`
3. `python manage.py createsuperuser`
4. `python manage.py collectstatic --noinput`
5. Создай `.env` с `TELEGRAM_BOT_TOKEN`, `DJANGO_SECRET_KEY`, опционально `ALLOWED_HOSTS=IP_СЕРВЕРА,localhost`
6. Запуск: `pm2 start ecosystem.config.cjs`
7. Сохранить при перезагрузке: `pm2 save && pm2 startup`

Админка: `http://IP_СЕРВЕРА:8000/admin/`

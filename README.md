# Avito Parser Bot

Бот для подбора автомобилей с Авито: пользователь выбирает марки и порог цены, получает свежие объявления. Рассылка новых объявлений — каждые 15 минут.

## Конфигурация (один файл)

Вся настройка — в **`config.toml`** в корне проекта. Файлов `.env` нет.

```toml
[bot]
token = "ТОКЕН_ОТ_BOTFATHER"
# telegram_proxy = "http://user:pass@host:port"   # если api.telegram.org заблокирован

[avito]
proxy_string = "login:password@host:port"
proxy_change_url = "https://..."   # для мобильного прокси (смена IP)
# use_playwright = true   # на сервере при 403: запросы через браузер (как в parser_avito)

[django]
secret_key = "случайная-строка"
debug = true
allowed_hosts = ["*"]
```

Прокси для Avito обязателен для стабильного парсинга. При ошибках парсинга пользователю показывается только: «Требуется замена прокси».

## Установка

```bash
pip install -r requirements.txt
```

Если на сервере Avito отдаёт 403 даже с прокси, включите режим **Playwright** (реальный браузер, как в [parser_avito](https://github.com/Duff89/parser_avito)):

1. В `config.toml` в секции `[avito]` задайте `use_playwright = true`.
2. Установите браузер для Playwright:  
   `python -m playwright install chromium`
3. На Linux-сервере могут понадобиться зависимости:  
   `apt install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2`  
   (или используйте образ с Playwright, как в parser_avito).

## Админка Django

```bash
source venv/bin/activate
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Админка: http://127.0.0.1:8000/admin/

- В разделе **Марки** для каждой марки укажите **Ссылку поиска Avito** (готовая ссылка выдачи с сайта).
- Пользователей создаёте в **Пользователи Telegram** (пароль, при первом входе бот сохранит chat_id). Выбранные марки отображаются в списке.

## Запуск бота

```bash
source venv/bin/activate
python bot.py
```

- **/start** — вход по паролю, выбор марок, ввод порога цены, первый подбор.
- **/brands** — изменить выбор марок автомобилей (и при необходимости порог цены).
- Каждые **15 минут** бот парсит выдачи по маркам и отправляет **только новые** объявления тем, кто подписан на эту марку.

## Структура проекта

- `config.toml` — единственный конфиг (бот, прокси, Django).
- `app_config.py` — загрузка настроек из config.toml.
- `avito/` — минимальный парсер Avito (запросы, прокси, разбор выдачи).
- `core/` — Django-приложение (модели, админка, `avito_search`).
- `bot/` — логика бота (обработчики, рассылка, расписание).
- `bot.py` — точка входа (Django setup + запуск бота).

## Деплой на сервер (админка по IP, бот и парсинг круглосуточно)

Нужны: **Python 3.10+**, **Node.js** (для PM2). На сервере (VPS/домашний) выполните по шагам.

### 1. Код и зависимости

```bash
cd /путь/к/avito_parser
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Конфиг

Отредактируйте **`config.toml`**:

- **`[avito]`** — `tg_token`, `proxy_string`, `proxy_change_url` (и при необходимости `bot_password`).
- **`[django]`** — для доступа к админке по IP сервера:
  - `allowed_hosts = ["IP_ВАШЕГО_СЕРВЕРА"]` — например `["192.168.1.10"]` или `["1.2.3.4", "myserver.local"]`;
  - `secret_key` — замените на длинную случайную строку;
  - `debug = false` в продакшене.

### 3. БД и суперпользователь

```bash
source venv/bin/activate
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

`collectstatic` нужен, чтобы админка отдавала стили (CSS).

### 4. Запуск через PM2

```bash
npm install -g pm2
pm2 start ecosystem.config.cjs
```

Будут запущены:

- **avito-admin** — Django (gunicorn) на порту **8000**, привязка `0.0.0.0` (доступ снаружи по IP).
- **avito-bot** — Telegram-бот и фоновый парсинг каждые 15 минут.

Проверка: `pm2 status`, логи: `pm2 logs`.

### 5. Админка по IP

В браузере откройте: **`http://IP_СЕРВЕРА:8000/admin/`** (логин/пароль — от `createsuperuser`).

В админке: **Марки** — укажите ссылки поиска Avito; **Пользователи Telegram** — создайте пользователей, после входа в бота сохранится `chat_id`.

### 6. Автозапуск после перезагрузки

```bash
pm2 startup
# выполните команду, которую выведет pm2
pm2 save
```

Итог: админка доступна по IP:8000, бот и парсинг работают круглосуточно, пока запущен процесс PM2.

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core.models import Brand, CarModel, City

CITIES_PER_PAGE = 12
MODELS_PER_PAGE = 12


def get_cities_keyboard(page: int = 0, selected_ids: set = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора городов (мультивыбор, пагинация). selected_ids — set(id) выбранных."""
    selected_ids = selected_ids or set()
    qs = City.objects.all().order_by("name_ru")
    total = qs.count()
    if total == 0:
        return InlineKeyboardMarkup([[]])
    start = page * CITIES_PER_PAGE
    end = start + CITIES_PER_PAGE
    cities = list(qs[start:end])
    buttons = []
    row = []
    for c in cities:
        prefix = "✓ " if c.id in selected_ids else ""
        row.append(InlineKeyboardButton(f"{prefix}{c.name_ru}", callback_data=f"city_{c.id}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    total_pages = (total + CITIES_PER_PAGE - 1) // CITIES_PER_PAGE
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀ Назад", callback_data=f"city_page_{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Вперёд ▶", callback_data=f"city_page_{page + 1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("Готово", callback_data="city_done")])
    return InlineKeyboardMarkup(buttons)


def get_brands_keyboard(selected_ids: set) -> InlineKeyboardMarkup:
    brands = Brand.objects.all().order_by("name")
    buttons = []
    row = []
    for b in brands:
        prefix = "✓ " if b.id in selected_ids else ""
        row.append(InlineKeyboardButton(f"{prefix}{b.name}", callback_data=f"brand_{b.id}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("Готово", callback_data="brands_done")])
    return InlineKeyboardMarkup(buttons)


def get_models_keyboard(brand_ids: list, selected_ids: set, page: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура выбора моделей по выбранным маркам (с пагинацией)."""
    qs = CarModel.objects.filter(brand_id__in=brand_ids).select_related("brand").order_by("brand__name", "name")
    total = qs.count()
    if total == 0:
        buttons = [[InlineKeyboardButton("Готово (все модели)", callback_data="models_done")]]
        return InlineKeyboardMarkup(buttons)
    start = page * MODELS_PER_PAGE
    end = start + MODELS_PER_PAGE
    models = list(qs[start:end])
    buttons = []
    row = []
    for m in models:
        prefix = "✓ " if m.id in selected_ids else ""
        label = f"{prefix}{m.brand.name} {m.name}"[:40]
        row.append(InlineKeyboardButton(label, callback_data=f"model_{m.id}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    total_pages = (total + MODELS_PER_PAGE - 1) // MODELS_PER_PAGE
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀ Назад", callback_data=f"model_page_{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Вперёд ▶", callback_data=f"model_page_{page + 1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("Готово", callback_data="models_done")])
    return InlineKeyboardMarkup(buttons)

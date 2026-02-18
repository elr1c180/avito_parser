from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core.models import Brand


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

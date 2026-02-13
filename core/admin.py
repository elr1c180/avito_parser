from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Brand, TelegramUser


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name"]


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ["username", "chat_id", "password", "max_price"]
    list_filter = []
    search_fields = ["username", "chat_id"]
    ordering = ["id"]
    filter_horizontal = ["selected_brands"]

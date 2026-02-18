from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Brand, TelegramUser, SeenAd


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "avito_url"]
    search_fields = ["name", "avito_url"]


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ["username", "chat_id", "max_price", "selected_brands_display"]
    list_filter = []
    search_fields = ["username", "chat_id"]
    ordering = ["id"]
    filter_horizontal = ["selected_brands"]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("selected_brands")

    @admin.display(description="Выбранные марки")
    def selected_brands_display(self, obj):
        if obj.pk:
            names = [b.name for b in obj.selected_brands.all()]
            return ", ".join(names) if names else "—"
        return "—"


@admin.register(SeenAd)
class SeenAdAdmin(admin.ModelAdmin):
    list_display = ["user", "avito_id", "price", "created_at"]
    search_fields = ["avito_id", "user__username", "user__chat_id"]
    ordering = ["-created_at"]

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Brand, CarModel, City, SeenAd, TelegramUser


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ["name_ru", "name_en", "slug"]
    search_fields = ["name_ru", "name_en", "slug"]
    ordering = ["name_ru"]


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "avito_url", "avito_path"]
    search_fields = ["name", "slug", "avito_url", "avito_path"]
    list_filter = []


@admin.register(CarModel)
class CarModelAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "avito_suffix", "brand"]
    search_fields = ["name", "slug", "brand__name"]
    list_filter = ["brand"]
    ordering = ["brand__name", "name"]


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ["username", "chat_id", "city", "max_price", "selected_brands_display", "selected_models_display"]
    list_filter = []
    search_fields = ["username", "chat_id"]
    ordering = ["id"]
    filter_horizontal = ["selected_brands", "selected_models"]
    raw_id_fields = ["city"]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("selected_brands", "selected_models", "city")

    @admin.display(description="Выбранные марки")
    def selected_brands_display(self, obj):
        if obj.pk:
            names = [b.name for b in obj.selected_brands.all()]
            return ", ".join(names) if names else "—"
        return "—"

    @admin.display(description="Выбранные модели")
    def selected_models_display(self, obj):
        if obj.pk:
            names = [f"{m.brand.name} {m.name}" for m in obj.selected_models.select_related("brand").all()[:10]]
            return ", ".join(names) + ("…" if obj.selected_models.count() > 10 else "") if names else "—"
        return "—"


@admin.register(SeenAd)
class SeenAdAdmin(admin.ModelAdmin):
    list_display = ["user", "avito_id", "price", "created_at"]
    search_fields = ["avito_id", "user__username", "user__chat_id"]
    ordering = ["-created_at"]

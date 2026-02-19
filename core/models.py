from django.db import models


class City(models.Model):
    """Город РФ: название на русском (для пользователя) и на английском (и slug для URL Avito)."""
    name_ru = models.CharField("Город (рус.)", max_length=150)
    name_en = models.CharField("Город (англ.)", max_length=150)
    slug = models.SlugField("Slug для Avito URL", max_length=100, unique=True)

    class Meta:
        verbose_name = "Город"
        verbose_name_plural = "Города"
        ordering = ["name_ru"]

    def __str__(self):
        return f"{self.name_ru} ({self.name_en})"


class Brand(models.Model):
    name = models.CharField("Название", max_length=100, unique=True)
    slug = models.SlugField(
        "Slug для Avito (латиница, напр. bmw, audi)",
        max_length=80,
        blank=True,
        help_text="Подставляется в URL: avito.ru/{город}/avtomobili/{slug}/…",
    )
    avito_suffix = models.CharField(
        "Суффикс Avito для моделей (если у марки свой)",
        max_length=80,
        blank=True,
        help_text="Напр. ASgBAgICAkTgtg3elyjitg3inSg для Audi; пусто — общий суффикс",
    )
    avito_url = models.URLField("Ссылка поиска Avito (полная)", blank=True, null=True)
    avito_path = models.CharField(
        "Путь Avito без города (напр. avtomobili)",
        max_length=255,
        blank=True,
        help_text="Используется с выбранным городом: avito.ru/{slug}/{path}",
    )

    class Meta:
        verbose_name = "Марка"
        verbose_name_plural = "Марки"

    def __str__(self):
        return self.name


class CarModel(models.Model):
    """Модель автомобиля, привязанная к марке."""
    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name="car_models",
        verbose_name="Марка",
    )
    name = models.CharField("Модель", max_length=120)
    slug = models.SlugField(
        "Slug для Avito (латиница, напр. m4, a-klass)",
        max_length=80,
        blank=True,
        help_text="Подставляется в URL: avito.ru/…/avtomobili/{марка_slug}/{slug}",
    )
    avito_suffix = models.CharField(
        "Суффикс Avito (если свой у модели)",
        max_length=80,
        blank=True,
        help_text="Напр. ASgBAgICAkTgtg3omCjitg2enyg для Mercedes; пусто — общий суффикс",
    )

    class Meta:
        verbose_name = "Модель авто"
        verbose_name_plural = "Модели авто"
        ordering = ["brand__name", "name"]
        unique_together = [["brand", "name"]]

    def __str__(self):
        return f"{self.brand.name} {self.name}"


class TelegramUser(models.Model):
    username = models.CharField("Username", max_length=100, blank=True, null=True)
    chat_id = models.BigIntegerField("Chat ID", blank=True, null=True, unique=True)
    password = models.CharField("Пароль", max_length=255)
    city = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Город",
    )
    selected_brands = models.ManyToManyField(Brand, blank=True, verbose_name="Выбранные марки")
    selected_models = models.ManyToManyField(
        "CarModel", blank=True, verbose_name="Выбранные модели", related_name="users"
    )
    max_price = models.PositiveIntegerField("Порог цены", null=True, blank=True)

    class Meta:
        verbose_name = "Пользователь Telegram"
        verbose_name_plural = "Пользователи Telegram"

    def __str__(self):
        return self.username or str(self.chat_id) or str(self.pk)


class SeenAd(models.Model):
    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name="seen_ads",
        verbose_name="Пользователь Telegram",
    )
    avito_id = models.BigIntegerField("ID объявления Avito")
    price = models.PositiveIntegerField("Цена (на момент отправки)", null=True, blank=True)
    created_at = models.DateTimeField("Когда отправили", auto_now_add=True)

    class Meta:
        verbose_name = "Отправленное объявление"
        verbose_name_plural = "Отправленные объявления"
        constraints = [
            models.UniqueConstraint(fields=["user", "avito_id"], name="uniq_seenad_user_avito_id")
        ]

    def __str__(self):
        return f"{self.user_id}:{self.avito_id}"

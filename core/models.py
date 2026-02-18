from django.db import models


class Brand(models.Model):
    name = models.CharField("Название", max_length=100, unique=True)
    avito_url = models.URLField("Ссылка поиска Avito", blank=True, null=True)

    class Meta:
        verbose_name = "Марка"
        verbose_name_plural = "Марки"

    def __str__(self):
        return self.name


class TelegramUser(models.Model):
    username = models.CharField("Username", max_length=100, blank=True, null=True)
    chat_id = models.BigIntegerField("Chat ID", blank=True, null=True, unique=True)
    password = models.CharField("Пароль", max_length=255)
    selected_brands = models.ManyToManyField(Brand, blank=True, verbose_name="Выбранные марки")
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

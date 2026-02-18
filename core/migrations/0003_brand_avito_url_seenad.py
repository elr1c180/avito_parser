from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_telegramuser_max_price_telegramuser_selected_brands"),
    ]

    operations = [
        migrations.AddField(
            model_name="brand",
            name="avito_url",
            field=models.URLField(blank=True, null=True, verbose_name="Ссылка поиска Avito"),
        ),
        migrations.CreateModel(
            name="SeenAd",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("avito_id", models.BigIntegerField(verbose_name="ID объявления Avito")),
                ("price", models.PositiveIntegerField(blank=True, null=True, verbose_name="Цена (на момент отправки)")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Когда отправили")),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="seen_ads",
                        to="core.telegramuser",
                        verbose_name="Пользователь Telegram",
                    ),
                ),
            ],
            options={
                "verbose_name": "Отправленное объявление",
                "verbose_name_plural": "Отправленные объявления",
            },
        ),
        migrations.AddConstraint(
            model_name="seenad",
            constraint=models.UniqueConstraint(fields=("user", "avito_id"), name="uniq_seenad_user_avito_id"),
        ),
    ]


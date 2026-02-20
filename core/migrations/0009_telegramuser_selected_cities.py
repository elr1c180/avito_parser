# Generated migration for selected_cities

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_brand_avito_suffix"),
    ]

    operations = [
        migrations.AddField(
            model_name="telegramuser",
            name="selected_cities",
            field=models.ManyToManyField(
                blank=True,
                related_name="users_by_selected_cities",
                to="core.city",
                verbose_name="Выбранные города (поиск по всем)",
            ),
        ),
    ]

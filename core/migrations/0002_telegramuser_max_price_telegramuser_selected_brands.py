from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]
    operations = [
        migrations.AddField(
            model_name="telegramuser",
            name="max_price",
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name="Порог цены"),
        ),
        migrations.AddField(
            model_name="telegramuser",
            name="selected_brands",
            field=models.ManyToManyField(blank=True, to="core.brand", verbose_name="Выбранные марки"),
        ),
    ]

from django.db import migrations, models


def create_brands(apps, schema_editor):
    Brand = apps.get_model("core", "Brand")
    brands = [
        "Mercedes",
        "BMW",
        "Toyota",
        "Lada/VAZ",
        "Lexus",
        "Li Xiang",
        "Geely",
        "Changan",
        "Hyundai",
        "Nissan",
    ]
    for name in brands:
        Brand.objects.get_or_create(name=name)


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Brand",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True, verbose_name="Название")),
            ],
            options={"verbose_name": "Марка", "verbose_name_plural": "Марки"},
        ),
        migrations.CreateModel(
            name="TelegramUser",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("username", models.CharField(blank=True, max_length=100, null=True, verbose_name="Username")),
                ("chat_id", models.BigIntegerField(blank=True, null=True, unique=True, verbose_name="Chat ID")),
                ("password", models.CharField(max_length=255, verbose_name="Пароль")),
            ],
            options={"verbose_name": "Пользователь Telegram", "verbose_name_plural": "Пользователи Telegram"},
        ),
        migrations.RunPython(create_brands),
    ]

# Generated by Django 5.1.3 on 2024-11-12 10:37

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("photobooth", "0002_photo_photo_with_bg"),
    ]

    operations = [
        migrations.AddField(
            model_name="photo",
            name="datetime_str",
            field=models.CharField(blank=True, max_length=20),
        ),
    ]

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("photobooth", "0003_photo_datetime_str"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="photo",
            name="email",
        ),
        migrations.RemoveField(
            model_name="photo",
            name="email_sent_at",
        ),
    ]

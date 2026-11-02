from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("photobooth", "0004_remove_photo_email"),
    ]

    operations = [
        migrations.AddField(
            model_name="photo",
            name="published_at",
            field=models.DateTimeField(null=True),
        ),
    ]

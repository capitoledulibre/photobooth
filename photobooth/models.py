import uuid

from django.db import models
from django.utils import timezone


class Photo(models.Model):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )

    email = models.EmailField()
    photo = models.ImageField()
    created_at = models.DateTimeField(default=timezone.now)
    email_sent_at = models.DateTimeField(null=True)

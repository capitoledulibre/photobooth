import uuid

from django.db import models
from django.utils import timezone


class Photo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    photo = models.ImageField()
    photo_with_bg = models.ImageField(blank=True)
    datetime_str = models.CharField(blank=True, max_length=20)
    created_at = models.DateTimeField(default=timezone.now)

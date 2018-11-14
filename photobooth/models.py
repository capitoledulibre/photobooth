from django.db import models
from django.utils import timezone


class Photo(models.Model):

    email = models.EmailField()
    photo = models.ImageField()
    created_at = models.DateTimeField(default=timezone.now)
    email_sent_at = models.DateTimeField(null=True)

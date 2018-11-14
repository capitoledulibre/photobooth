from django.db import models


class Photo(models.Model):

    email = models.EmailField()
    photo = models.ImageField()

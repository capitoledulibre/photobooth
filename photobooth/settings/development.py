# flake8: noqa
# pylint: disable-all
from photobooth.settings.base import *

DEBUG = True

CELERY_TASK_ALWAYS_EAGER = True

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'localhost'
EMAIL_PORT = 1025

# flake8: noqa
# pylint: disable-all
from photobooth.settings.base import *

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'photobooth',
        'USER': 'photobooth_user',
        'PASSWORD': os.environ.get("DJANGO_DATABASE_PASSWORD", 'password'),
        'HOST': 'mysql',
    }
}

CELERY_BROKER_URL = 'amqp://rabbitmq'

PHOTOBOOTH_BASE_URL = 'https://2018.capitoledulibre.org/photobooth/'
PHOTOBOOTH_RSYNC_COMMAND = 'echo rsync -avz -e ssh ./media/ localhost:/tmp/www/'

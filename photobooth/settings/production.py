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

PHOTOBOOTH_BASE_URL = 'https://photo.capitoledulibre.org/'
PHOTOBOOTH_RSYNC_COMMAND = 'rsync -avz -e "ssh -i /home/daemon/.ssh/id_rsa -oStrictHostKeyChecking=accept-new" media/ photobooth@photo.capitoledulibre.org:/srv/photo/'

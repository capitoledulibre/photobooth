# flake8: noqa
# pylint: disable-all
from photobooth.settings.base import *

CELERY_BROKER_URL = ''

PHOTOBOOTH_BASE_URL = 'https://2018.capitoledulibre.org/photobooth/'
PHOTOBOOTH_RSYNC_COMMAND = 'echo rsync -avz -e ssh ./media/ localhost:/tmp/www/'

# Create your tasks here
from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.conf import settings

import subprocess


@shared_task
def rsync_photo():
    subprocess.check_call(
        ['flock', '/tmp/photobooth.lock', '-c', settings.PHOTOBOOTH_RSYNC_COMMAND]
    )

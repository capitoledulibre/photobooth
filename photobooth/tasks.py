# Create your tasks here
import subprocess

from celery import shared_task
from django.conf import settings


@shared_task
def rsync_photo():
    subprocess.check_call(
        ["flock", "/tmp/photobooth.lock", "-c", settings.PHOTOBOOTH_RSYNC_COMMAND]
    )

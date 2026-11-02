import fcntl
import subprocess

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from photobooth.models import Photo

LOCK_FILE = "/tmp/photobooth.lock"


@shared_task
def rsync_photo():
    """
    Pushes the whole media directory to the download server.

    Every photo created before the rsync started is on disk, so it is
    online once the command succeeds. A failed run leaves photos
    unpublished; the next successful run publishes them.
    """
    with open(LOCK_FILE, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        started_at = timezone.now()
        subprocess.check_call(settings.PHOTOBOOTH_RSYNC_COMMAND, shell=True)

    Photo.objects.filter(created_at__lte=started_at, published_at__isnull=True).update(
        published_at=timezone.now()
    )

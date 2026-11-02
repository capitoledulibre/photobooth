import binascii
import io
import logging
import urllib.parse
import uuid

import qrcode
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

import photobooth.tasks
from photobooth.common import add_exif_data, duplicate_image_with_background
from photobooth.models import Photo

logger = logging.getLogger(__name__)


def home(request):
    return render(request, "photobooth/index.html")


@csrf_exempt
def photo(request):
    body = request.body.decode("utf-8")
    if not body.startswith("data:image/jpeg;base64"):
        logger.warning("Body data starts with: %r", body[:20])
        return HttpResponse(
            "Bad data-uri format",
            status=400,
            content_type="text/plain",
        )

    now = timezone.now().strftime("%Y-%m-%d-%H-%M-%S_")

    length = len("data:image/jpeg;base64")
    photo_data = binascii.a2b_base64(body[length:])
    photo_uuid = uuid.uuid4()
    photo_file = default_storage.save(
        f"{now}{photo_uuid!s}.jpg", ContentFile(photo_data)
    )

    add_exif_data(photo_uuid, now)
    photo_with_bg = duplicate_image_with_background(photo_uuid, now)

    photo = Photo.objects.create(
        id=photo_uuid,
        photo=photo_file,
        photo_with_bg=photo_with_bg,
        datetime_str=now,
    )
    photobooth.tasks.rsync_photo.delay()
    return HttpResponse(
        str(photo.id),
        status=200,
        content_type="text/plain",
    )


@require_GET
def photo_status(request, photo_uuid):
    photo = get_object_or_404(Photo, id=photo_uuid)
    return JsonResponse({"published": photo.published_at is not None})


def _qrcode_response(file_name: str) -> HttpResponse:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    # Plain URL: phones only offer to open the link when nothing else is
    # in the payload.
    qr.add_data(urllib.parse.urljoin(settings.PHOTOBOOTH_BASE_URL, file_name))
    img = qr.make_image()

    buffer = io.BytesIO()
    img.save(buffer)

    return HttpResponse(buffer.getvalue(), status=200, content_type="image/png")


@require_GET
def qrcode_link(request, photo_uuid):
    photo = get_object_or_404(Photo, id=photo_uuid)
    return _qrcode_response(f"{photo.datetime_str}{photo.id!s}.jpg")


@require_GET
def qrcode_with_background_link(request, photo_uuid):
    photo = get_object_or_404(Photo, id=photo_uuid)
    return _qrcode_response(f"{photo.datetime_str}{photo.id!s}_background.jpg")


def img_result(request, photo_uuid):
    photo = get_object_or_404(Photo, id=photo_uuid)

    with open(photo.photo_with_bg.path, "rb") as image_file:
        img_data = image_file.read()

    return HttpResponse(
        img_data,
        status=200,
        content_type="image/jpeg",
    )

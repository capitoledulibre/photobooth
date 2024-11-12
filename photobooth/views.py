import io
import json
import binascii
import uuid
import urllib.parse

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import qrcode

from photobooth.common import add_exif_data, duplicate_image_with_background
from photobooth.models import Photo
import photobooth.tasks


def home(request):
    return render(request, "photobooth/index.html", {"settings": settings})


@csrf_exempt
def photo(request):
    body = request.body.decode("utf-8")
    if not body.startswith("data:image/jpeg;base64"):
        print("Body data starts with: %r" % body[:20])
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
        f"{now}{str(photo_uuid)}.jpg", ContentFile(photo_data)
    )

    add_exif_data(photo_uuid, now)
    photo_with_bg = duplicate_image_with_background(photo_uuid, now)

    photo = Photo.objects.create(
        id=photo_uuid,
        photo=photo_file,
        photo_with_bg=photo_with_bg,
        datetime_str=now,
    )
    if settings.PHOTOBOOTH_USE_QR_CODE:
        photobooth.tasks.rsync_photo.delay()
    return HttpResponse(
        str(photo.id),
        status=200,
        content_type="text/plain",
    )


def qrcode_link(request, photo_uuid):
    photo = get_object_or_404(Photo, id=photo_uuid)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(
        f"URL: {str(urllib.parse.urljoin(settings.PHOTOBOOTH_BASE_URL, f"{photo.datetime_str}{str(photo.id)}.jpg"))}"
    )
    img = qr.make_image()

    buffer = io.BytesIO()
    img.save(buffer)
    buffer.seek(0)

    return HttpResponse(
        buffer,
        status=200,
        content_type="image/png",
    )


def qrcode_with_background_link(request, photo_uuid):
    photo = get_object_or_404(Photo, id=photo_uuid)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(
        f"URL: {str(urllib.parse.urljoin(settings.PHOTOBOOTH_BASE_URL, f"{photo.datetime_str}{str(photo.id)}_background.jpg"))}"
    )
    img = qr.make_image()

    buffer = io.BytesIO()
    img.save(buffer)
    buffer.seek(0)

    return HttpResponse(
        buffer,
        status=200,
        content_type="image/png",
    )


def img_result(request, photo_uuid):
    photo = get_object_or_404(Photo, id=photo_uuid)

    img_data = open(photo.photo_with_bg.path, "rb").read()

    return HttpResponse(
        img_data,
        status=200,
        content_type="image/jpeg",
    )


@csrf_exempt
def email(request):
    body = json.loads(request.body)

    photo = get_object_or_404(Photo, id=body["uuid"])
    photo.email = body["email"]
    photo.save()

    msg = EmailMessage(
        "Photobooth Capitole du Libre",
        "Bonjour,\nMerci de votre passage au Capitole du Libre",
        settings.FROM_EMAIL,
        [photo.email],
    )
    with photo.photo.open() as fileobj:
        msg_img = fileobj.read()
        msg.attach("capitole-du-libre.jpeg", msg_img, "image/jpeg")
    msg.send()

    photo.email_sent_at = timezone.now()
    photo.save()

    return HttpResponse(
        "ok",
        status=200,
        content_type="text/plain",
    )

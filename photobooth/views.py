import io
import json
import binascii
import uuid
import urllib.parse

from exif import Image, DATETIME_STR_FORMAT, GpsAltitudeRef

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import qrcode

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

    length = len("data:image/jpeg;base64")
    photo_data = binascii.a2b_base64(body[length:])
    photo_uuid = uuid.uuid4()
    photo_file = default_storage.save("%s.jpg" % photo_uuid, ContentFile(photo_data))

    with open("media/" + str(photo_uuid) + ".jpg", "rb") as image_file:
        my_image = Image(image_file)

        my_image.datetime_original = timezone.localtime().strftime(DATETIME_STR_FORMAT)
        my_image.gps_latitude = (43.0, 36.0, 7.848)
        my_image.gps_latitude_ref = "N"
        my_image.gps_longitude = (1.0, 27.0, 16.83)
        my_image.gps_longitude_ref = "E"
        my_image.gps_altitude = 155
        my_image.gps_altitude_ref = GpsAltitudeRef.ABOVE_SEA_LEVEL

        with open("media/" + str(photo_uuid) + ".jpg", "wb") as new_my_image:
            new_my_image.write(my_image.get_file())

    photo = Photo.objects.create(
        id=photo_uuid,
        photo=photo_file,
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
        "URL: %s"
        % urllib.parse.urljoin(settings.PHOTOBOOTH_BASE_URL, "%s.jpg" % (photo.id,))
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

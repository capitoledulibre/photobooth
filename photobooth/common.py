import io
import os
import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils import timezone
from exif import DATETIME_STR_FORMAT, GpsAltitudeRef
from exif import Image as ImageExif
from PIL import Image


def _photo_path(photo_uuid: uuid.UUID, now: str) -> str:
    return os.path.join(settings.MEDIA_ROOT, f"{now}{photo_uuid!s}.jpg")


def add_exif_data(photo_uuid: uuid.UUID, now: str):
    """
    Adds date and time to an image.
    """

    with open(_photo_path(photo_uuid, now), "rb") as image_file:
        my_image = ImageExif(image_file)

        my_image.datetime_original = timezone.localtime().strftime(DATETIME_STR_FORMAT)
        my_image.gps_latitude = (43.0, 36.0, 7.848)
        my_image.gps_latitude_ref = "N"
        my_image.gps_longitude = (1.0, 27.0, 16.83)
        my_image.gps_longitude_ref = "E"
        my_image.gps_altitude = 155
        my_image.gps_altitude_ref = GpsAltitudeRef.ABOVE_SEA_LEVEL

        with open(_photo_path(photo_uuid, now), "wb") as new_my_image:
            new_my_image.write(my_image.get_file())


def duplicate_image_with_background(photo_uuid: uuid.UUID, now: str) -> str:
    # Duplicate image
    with Image.open(_photo_path(photo_uuid, now)) as img:
        # Add background
        background = Image.open(
            os.path.join(settings.STATIC_ROOT, "img", "photobooth-mask.png")
        )

        # Define the coordinates for pasting image 2 onto image 1
        x, y = 0, 0

        img.paste(
            background, (x, y), background
        )  # The third argument, background, is used to manage transparency.

        # Convert the PIL Image to a byte stream
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        img_bytes.seek(0)

        # Create an InMemoryUploadedFile object
        image_file = InMemoryUploadedFile(
            img_bytes,
            field_name="photo_with_bg",
            name=f"{now}{photo_uuid!s}_background.jpg",
            content_type="image/jpeg",
            size=len(img_bytes.getvalue()),
            charset=None,
        )

    return default_storage.save(f"{now}{photo_uuid!s}_background.jpg", image_file)

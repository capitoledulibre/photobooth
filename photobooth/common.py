import io
import os
import uuid

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from exif import DATETIME_STR_FORMAT, GpsAltitudeRef
from exif import Image as ImageExif
from PIL import Image

from photobooth.frame import build_frame, frame_text

# Quality used when re-encoding the photo with the frame.
JPEG_QUALITY = 92


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
    """
    Saves a copy of the photo with the event frame on top of it.
    """
    with Image.open(_photo_path(photo_uuid, now)) as img:
        frame = build_frame(img.width, img.height, frame_text())

        # The third argument uses the frame alpha channel for transparency.
        img.paste(frame, (0, 0), frame)

        save_kwargs = {"format": "JPEG", "quality": JPEG_QUALITY}
        if "exif" in img.info:
            save_kwargs["exif"] = img.info["exif"]

        img_bytes = io.BytesIO()
        img.save(img_bytes, **save_kwargs)

    return default_storage.save(
        f"{now}{photo_uuid!s}_background.jpg", ContentFile(img_bytes.getvalue())
    )

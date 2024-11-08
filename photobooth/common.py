import io
import uuid
from django.utils import timezone
from PIL import Image
from exif import Image as ImageExif
from exif import GpsAltitudeRef, DATETIME_STR_FORMAT
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import InMemoryUploadedFile


def add_exif_data(photo_uuid: uuid.UUID, now: str):
    """
    Adds date and time to an image.
    """

    with open(f"media/{now}{str(photo_uuid)}.jpg", "rb") as image_file:
        my_image = ImageExif(image_file)

        my_image.datetime_original = timezone.localtime().strftime(DATETIME_STR_FORMAT)
        my_image.gps_latitude = (43.0, 36.0, 7.848)
        my_image.gps_latitude_ref = "N"
        my_image.gps_longitude = (1.0, 27.0, 16.83)
        my_image.gps_longitude_ref = "E"
        my_image.gps_altitude = 155
        my_image.gps_altitude_ref = GpsAltitudeRef.ABOVE_SEA_LEVEL

        with open(f"media/{now}{str(photo_uuid)}.jpg", "wb") as new_my_image:
            new_my_image.write(my_image.get_file())


def duplicate_image_with_background(photo_uuid: uuid.UUID, now: str) -> str:
    # Duplicate image
    with Image.open(f"media/{now}{str(photo_uuid)}.jpg") as img:
        img.save(f"media/{now}{str(photo_uuid)}_background.jpg")

    # Add background
    my_image = Image.open(f"media/{now}{str(photo_uuid)}_background.jpg")
    background = Image.open("static/img/photobooth-mask.png")

    # Define the coordinates for pasting image 2 onto image 1
    x, y = 0, 0

    my_image.paste(
        background, (x, y), background
    )  # The third argument, background, is used to manage transparency.

    my_image.save(f"media/{now}{str(photo_uuid)}_background.jpg")

    with Image.open(f"media/{now}{str(photo_uuid)}_background.jpg") as img:
        # Convert the PIL Image to a byte stream
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        img_bytes.seek(0)

        # Create an InMemoryUploadedFile object
        image_file = InMemoryUploadedFile(
            img_bytes,
            field_name="photo_with_bg",
            name=f"{now}{str(photo_uuid)}_background.jpg",
            content_type="image/jpeg",
            size=len(img_bytes.getvalue()),
            charset=None,
        )

    return default_storage.save(f"{now}{str(photo_uuid)}_background.jpg", image_file)

import base64
import io
import json
import os
import shutil
import tempfile
import uuid
from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings
from exif import Image as ImageExif
from PIL import Image

from photobooth.models import Photo


def make_data_uri(width=640, height=360):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "blue").save(buffer, format="JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


class PhotoboothTestCase(TestCase):
    def setUp(self):
        # Write uploaded photos to a throw-away directory, never to media/.
        self.media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media_root)
        settings_override = override_settings(MEDIA_ROOT=self.media_root)
        settings_override.enable()
        self.addCleanup(settings_override.disable)

        # The rsync task shells out to flock/rsync; don't run it in tests.
        patcher = mock.patch("photobooth.tasks.rsync_photo.delay")
        self.rsync_delay = patcher.start()
        self.addCleanup(patcher.stop)

    def take_photo(self):
        response = self.client.post(
            "/photo/", data=make_data_uri(), content_type="text/plain"
        )
        self.assertEqual(response.status_code, 200)
        return Photo.objects.get(id=response.content.decode())

    def test_home(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Photobooth Capitole du Libre")

    def test_photo_rejects_invalid_body(self):
        response = self.client.post(
            "/photo/", data="not a data uri", content_type="text/plain"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Photo.objects.exists())

    def test_photo_is_stored_with_exif_and_background(self):
        photo = self.take_photo()

        self.assertTrue(os.path.exists(photo.photo.path))
        self.assertTrue(os.path.exists(photo.photo_with_bg.path))
        self.assertTrue(photo.photo.path.startswith(self.media_root))
        self.assertTrue(photo.photo_with_bg.path.startswith(self.media_root))

        with open(photo.photo.path, "rb") as fileobj:
            exif_image = ImageExif(fileobj)
        self.assertTrue(exif_image.has_exif)
        self.assertEqual(exif_image.gps_latitude_ref, "N")

        with Image.open(photo.photo_with_bg.path) as img:
            self.assertEqual(img.format, "JPEG")

        self.rsync_delay.assert_called_once_with()

    def test_qrcodes_and_result(self):
        photo = self.take_photo()

        for url in (f"/qrcode/{photo.id}/", f"/qrcode-background/{photo.id}/"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "image/png")

        response = self.client.get(f"/img-result/{photo.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")

    def test_unknown_photo_returns_404(self):
        unknown = uuid.uuid4()
        for url in (
            f"/qrcode/{unknown}/",
            f"/qrcode-background/{unknown}/",
            f"/img-result/{unknown}/",
        ):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_email(self):
        photo = self.take_photo()

        response = self.client.post(
            "/email/",
            data=json.dumps({"uuid": str(photo.id), "email": "visitor@example.org"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        photo.refresh_from_db()
        self.assertEqual(photo.email, "visitor@example.org")
        self.assertIsNotNone(photo.email_sent_at)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["visitor@example.org"])
        self.assertEqual(len(mail.outbox[0].attachments), 1)

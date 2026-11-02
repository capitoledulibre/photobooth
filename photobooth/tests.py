import base64
import io
import os
import shutil
import tempfile
import uuid
from unittest import mock

import qrcode
from django.test import TestCase, override_settings
from exif import Image as ImageExif
from PIL import Image

import photobooth.tasks
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

        # The rsync task shells out to rsync; don't run it from the views.
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

    def test_qrcodes_contain_plain_urls(self):
        photo = self.take_photo()
        base_name = f"https://photo.capitoledulibre.org/{photo.datetime_str}{photo.id}"

        real_add_data = qrcode.QRCode.add_data
        for url, expected in (
            (f"/qrcode/{photo.id}/", f"{base_name}.jpg"),
            (f"/qrcode-background/{photo.id}/", f"{base_name}_background.jpg"),
        ):
            with mock.patch.object(
                qrcode.QRCode, "add_data", autospec=True, side_effect=real_add_data
            ) as add_data:
                response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "image/png")
            add_data.assert_called_once_with(mock.ANY, expected)

    def test_img_result(self):
        photo = self.take_photo()
        response = self.client.get(f"/img-result/{photo.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")

    def test_status(self):
        photo = self.take_photo()
        url = f"/status/{photo.id}/"
        self.assertEqual(self.client.get(url).json(), {"published": False})

        with mock.patch("subprocess.check_call") as check_call:
            photobooth.tasks.rsync_photo()
        check_call.assert_called_once_with("echo rsync", shell=True)

        self.assertEqual(self.client.get(url).json(), {"published": True})

    def test_failed_rsync_does_not_publish(self):
        photo = self.take_photo()

        with (
            mock.patch("subprocess.check_call", side_effect=OSError("boom")),
            self.assertRaises(OSError),
        ):
            photobooth.tasks.rsync_photo()

        photo.refresh_from_db()
        self.assertIsNone(photo.published_at)

    def test_unknown_photo_returns_404(self):
        unknown = uuid.uuid4()
        for url in (
            f"/qrcode/{unknown}/",
            f"/qrcode-background/{unknown}/",
            f"/img-result/{unknown}/",
            f"/status/{unknown}/",
        ):
            self.assertEqual(self.client.get(url).status_code, 404, url)

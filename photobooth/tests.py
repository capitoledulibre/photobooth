import io
import shutil
import tempfile
import uuid
from datetime import date
from unittest import mock

import qrcode
from django.test import TestCase, override_settings
from exif import Image as ImageExif
from PIL import Image

import photobooth.tasks
from photobooth import frame
from photobooth.models import Photo


def make_jpeg(width=640, height=360):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "blue").save(buffer, format="JPEG")
    return buffer.getvalue()


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

    def take_photo(self, width=640, height=360):
        response = self.client.post(
            "/photo/", data=make_jpeg(width, height), content_type="image/jpeg"
        )
        self.assertEqual(response.status_code, 200)
        return Photo.objects.get(id=response.content.decode())

    def test_home(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Photobooth Capitole du Libre")

    def test_photo_rejects_invalid_body(self):
        response = self.client.post(
            "/photo/", data=b"not a jpeg", content_type="image/jpeg"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Photo.objects.exists())

    def test_photo_rejects_get(self):
        self.assertEqual(self.client.get("/photo/").status_code, 405)

    def test_photo_is_stored_with_exif_and_background(self):
        photo = self.take_photo()

        self.assertTrue(photo.photo.path.startswith(self.media_root))
        self.assertTrue(photo.photo_with_bg.path.startswith(self.media_root))

        for path in (photo.photo.path, photo.photo_with_bg.path):
            with open(path, "rb") as fileobj:
                exif_image = ImageExif(fileobj)
            self.assertTrue(exif_image.has_exif, path)
            self.assertEqual(exif_image.gps_latitude_ref, "N", path)

        self.assertIsNone(photo.published_at)
        self.rsync_delay.assert_called_once_with()

    def test_photo_with_frame(self):
        photo = self.take_photo(1920, 1080)

        with Image.open(photo.photo_with_bg.path) as img:
            self.assertEqual(img.format, "JPEG")
            self.assertEqual(img.size, (1920, 1080))
            rgb = img.convert("RGB")
            # Photo untouched at the top and in the middle.
            self.assertBlue(rgb.getpixel((960, 20)))
            self.assertBlue(rgb.getpixel((960, 540)))
            # Darkened by the gradient at the bottom.
            blue = rgb.getpixel((960, 1075))[2]
            self.assertLess(blue, 120)

    def assertBlue(self, pixel):
        red, green, blue = pixel
        self.assertLess(red, 20)
        self.assertLess(green, 20)
        self.assertGreater(blue, 235)

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
        self.assertTrue(b"".join(response.streaming_content).startswith(b"\xff\xd8"))

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


class FrameTestCase(TestCase):
    def test_overlay_scales_with_the_photo(self):
        for width, height in ((3840, 2160), (1920, 1080), (640, 360)):
            img = frame.build_frame(width, height, "2026")
            self.assertEqual(img.size, (width, height))
            self.assertEqual(img.mode, "RGBA")
            alpha = img.getchannel("A")
            # Transparent at the top and in the middle, shaded at the bottom.
            self.assertEqual(
                alpha.crop((0, 0, width, height // 2)).getextrema(), (0, 0)
            )
            self.assertGreater(alpha.getpixel((width // 2, height - 1)), 150)

    def test_logo_and_pill_are_drawn(self):
        img = frame.build_frame(1920, 1080, "2026").convert("RGB")
        bottom = img.crop((0, 1080 - 150, 1920, 1080))
        colors = {color for _, color in bottom.getcolors(1 << 20)}
        self.assertIn(frame.WHITE, colors)
        self.assertIn(frame.ORANGE, colors)

    def test_no_pill_without_text(self):
        img = frame.build_frame(1920, 1080, "").convert("RGB")
        colors = {color for _, color in img.getcolors(1 << 20)}
        self.assertIn(frame.WHITE, colors)
        self.assertNotIn(frame.ORANGE, colors)

    def test_long_text_does_not_overlap_the_logo(self):
        img = frame.build_frame(1920, 1080, "2026 · " + "capitoledulibre.org " * 4)
        alpha = frame._logo_alpha()[0]
        logo_width = round(alpha.width * frame.CAP_HEIGHT / frame._logo_alpha()[2])
        margin = frame.MARGIN
        # Between the logo and the pill there is only the gradient: no orange.
        gap = img.crop(
            (margin + logo_width + 2, 900, 2 * margin + logo_width - 2, 1080)
        )
        colors = {color[:3] for _, color in gap.getcolors(1 << 20)}
        self.assertNotIn(frame.ORANGE, colors)
        # And the pill is still there.
        colors = {color[:3] for _, color in img.getcolors(1 << 20)}
        self.assertIn(frame.ORANGE, colors)

    @override_settings(PHOTOBOOTH_FRAME_TEXT=None)
    def test_default_text_is_the_current_year(self):
        with mock.patch(
            "django.utils.timezone.localdate", return_value=date(2031, 11, 15)
        ):
            self.assertEqual(frame.frame_text(), "2031")

    @override_settings(PHOTOBOOTH_FRAME_TEXT="2026 · capitoledulibre.org")
    def test_text_can_be_overridden(self):
        self.assertEqual(frame.frame_text(), "2026 · capitoledulibre.org")

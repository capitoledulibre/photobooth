import io
import os
import shutil
import tempfile
import uuid
from datetime import date
from unittest import mock

import qrcode
from django.conf import settings
from django.test import TestCase, override_settings
from exif import Image as ImageExif
from PIL import Image

import photobooth.tasks
from photobooth import frame
from photobooth.apps import check_frame_settings
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


ORANGE = (208, 61, 0)
WHITE = (255, 255, 255)


def make_style(**kwargs):
    defaults = {
        "text": "2026",
        "color": ORANGE,
        "logo_path": os.path.join(
            settings.STATIC_ROOT, "img", "logo-capitoledulibre-horizontal.png"
        ),
        "logo_color": WHITE,
    }
    return frame.FrameStyle(**(defaults | kwargs))


def colors_of(img):
    return {color[:3] for _, color in img.convert("RGB").getcolors(1 << 22)}


class FrameTestCase(TestCase):
    def test_overlay_scales_with_the_photo(self):
        for width, height in ((3840, 2160), (1920, 1080), (640, 360)):
            img = frame.build_frame(width, height, make_style())
            self.assertEqual(img.size, (width, height))
            self.assertEqual(img.mode, "RGBA")
            alpha = img.getchannel("A")
            # Transparent at the top and in the middle, shaded at the bottom.
            self.assertEqual(
                alpha.crop((0, 0, width, height // 2)).getextrema(), (0, 0)
            )
            self.assertGreater(alpha.getpixel((width // 2, height - 1)), 150)

    def test_logo_and_pill_are_drawn(self):
        colors = colors_of(frame.build_frame(1920, 1080, make_style()))
        self.assertIn(WHITE, colors)
        self.assertIn(ORANGE, colors)

    def test_no_pill_without_text(self):
        colors = colors_of(frame.build_frame(1920, 1080, make_style(text="")))
        self.assertIn(WHITE, colors)
        self.assertNotIn(ORANGE, colors)

    def test_pill_color(self):
        blue = (44, 82, 130)
        colors = colors_of(frame.build_frame(1920, 1080, make_style(color=blue)))
        self.assertIn(blue, colors)
        self.assertNotIn(ORANGE, colors)

    def test_text_color_is_readable_on_the_pill(self):
        self.assertEqual(frame.text_color(ORANGE), WHITE)
        self.assertEqual(frame.text_color((246, 173, 85)), frame.DARK)
        self.assertEqual(frame.text_color(WHITE), frame.DARK)

    def test_logo_color(self):
        yellow = (246, 173, 85)
        colors = colors_of(
            frame.build_frame(1920, 1080, make_style(text="", logo_color=yellow))
        )
        self.assertIn(yellow, colors)
        self.assertNotIn(WHITE, colors)

    def test_logo_original_colors(self):
        # The default logo is orange: kept as is, without the white tint.
        colors = colors_of(
            frame.build_frame(1920, 1080, make_style(text="", logo_color=None))
        )
        self.assertIn(ORANGE, colors)
        self.assertNotIn(WHITE, colors)

    def test_custom_logo(self):
        # A square logo, wider than the default logo is high.
        logo_path = os.path.join(
            self.enterContext(tempfile.TemporaryDirectory()), "logo.png"
        )
        Image.new("RGBA", (100, 100), (10, 200, 30, 255)).save(logo_path)
        img = frame.build_frame(
            1920, 1080, make_style(text="", logo_path=logo_path, logo_color=None)
        )
        # 58x58 pixels in the bottom left corner, one margin from the edges.
        green = img.crop(
            (
                frame.MARGIN,
                1080 - frame.MARGIN - 58,
                frame.MARGIN + 58,
                1080 - frame.MARGIN,
            )
        )
        self.assertEqual(colors_of(green), {(10, 200, 30)})

    def test_long_text_does_not_overlap_the_logo(self):
        img = frame.build_frame(
            1920, 1080, make_style(text="2026 · " + "capitoledulibre.org " * 4)
        )
        logo = frame._load_logo(make_style().logo_path)
        logo_width = round(logo.width * frame.LOGO_HEIGHT / logo.height)
        margin = frame.MARGIN
        # Between the logo and the pill there is only the gradient: no orange.
        gap = img.crop(
            (margin + logo_width + 2, 900, 2 * margin + logo_width - 2, 1080)
        )
        self.assertNotIn(ORANGE, colors_of(gap))
        # And the pill is still there.
        self.assertIn(ORANGE, colors_of(img))


class FrameSettingsTestCase(TestCase):
    @override_settings(PHOTOBOOTH_FRAME_TEXT=None)
    def test_default_text_is_the_current_year(self):
        with mock.patch(
            "django.utils.timezone.localdate", return_value=date(2031, 11, 15)
        ):
            self.assertEqual(frame.current_style().text, "2031")

    @override_settings(
        PHOTOBOOTH_FRAME_TEXT="#CDL2026",
        PHOTOBOOTH_FRAME_COLOR="2c5282",
        PHOTOBOOTH_FRAME_LOGO_COLOR="",
    )
    def test_settings(self):
        style = frame.current_style()
        self.assertEqual(style.text, "#CDL2026")
        self.assertEqual(style.color, (44, 82, 130))
        self.assertIsNone(style.logo_color)

    def test_parse_color(self):
        self.assertEqual(frame.parse_color("#d03d00"), ORANGE)
        self.assertEqual(frame.parse_color("d03d00"), ORANGE)
        self.assertEqual(frame.parse_color("white"), WHITE)
        with self.assertRaises(ValueError):
            frame.parse_color("pinkish")

    def test_checks_pass_with_the_defaults(self):
        self.assertEqual(check_frame_settings(None), [])

    @override_settings(
        PHOTOBOOTH_FRAME_COLOR="pinkish", PHOTOBOOTH_FRAME_LOGO="/nonexistent.png"
    )
    def test_checks_report_invalid_settings(self):
        ids = [error.id for error in check_frame_settings(None)]
        self.assertEqual(ids, ["photobooth.E001", "photobooth.E002"])

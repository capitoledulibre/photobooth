"""
Generates the overlay drawn on top of the photos.

The overlay used to be a PNG frame redrawn every year to update the
edition year. It is now generated: a soft dark gradient at the bottom of
the photo, the event logo in white on the left and an orange pill with a
text (the current year by default) on the right. A new edition needs no
new artwork.

    +------------------------------------------------+
    |                                                |
    |                     photo                      |
    |                                                |
    |░░░░░░░░░░░░░░░░ gradient ░░░░░░░░░░░░░░░░░░░░░░|
    |▒▒ Capitole du Libre ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ (2026) ▒▒|
    +------------------------------------------------+

The logo comes from the capitoledulibre-branding repository. Pillow does not
read SVG, so the PNG is rendered from the SVG with:

    rsvg-convert -w 3000 static/img/logo-capitoledulibre-horizontal.svg \\
        -o static/img/logo-capitoledulibre-horizontal.png
"""

import functools
import os

from django.conf import settings
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

ORANGE = (208, 61, 0)  # Capitole du Libre orange, #d03d00
WHITE = (255, 255, 255)

# Geometry in pixels for a 1080 pixels high photo, scaled to the photo height.
REFERENCE_HEIGHT = 1080
GRADIENT_HEIGHT = 324
GRADIENT_MAX_OPACITY = 190
# >1 keeps the top of the gradient almost transparent, so it fades in softly.
GRADIENT_CURVE = 1.6
MARGIN = 56
# Height of the logo capital letters; the pill text uses the same height.
CAP_HEIGHT = 44
PILL_PADDING_X = 22
PILL_PADDING_Y = 14


def _static_path(*parts: str) -> str:
    return os.path.join(settings.STATIC_ROOT, *parts)


def frame_text() -> str:
    text = settings.PHOTOBOOTH_FRAME_TEXT
    if text is None:
        text = str(timezone.localdate().year)
    return text


@functools.cache
def _logo_alpha() -> tuple[Image.Image, int, int]:
    """
    Returns the logo alpha channel cropped to its content, and the top and
    height of its capital letters.
    """
    with Image.open(_static_path("img", "logo-capitoledulibre-horizontal.png")) as logo:
        alpha = logo.convert("RGBA").getchannel("A")
    alpha = alpha.crop(alpha.getbbox())
    # The first letter is a "C": its height is the capital height of the logo.
    _, top, _, bottom = alpha.crop((0, 0, alpha.width // 20, alpha.height)).getbbox()
    return alpha, top, bottom - top


def _white_logo(cap_height: int) -> tuple[Image.Image, int]:
    """
    Returns the logo in white, scaled so its capital letters are cap_height
    pixels high, and the offset of the top of the capitals in the image.
    """
    alpha, cap_top, logo_cap_height = _logo_alpha()
    scale = cap_height / logo_cap_height
    alpha = alpha.resize(
        (round(alpha.width * scale), round(alpha.height * scale)),
        Image.Resampling.LANCZOS,
    )
    logo = Image.new("RGBA", alpha.size, WHITE)
    logo.putalpha(alpha)
    return logo, round(cap_top * scale)


def _font(cap_height: int) -> ImageFont.FreeTypeFont:
    """Returns the Ubuntu Bold font sized so capitals are cap_height high."""
    path = _static_path("fonts", "Ubuntu-Bold.ttf")
    probe = ImageFont.truetype(path, 1000)
    _, top, _, bottom = probe.getbbox("H")
    return ImageFont.truetype(path, round(1000 * cap_height / (bottom - top)))


def _gradient(width: int, height: int) -> Image.Image:
    column = Image.new("L", (1, height))
    for y in range(height):
        progress = y / max(height - 1, 1)
        column.putpixel((0, y), round(GRADIENT_MAX_OPACITY * progress**GRADIENT_CURVE))
    shade = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    shade.putalpha(column.resize((width, height)))
    return shade


@functools.lru_cache(maxsize=8)
def build_frame(width: int, height: int, text: str) -> Image.Image:
    """
    Returns an RGBA overlay of the given size, transparent except for the
    bottom gradient, the logo and the text pill.
    """
    scale = height / REFERENCE_HEIGHT
    margin = round(MARGIN * scale)
    cap_height = round(CAP_HEIGHT * scale)

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gradient_height = round(GRADIENT_HEIGHT * scale)
    overlay.alpha_composite(
        _gradient(width, gradient_height), (0, height - gradient_height)
    )

    # Logo, bottom left: its baseline sits one margin above the bottom.
    logo, logo_cap_top = _white_logo(cap_height)
    cap_y = height - margin - cap_height
    overlay.alpha_composite(logo, (margin, cap_y - logo_cap_top))

    if not text:
        return overlay

    # Text pill, bottom right, vertically centered on the logo capitals.
    draw = ImageDraw.Draw(overlay)
    pad_x = round(PILL_PADDING_X * scale)
    pad_y = round(PILL_PADDING_Y * scale)
    available_width = width - 3 * margin - logo.width

    text_cap_height = cap_height
    for _ in range(3):
        font = _font(text_cap_height)
        left, _, right, _ = draw.textbbox((0, 0), text, font=font)
        pill_width = right - left + 2 * pad_x
        if pill_width <= available_width:
            break
        # Too long for the space left by the logo: shrink the text.
        text_cap_height = int(
            text_cap_height * (available_width - 2 * pad_x) / (right - left)
        )

    _, cap_top, _, cap_bottom = draw.textbbox((0, 0), "H", font=font)
    pill_height = cap_bottom - cap_top + 2 * pad_y
    pill_right = width - margin
    pill_top = cap_y + cap_height // 2 - pill_height // 2
    draw.rounded_rectangle(
        (pill_right - pill_width, pill_top, pill_right, pill_top + pill_height),
        radius=pill_height // 2,
        fill=ORANGE,
    )
    draw.text(
        (pill_right - pill_width + pad_x - left, pill_top + pad_y - cap_top),
        text,
        font=font,
        fill=WHITE,
    )
    return overlay

"""
Generates the overlay drawn on top of the photos.

The overlay used to be a PNG frame redrawn every year to update the
edition year. It is now generated: a soft dark gradient at the bottom of
the photo, a logo (white by default) on the left and a colored pill with a
text (the current year by default) on the right. A new edition needs no
new artwork.

The logo, its color, the pill color and the text are configurable, see the
PHOTOBOOTH_FRAME_* settings.

    +------------------------------------------------+
    |                                                |
    |                     photo                      |
    |                                                |
    |░░░░░░░░░░░░░░░░ gradient ░░░░░░░░░░░░░░░░░░░░░░|
    |▒▒ Capitole du Libre ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ (2026) ▒▒|
    +------------------------------------------------+

The default logo comes from the capitoledulibre-branding repository. Pillow
does not read SVG, so the PNG is rendered from the SVG with:

    rsvg-convert -w 3000 static/img/logo-capitoledulibre-horizontal.svg \\
        -o static/img/logo-capitoledulibre-horizontal.png
"""

import dataclasses
import functools
import os

from django.conf import settings
from django.utils import timezone
from PIL import Image, ImageColor, ImageDraw, ImageFont

RGB = tuple[int, int, int]

WHITE = (255, 255, 255)
DARK = (26, 54, 93)  # Brand deep blue, for text on light pill colors.

# Geometry in pixels for a 1080 pixels high photo, scaled to the photo height.
REFERENCE_HEIGHT = 1080
GRADIENT_HEIGHT = 324
GRADIENT_MAX_OPACITY = 190
# >1 keeps the top of the gradient almost transparent, so it fades in softly.
GRADIENT_CURVE = 1.6
MARGIN = 56
LOGO_HEIGHT = 58
# Height of the capital letters of the pill text.
TEXT_CAP_HEIGHT = 44
PILL_PADDING_X = 22
PILL_PADDING_Y = 14


@dataclasses.dataclass(frozen=True)
class FrameStyle:
    text: str
    color: RGB
    logo_path: str
    # None keeps the logo original colors.
    logo_color: RGB | None


def parse_color(value: str) -> RGB:
    """Parses "#d03d00", "d03d00" or a color name like "white"."""
    value = value.strip()
    if len(value) in (3, 6) and all(c in "0123456789abcdefABCDEF" for c in value):
        value = "#" + value
    return ImageColor.getrgb(value)[:3]


def current_style() -> FrameStyle:
    """Returns the overlay style from the settings."""
    text = settings.PHOTOBOOTH_FRAME_TEXT
    if text is None:
        text = str(timezone.localdate().year)
    logo_color = settings.PHOTOBOOTH_FRAME_LOGO_COLOR
    return FrameStyle(
        text=text,
        color=parse_color(settings.PHOTOBOOTH_FRAME_COLOR),
        logo_path=settings.PHOTOBOOTH_FRAME_LOGO,
        logo_color=parse_color(logo_color) if logo_color else None,
    )


def text_color(background: RGB) -> RGB:
    """Returns white or dark, whichever is more readable on background."""
    red, green, blue = background
    # Perceived brightness (ITU-R BT.601 luma).
    luma = 0.299 * red + 0.587 * green + 0.114 * blue
    return DARK if luma > 170 else WHITE


@functools.lru_cache(maxsize=4)
def _load_logo(path: str) -> Image.Image:
    """Returns the logo as RGBA, cropped to its visible content."""
    with Image.open(path) as logo:
        logo = logo.convert("RGBA")
    bbox = logo.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError(f"The logo {path} is fully transparent")
    return logo.crop(bbox)


def _logo(path: str, color: RGB | None, height: int) -> Image.Image:
    logo = _load_logo(path)
    logo = logo.resize(
        (max(1, round(logo.width * height / logo.height)), height),
        Image.Resampling.LANCZOS,
    )
    if color is not None:
        tinted = Image.new("RGBA", logo.size, color)
        tinted.putalpha(logo.getchannel("A"))
        logo = tinted
    return logo


def _font(cap_height: int) -> ImageFont.FreeTypeFont:
    """Returns the Ubuntu Bold font sized so capitals are cap_height high."""
    path = os.path.join(settings.STATIC_ROOT, "fonts", "Ubuntu-Bold.ttf")
    probe = ImageFont.truetype(path, 1000)
    _, top, _, bottom = probe.getbbox("H")
    return ImageFont.truetype(path, max(1, round(1000 * cap_height / (bottom - top))))


def _gradient(width: int, height: int) -> Image.Image:
    column = Image.new("L", (1, height))
    for y in range(height):
        progress = y / max(height - 1, 1)
        column.putpixel((0, y), round(GRADIENT_MAX_OPACITY * progress**GRADIENT_CURVE))
    shade = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    shade.putalpha(column.resize((width, height)))
    return shade


@functools.lru_cache(maxsize=8)
def build_frame(width: int, height: int, style: FrameStyle) -> Image.Image:
    """
    Returns an RGBA overlay of the given size, transparent except for the
    bottom gradient, the logo and the text pill.
    """
    scale = height / REFERENCE_HEIGHT
    margin = round(MARGIN * scale)

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gradient_height = round(GRADIENT_HEIGHT * scale)
    overlay.alpha_composite(
        _gradient(width, gradient_height), (0, height - gradient_height)
    )

    # Logo, bottom left. Never wider than half of the photo.
    logo = _logo(style.logo_path, style.logo_color, round(LOGO_HEIGHT * scale))
    if logo.width > width // 2:
        logo = _logo(
            style.logo_path,
            style.logo_color,
            max(1, logo.height * (width // 2) // logo.width),
        )
    logo_top = height - margin - logo.height
    overlay.alpha_composite(logo, (margin, logo_top))

    if not style.text:
        return overlay

    # Text pill, bottom right, vertically centered on the logo.
    draw = ImageDraw.Draw(overlay)
    pad_x = round(PILL_PADDING_X * scale)
    pad_y = round(PILL_PADDING_Y * scale)
    available_width = width - 3 * margin - logo.width

    cap_height = round(TEXT_CAP_HEIGHT * scale)
    for _ in range(3):
        font = _font(cap_height)
        left, _, right, _ = draw.textbbox((0, 0), style.text, font=font)
        pill_width = right - left + 2 * pad_x
        if pill_width <= available_width:
            break
        # Too long for the space left by the logo: shrink the text.
        cap_height = int(cap_height * (available_width - 2 * pad_x) / (right - left))

    _, cap_top, _, cap_bottom = draw.textbbox((0, 0), "H", font=font)
    pill_height = cap_bottom - cap_top + 2 * pad_y
    pill_right = width - margin
    pill_top = logo_top + logo.height // 2 - pill_height // 2
    draw.rounded_rectangle(
        (pill_right - pill_width, pill_top, pill_right, pill_top + pill_height),
        radius=pill_height // 2,
        fill=style.color,
    )
    draw.text(
        (pill_right - pill_width + pad_x - left, pill_top + pad_y - cap_top),
        style.text,
        font=font,
        fill=text_color(style.color),
    )
    return overlay

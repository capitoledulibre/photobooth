from django.apps import AppConfig
from django.conf import settings
from django.core import checks


class PhotoboothConfig(AppConfig):
    name = "photobooth"

    def ready(self):
        checks.register(check_frame_settings)


def check_frame_settings(app_configs, **kwargs):
    """
    Validates the PHOTOBOOTH_FRAME_* settings at startup (migrate and
    runserver run the checks), instead of failing on the first photo.
    """
    from photobooth.frame import _load_logo, parse_color

    errors = []
    for name in ("PHOTOBOOTH_FRAME_COLOR", "PHOTOBOOTH_FRAME_LOGO_COLOR"):
        value = getattr(settings, name)
        if name == "PHOTOBOOTH_FRAME_LOGO_COLOR" and not value:
            continue
        try:
            parse_color(value)
        except ValueError:
            errors.append(
                checks.Error(
                    f"{name}={value!r} is not a valid color.",
                    hint='Use a hex color like "#d03d00" or a color name.',
                    id="photobooth.E001",
                )
            )

    try:
        _load_logo(settings.PHOTOBOOTH_FRAME_LOGO)
    except (OSError, ValueError) as exc:
        errors.append(
            checks.Error(
                f"PHOTOBOOTH_FRAME_LOGO cannot be used: {exc}",
                hint="Use the path of a PNG file with a transparent background.",
                id="photobooth.E002",
            )
        )
    return errors

"""photobooth URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.urls import path
from django.views import static as views_static

import photobooth.views


urlpatterns = [
    path("", photobooth.views.home, name="home"),
    path("photo/", photobooth.views.photo, name="photo"),
    path("qrcode/<uuid:photo_uuid>/", photobooth.views.qrcode_link, name="qrcode"),
    path(
        "qrcode-background/<uuid:photo_uuid>/",
        photobooth.views.qrcode_with_background_link,
        name="qrcode-background",
    ),
    path("email/", photobooth.views.email, name="email"),
    path(
        "static/<path:path>",
        views_static.serve,
        {"document_root": settings.STATIC_ROOT},
    ),
]

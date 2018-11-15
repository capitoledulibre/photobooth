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
from django.contrib import admin
from django.conf import settings
from django.urls import path
from django.conf.urls import url
from django.views import static as views_static
from django.urls import re_path

import photobooth.views


urlpatterns = [
    url(r'^$', photobooth.views.home, name='home'),
    url(r'^photo/$', photobooth.views.photo, name='photo'),
    url(r'^qrcode/(?P<photo_uuid>[0-9A-Za-z_-]+)/$',
        photobooth.views.qrcode_link, name='qrcode'),
    url(r'^email/$', photobooth.views.email, name='email'),

    url(r'^static/(?P<path>.*)$', views_static.serve,
        {'document_root': settings.STATIC_ROOT}),
]

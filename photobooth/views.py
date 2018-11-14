import json
import binascii

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


from photobooth.models import Photo


def home(request):
    return render(request, 'photobooth/index.html')


@csrf_exempt
def photo(request):
    body = json.loads(request.body)
    if not body['data'].startswith('data:image/jpeg;base64'):
        print('Body data starts with: %r' % body['data'][:20])
        return HttpResponse(
            'Bad data-uri format',
            status=400,
            content_type='text/plain',
        )

    photo_data = binascii.a2b_base64(
        body['data'][len('data:image/jpeg;base64'):]
    )
    photo = Photo.objects.create(
        email=body['email'],
    )
    photo_file = default_storage.save(
        "%s.jpg" % photo.pk, ContentFile(photo_data)
    )
    photo.photo = photo_file
    photo.save()
    return HttpResponse(
        'ok',
        status=200,
        content_type='text/plain',
    )
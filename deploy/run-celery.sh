#!/bin/sh

set -ex

python3 manage.py migrate
exec celery -A photobooth worker -l info -c 1

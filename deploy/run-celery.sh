#!/bin/sh

set -ex

exec celery -A photobooth worker -l info -c 1

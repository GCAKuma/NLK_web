#!/bin/sh
# Web entrypoint: apply migrations and collect static, then run the given CMD.
set -e

echo "==> Applying database migrations"
python manage.py migrate --noinput

echo "==> Collecting static files"
python manage.py collectstatic --noinput

echo "==> Starting: $*"
exec "$@"

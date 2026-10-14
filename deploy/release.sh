#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
compose() { docker compose -f docker-compose.prod.yml --env-file .env.prod "$@"; }
compose build web
# Verify an off-site backup before modifying the hosted database.
sh deploy/backup.sh
compose run --rm --no-deps migrate python manage.py check --deploy
compose run --rm --no-deps migrate python manage.py migrate --noinput
compose run --rm --no-deps migrate python manage.py secure_application_tables
compose run --rm --no-deps web python manage.py collectstatic --noinput
compose up -d --wait --wait-timeout 120 redis web celery dispatcher
compose exec -T web python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready/', timeout=15)"
# Refresh nginx's upstream address after the web container is recreated.
if compose ps --status running --services | grep -qx nginx; then
    compose exec -T nginx nginx -t
    compose exec -T nginx nginx -s reload
fi
# HTTPS bootstrapping remains an explicit step on the first release.

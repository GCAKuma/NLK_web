#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T web python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready/', timeout=15)"
docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T web python manage.py notification_status

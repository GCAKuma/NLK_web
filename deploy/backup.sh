#!/bin/sh
# Back up the hosted database; the old local PostgreSQL service is no longer used.
set -eu
cd "$(dirname "$0")/.."
mkdir -p backups
chmod 700 backups
compose() { docker compose -f docker-compose.prod.yml --env-file .env.prod "$@"; }
compose run --rm backup
# pg_dump creates root-owned 0600 files. Only this read-only maintenance
# container uses root; the web server and workers remain unprivileged.
compose run --rm --no-deps --user 0:0 -v "$PWD/backups:/backups:ro" web python manage.py upload_backups
# Local retention applies only after an off-site upload succeeds.
find "$PWD/backups" -maxdepth 1 -type f -name 'nlk-*.dump' -mtime +14 -delete

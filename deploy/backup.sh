#!/usr/bin/env bash
# Nightly Postgres backup for the NLK production stack.
#
# Run this on the HOST (the VPS), not inside a container — it drives the
# `db` container from the outside via `docker compose exec`. Schedule it
# with cron, e.g.:
#   0 2 * * * /opt/nlk/deploy/backup.sh >> /var/log/nlk-backup.log 2>&1
set -euo pipefail

cd "$(dirname "$0")/.."   # repo root
COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.prod"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILE="$BACKUP_DIR/nlk_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"
$COMPOSE exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$FILE"
echo "Backup written: $FILE"

# Optional off-site copy to S3 / Cloudflare R2 / DO Spaces — set
# BACKUP_TO_S3=true and the AWS_* vars in .env.prod (same creds media
# storage uses). Requires the `aws` CLI on the host.
if [ "${BACKUP_TO_S3:-false}" = "true" ]; then
  # shellcheck disable=SC1091
  set -a; source .env.prod; set +a
  aws s3 cp "$FILE" "s3://${AWS_STORAGE_BUCKET_NAME}/db-backups/$(basename "$FILE")" \
    ${AWS_S3_ENDPOINT_URL:+--endpoint-url "$AWS_S3_ENDPOINT_URL"}
  echo "Uploaded to s3://${AWS_STORAGE_BUCKET_NAME}/db-backups/$(basename "$FILE")"
fi

# Keep 14 days of local backups; rely on the off-site copy beyond that.
find "$BACKUP_DIR" -name 'nlk_*.sql.gz' -mtime +14 -delete

#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm certbot renew --webroot -w /var/www/certbot --quiet
docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T nginx nginx -t
docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T nginx nginx -s reload

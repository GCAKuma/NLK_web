#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
domain=${1:?Usage: sh deploy/enable-https.sh example.com email@example.com}
email=${2:?Provide a certificate contact email}
# Validate before substituting into configuration or passing as a domain.
case "$domain" in *[!a-zA-Z0-9.-]*|.*|*..*|-*) echo "Invalid domain" >&2; exit 1;; esac
compose() { docker compose -f docker-compose.prod.yml --env-file .env.prod "$@"; }
if [ ! -f nginx/active.conf ]; then cp nginx/bootstrap.conf nginx/active.conf; fi
compose up -d nginx
compose run --rm certbot certonly --webroot -w /var/www/certbot --non-interactive --agree-tos --email "$email" -d "$domain"
sed "s/DOMAIN_NAME/$domain/g" nginx/https.conf.template > nginx/active.conf
compose exec -T nginx nginx -t
compose exec -T nginx nginx -s reload

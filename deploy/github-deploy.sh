#!/usr/bin/env bash
# Run by the dedicated EC2 runner, not by pull-request jobs.
set -euo pipefail

release_sha=${1:?A tested Git commit is required}
deploy_url=${2:?Set the EC2_TEST_URL repository variable}
branch=charith/aws-production
app_dir=/opt/nlk

[[ "$release_sha" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid release commit.' >&2; exit 1; }
[[ "$deploy_url" == https://* ]] || { echo 'EC2_TEST_URL must use HTTPS.' >&2; exit 1; }
cd "$app_dir"

# Protect against overlapping runs, including a runner restart during a release.
exec 9>.git/nlk-deploy.lock
flock -w 300 9 || { echo 'Another deployment holds the release lock.' >&2; exit 1; }

for config in .env.prod .env.migrate nginx/active.conf; do
    [[ -s "$config" ]] || {
        echo "Missing $config. Complete the initial server setup before enabling automatic deployment." >&2
        exit 1
    }
done

[[ "$(git branch --show-current)" == "$branch" ]] || {
    echo "The application checkout must be on $branch." >&2; exit 1;
}
[[ -z "$(git status --porcelain)" ]] || {
    echo 'The application checkout has local changes. Resolve them before deploying; nothing was overwritten.' >&2
    exit 1
}
docker info >/dev/null
compose() { docker compose -f docker-compose.prod.yml --env-file .env.prod "$@"; }
if ! compose ps --status running --services | grep -qx nginx; then
    echo 'Finish the first manual HTTPS deployment before enabling automatic deployment.' >&2
    exit 1
fi

# Use the existing read-only GitHub deploy key configured in this checkout.
export GIT_TERMINAL_PROMPT=0
git fetch --no-tags origin "refs/heads/$branch"
latest_sha=$(git rev-parse FETCH_HEAD)
if [[ "$latest_sha" != "$release_sha" ]]; then
    echo 'This run was superseded by a newer push. Waiting for that commit to pass its own tests.'
    exit 0
fi

previous_sha=$(git rev-parse HEAD)
git merge --ff-only "$release_sha"
[[ "$(git rev-parse HEAD)" == "$release_sha" ]] || { echo 'Release commit mismatch.' >&2; exit 1; }
echo "Deploying $release_sha (previous checkout: $previous_sha)."
sh deploy/release.sh
curl --fail --silent --show-error --max-time 20 "${deploy_url%/}/health/ready/"
echo
echo "Deployed and checked $release_sha."
# Do not automatically reverse database migrations when a release fails.

#!/bin/sh
# Runtime entrypoint. Release operations run explicitly with migration credentials.
set -e

echo "==> Starting: $*"
exec "$@"

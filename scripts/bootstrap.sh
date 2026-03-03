#!/usr/bin/env sh
set -e

if [ ! -d migrations ]; then
  flask db init
fi

flask db migrate -m "init schema" || true
flask db upgrade
flask seed

echo "Bootstrap completed"

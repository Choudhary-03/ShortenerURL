#!/bin/sh
set -e

# Only the web container sets RUN_MIGRATIONS=1, so the worker never races it.
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  if ! python manage.py makemigrations --check --dry-run >/dev/null 2>&1; then
    echo "ERROR: models have no matching migration files."
    echo "Run 'python manage.py makemigrations accounts shortener analytics' locally,"
    echo "commit the generated files, and rebuild the image."
    exit 1
  fi
  echo "Applying migrations..."
  python manage.py migrate --noinput
fi

exec "$@"

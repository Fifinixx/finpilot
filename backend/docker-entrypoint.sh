#!/bin/sh
# Container start-up: apply migrations, optionally seed, then hand over to the server.
# `set -e` means a failed migration stops the container before it serves traffic;
# PostgreSQL runs each migration in a transaction, so the schema is left unchanged.
set -e

echo "entrypoint: applying migrations"
python manage.py migrate --noinput

if [ "${SEED_ON_START:-true}" = "true" ]; then
    echo "entrypoint: seeding demo users and CSV data"
    python manage.py seed_demo_users
    # Safe to repeat: files that were already imported are skipped by hash.
    python manage.py import_data --dir "${DATA_DIR:-/data}"
fi

exec "$@"

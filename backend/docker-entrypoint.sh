#!/bin/sh
# Container start: prepare the uploads volume, apply migrations, then run the API as a non-root user.
set -e

run_as_app() {
    if [ "$(id -u)" = "0" ]; then
        exec setpriv --reuid=app --regid=app --init-groups "$@"
    fi
    exec "$@"
}

# A freshly mounted volume (e.g. Railway at /data) is owned by root; the API user must write to it.
if [ "$(id -u)" = "0" ]; then
    mkdir -p "${STORAGE_PATH:-/data/storage}"
    chown -R app "$(dirname "${STORAGE_PATH:-/data/storage}")"
fi

# One API instance: migrating on start keeps the schema in step with the code. Set
# RUN_MIGRATIONS=false if migrations are run some other way.
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Applying database migrations..."
    if [ "$(id -u)" = "0" ]; then
        setpriv --reuid=app --regid=app --init-groups alembic upgrade head
    else
        alembic upgrade head
    fi
fi

run_as_app "$@"

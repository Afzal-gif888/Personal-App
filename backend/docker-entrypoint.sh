#!/bin/sh
# Container start: prepare the uploads volume, apply migrations, then run the API as a non-root user.
set -e

if [ "$(id -u)" = "0" ]; then
    # setpriv changes the user but not the environment. Without this, HOME stays /root, and libpq
    # probes /root/.postgresql/postgresql.crt (its default, optional client-certificate path) on
    # every SSL connection: as the app user that probe fails with "Permission denied", which libpq
    # treats as fatal. With the app user's own HOME the file is simply absent, as intended.
    HOME="$(getent passwd app | cut -d: -f6)"
    export HOME
fi

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

# Where the database is, without secrets (never the URL, user or password).
python -m scripts.db_info || true

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

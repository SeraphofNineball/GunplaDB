#!/bin/bash
set -e

# Detect PostgreSQL binary path (handles whatever version Debian installed)
PG_VERSION=$(ls /usr/lib/postgresql/)
export PG_BIN="/usr/lib/postgresql/${PG_VERSION}/bin"

# Set internal service connection strings (always localhost in single-container mode)
export DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER:-gunpla}:${POSTGRES_PASSWORD:-gunplapass}@127.0.0.1:5432/gunpladb"
export REDIS_URL="redis://127.0.0.1:6379/0"
export MINIO_ENDPOINT="127.0.0.1:9000"
export MINIO_ACCESS_KEY="${MINIO_ROOT_USER:-minioadmin}"
export MINIO_SECRET_KEY="${MINIO_ROOT_PASSWORD:-minioadmin123}"
export MINIO_BUCKET="gunpladb"
export SECRET_KEY="${SECRET_KEY:-changeme-in-production}"
export MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}"
export MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minioadmin123}"

INIT_FLAG=/var/lib/postgresql/.gunpladb_initialized

if [ ! -f "$INIT_FLAG" ]; then
    echo "[gunpladb] First run — initializing services..."

    # PostgreSQL
    mkdir -p /var/lib/postgresql/data
    chown -R postgres:postgres /var/lib/postgresql/data
    gosu postgres "$PG_BIN/initdb" -D /var/lib/postgresql/data

    gosu postgres "$PG_BIN/pg_ctl" start -D /var/lib/postgresql/data -w -o "-h 127.0.0.1 -p 5432"
    gosu postgres psql -c "CREATE USER ${POSTGRES_USER:-gunpla} WITH PASSWORD '${POSTGRES_PASSWORD:-gunplapass}';"
    gosu postgres psql -c "CREATE DATABASE gunpladb OWNER ${POSTGRES_USER:-gunpla};"
    gosu postgres "$PG_BIN/pg_ctl" stop -D /var/lib/postgresql/data -w

    # MinIO bucket
    mkdir -p /data/minio
    MINIO_ROOT_USER="${MINIO_ROOT_USER}" \
    MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD}" \
    /usr/local/bin/minio server /data/minio &
    MINIO_PID=$!

    echo "[gunpladb] Waiting for MinIO..."
    for i in $(seq 1 30); do
        if /usr/local/bin/mc alias set local http://127.0.0.1:9000 \
            "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" 2>/dev/null; then
            break
        fi
        sleep 1
    done

    /usr/local/bin/mc mb --ignore-existing local/gunpladb
    /usr/local/bin/mc anonymous set download local/gunpladb

    kill $MINIO_PID
    wait $MINIO_PID 2>/dev/null || true

    touch "$INIT_FLAG"
    echo "[gunpladb] Initialization complete."
fi

mkdir -p /data/redis /var/log/supervisor

exec "$@"

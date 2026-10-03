#!/bin/sh
# Espera a la base de datos, aplica migraciones, recopila estáticos y arranca el comando (gunicorn).
set -eu

echo "Esperando a PostgreSQL en ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
python - <<'PY'
import os
import sys
import time

import psycopg

limite = time.monotonic() + 60
while True:
    try:
        psycopg.connect(
            dbname=os.environ["POSTGRES_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            host=os.environ.get("POSTGRES_HOST", "db"),
            port=os.environ.get("POSTGRES_PORT", "5432"),
            connect_timeout=3,
        ).close()
        break
    except psycopg.OperationalError as error:
        if time.monotonic() > limite:
            print(f"PostgreSQL no respondió en 60 s: {error}", file=sys.stderr)
            sys.exit(1)
        time.sleep(1)
PY
echo "PostgreSQL disponible."

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"

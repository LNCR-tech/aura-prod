#!/bin/sh
set -eu

mode="${SERVICE_MODE:-web}"

case "$mode" in
  web)
    exec python /app/scripts/run_runtime_stack.py
    ;;
  worker)
    exec celery -A app.workers.celery_app.celery_app worker \
      --loglevel="${CELERY_LOGLEVEL:-info}" \
      --pool "${CELERY_WORKER_POOL:-solo}" \
      --concurrency "${CELERY_WORKER_CONCURRENCY:-1}"
    ;;
  beat)
    exec celery -A app.workers.celery_app.celery_app beat \
      --loglevel="${CELERY_LOGLEVEL:-info}" \
      --schedule /tmp/celerybeat-schedule
    ;;
  migrate)
    # If upgrade fails (e.g. old revision not found after migration history reset),
    # clear alembic_version and retry. Safe because baseline uses CREATE TABLE IF NOT EXISTS.
    if ! alembic upgrade heads 2>/dev/null; then
      echo "Migration failed — clearing stale alembic_version and retrying..."
      python -c "
from sqlalchemy import create_engine, text
import os
engine = create_engine(os.environ['DATABASE_URL'], connect_args={'options': '-csearch_path=aura_norm,public'})
with engine.connect() as conn:
    for schema in ['aura_norm', 'public']:
        try:
            conn.execute(text(f'DELETE FROM {schema}.alembic_version'))
            conn.commit()
            print(f'Cleared {schema}.alembic_version')
        except Exception:
            conn.rollback()
"
      exec alembic upgrade heads
    fi
    ;;
  *)
    echo "Unsupported SERVICE_MODE: $mode" >&2
    exit 1
    ;;
esac

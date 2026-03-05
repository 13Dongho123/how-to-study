#!/usr/bin/env sh
set -e

# Option 1 (권장): .env의 완성형 DB_URL 사용
# Option 2: DB_URL이 없으면 MYSQL_* + DB_* 값으로 조합
if [ -z "${DB_URL:-}" ] && [ -n "${MYSQL_USER:-}" ] && [ -n "${MYSQL_PASSWORD:-}" ] && [ -n "${DB_HOST:-}" ] && [ -n "${DB_NAME:-}" ]; then
  export DB_URL="mysql+pymysql://${MYSQL_USER}:${MYSQL_PASSWORD}@${DB_HOST}:${DB_PORT:-3306}/${DB_NAME}?charset=utf8mb4"
fi

echo "[entrypoint] Waiting for MySQL..."

python - <<'PY'
import os
import time
import traceback
from sqlalchemy import create_engine, text

url = os.getenv("DB_URL") or os.getenv("DATABASE_URL")
if not url:
    raise SystemExit("DB_URL (or DATABASE_URL) is not set")

last_err = None
for i in range(60):
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[entrypoint] MySQL is ready")
        break
    except Exception as e:
        last_err = e
        print(f"[entrypoint] attempt {i+1}/60 failed: {e!r}")
        time.sleep(2)
else:
    print("[entrypoint] MySQL connection failed after 120s.")
    print("[entrypoint] last error traceback:")
    traceback.print_exception(type(last_err), last_err, last_err.__traceback__)
    raise SystemExit("MySQL connection failed")
PY

if [ "${AUTO_DB_UPGRADE:-0}" = "1" ]; then
  echo "[entrypoint] Running flask db upgrade..."
  flask db upgrade
fi

echo "[entrypoint] Starting Flask..."
exec flask run --host=0.0.0.0 --port=5000

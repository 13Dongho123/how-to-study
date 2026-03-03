#!/usr/bin/env sh
set -e

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

for i in range(60):  # 60 * 2s = 120s
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

echo "[entrypoint] Starting Flask..."
exec flask run --host=0.0.0.0 --port=5000
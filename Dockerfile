# ---------- builder ----------
FROM python:3.12-slim AS builder
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


# ---------- runtime ----------
FROM python:3.12-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py

# 런타임 최소 의존성 (PyMuPDF 환경에 따라 아래 3개는 필요 없으면 제거 가능)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libssl3 \
    libglib2.0-0 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY . .
RUN chmod +x /app/scripts/entrypoint.sh

EXPOSE 5000
CMD ["/app/scripts/entrypoint.sh"]
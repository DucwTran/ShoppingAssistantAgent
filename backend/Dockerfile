FROM python:3.11.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production \
    LOG_FORMAT=json \
    DATA_DIR=/data

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY data/knowledge ./data/knowledge
COPY docker-entrypoint.sh .

# Runtime state lives on a volume at /data; the process runs unprivileged
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /data \
    && chown app:app /data \
    && chmod +x docker-entrypoint.sh
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3)"

CMD ["./docker-entrypoint.sh"]

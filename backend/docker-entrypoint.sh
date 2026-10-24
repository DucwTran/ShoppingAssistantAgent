#!/bin/sh
set -e

# Build the knowledge index on first start (it lives on the volume, so later starts skip this).
# A failure does not stop the server: queries still work through web search, and /health/ready
# reports the missing index.
python -m app.rag.vectorstore --if-missing \
    || echo '{"level": "ERROR", "message": "Knowledge index build failed; /health/ready reports not ready"}'

# One worker on purpose: embedded Qdrant and SQLite allow a single process, and the rate limit is
# counted in memory. --proxy-headers takes the client address from the X-Forwarded-For set by the
# frontend's nginx; trusting every sender is safe only because this port is not published.
exec uvicorn app.main:app \
    --host 0.0.0.0 --port 8000 --workers 1 \
    --proxy-headers --forwarded-allow-ips='*' \
    --no-access-log

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000 \
    STORAGE_PATH=/data/storage

WORKDIR /srv

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# The API runs as this unprivileged user; the entrypoint only uses root to prepare the volume.
RUN chmod +x /usr/local/bin/docker-entrypoint.sh \
    && useradd --create-home --uid 10001 app \
    && mkdir -p /data/storage && chown -R app /srv /data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8000\")}/health', timeout=2)"

ENTRYPOINT ["docker-entrypoint.sh"]
# --host '' opens one IPv4 and one IPv6 socket (Railway's private network is IPv6; "::" alone
# would be IPv6-only under asyncio). Proxy headers give the real client IP behind Railway's edge.
CMD ["sh", "-c", "exec uvicorn app.main:app --host '' --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]

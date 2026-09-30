FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AGENT_CORE_PORT=8001

WORKDIR /srv

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 agent && chown -R agent /srv
USER agent

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\") or os.environ.get(\"AGENT_CORE_PORT\", \"8001\")}/health', timeout=2)"

# --host '' opens one IPv4 and one IPv6 socket (Railway's private network is IPv6; "::" alone
# would be IPv6-only under asyncio). PORT (set by Railway) wins over AGENT_CORE_PORT.
CMD ["sh", "-c", "exec uvicorn app.main:create_app --factory --host '' --port ${PORT:-${AGENT_CORE_PORT}}"]

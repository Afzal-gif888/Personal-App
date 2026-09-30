"""Database connection configuration (no live database needed).

Guards the Railway/Neon setup: DATABASE_URL comes from the environment, SSL query parameters pass
through untouched, nothing adds client-certificate settings, and Alembic uses the same URL as the app.
"""

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy.engine import make_url

from app.core.config import Settings
from app.db.session import build_engine
from scripts.db_info import describe

BACKEND = Path(__file__).resolve().parents[1]
NEON = "postgresql://neon_user:not-a-real-password@ep-example-123456.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
CLIENT_CERT_KEYS = {"sslcert", "sslkey", "sslrootcert", "sslpassword", "sslcrl"}


def test_database_url_is_read_from_the_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", NEON)
    url = make_url(Settings().database_url)
    assert url.host == "ep-example-123456.us-east-2.aws.neon.tech" and url.database == "neondb"


def test_local_development_url_still_works(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://agentos:agentos@127.0.0.1:5433/agentos")
    url = make_url(Settings().database_url)
    assert url.drivername == "postgresql+psycopg" and url.port == 5433 and url.database == "agentos"


def test_neon_ssl_parameters_are_preserved_and_no_client_certificate_is_added(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", NEON)
    engine = build_engine(Settings().database_url)
    try:
        assert engine.url.drivername == "postgresql+psycopg"  # psycopg 3, not psycopg2
        assert engine.url.query["sslmode"] == "require"
        assert engine.url.query["channel_binding"] == "require"
        assert not CLIENT_CERT_KEYS & set(engine.url.query)
        # What SQLAlchemy actually hands psycopg/libpq: SSL mode yes, client certificate paths no.
        _, kwargs = engine.dialect.create_connect_args(engine.url)
        passed = " ".join(f"{k}={v}" for k, v in kwargs.items())
        assert "sslmode=require" in passed and "channel_binding=require" in passed
        assert not CLIENT_CERT_KEYS & set(kwargs) and "postgresql.crt" not in passed
    finally:
        engine.dispose()


def test_postgres_scheme_from_hosting_providers_is_normalised(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", NEON.replace("postgresql://", "postgres://"))
    url = make_url(Settings().database_url)
    assert url.drivername == "postgresql+psycopg" and url.query["sslmode"] == "require"


def test_alembic_uses_the_same_database_url_as_the_app():
    """Offline migration run (no connection): Alembic's URL must be DATABASE_URL, not a default."""
    code = (
        "from alembic.config import Config\nfrom alembic import command\n"
        "cfg = Config('alembic.ini')\ncommand.upgrade(cfg, 'head', sql=True)\n"
        "import sys; print('ALEMBIC_URL=' + cfg.get_main_option('sqlalchemy.url'), file=sys.stderr)\n"
    )
    env = {**os.environ, "DATABASE_URL": NEON, "APP_ENV": "development"}
    result = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr[-2000:]
    alembic_url = make_url(result.stderr.split("ALEMBIC_URL=")[1].split()[0])
    app_url = make_url(Settings(database_url=NEON).database_url)
    assert alembic_url.render_as_string(hide_password=False) == app_url.render_as_string(hide_password=False)
    assert "CREATE TABLE users" in result.stdout  # migrations rendered against PostgreSQL


def test_startup_diagnostic_never_prints_credentials():
    line = describe(Settings(database_url=NEON).database_url)
    assert line == ("Database: postgresql host=ep-example-123456.us-east-2.aws.neon.tech db=neondb "
                    "sslmode=require channel_binding=require")
    assert "not-a-real-password" not in line and "neon_user" not in line


def test_entrypoint_gives_the_app_user_its_own_home_before_dropping_root():
    """setpriv keeps HOME=/root; libpq then probes /root/.postgresql/postgresql.crt as the app user
    and fails with Permission denied on any SSL connection (the Railway + Neon failure)."""
    script = (BACKEND / "docker-entrypoint.sh").read_text(encoding="utf-8")
    home = script.index('HOME="$(getent passwd app')
    assert home < script.index("setpriv --reuid=app") and "export HOME" in script
    assert "sslcert" not in script and "PGSSL" not in script
    assert b"\r" not in (BACKEND / "docker-entrypoint.sh").read_bytes()  # LF endings: runs on Linux


def test_production_refuses_a_local_or_missing_database(monkeypatch):
    import pytest

    prod = {"app_env": "production", "jwt_secret": "x" * 48, "jwt_refresh_secret": "y" * 48, "cors_origins": ["https://app.example"]}
    monkeypatch.delenv("DATABASE_URL", raising=False)
    for local in ("postgresql+psycopg://agentos:agentos@localhost:5432/agentos", "sqlite:///x.db"):
        with pytest.raises(ValueError, match="DATABASE_URL must point"):
            Settings(**prod, database_url=local)
    assert Settings(**prod, database_url=NEON).database_url.startswith("postgresql+psycopg://")  # Neon is fine

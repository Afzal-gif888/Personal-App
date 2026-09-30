"""CORS: the deployed frontend (another origin) must pass the browser's preflight; other sites must not."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings

VERCEL = "https://its-personal-7dujighsp-xdark1.vercel.app"
PREFLIGHT = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type"}


def _client(monkeypatch, origins, regex=""):
    """A fresh app built with these CORS settings (the middleware reads them at startup)."""
    from app.main import create_app

    monkeypatch.setattr(get_settings(), "cors_origins", Settings(cors_origins=origins).cors_origins)
    monkeypatch.setattr(get_settings(), "cors_origin_regex", regex)
    return TestClient(create_app())


def test_preflight_from_the_configured_frontend_is_allowed(monkeypatch):
    client = _client(monkeypatch, VERCEL)
    resp = client.options("/api/v1/auth/login", headers={"Origin": VERCEL, **PREFLIGHT})
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == VERCEL
    methods = resp.headers["access-control-allow-methods"]
    assert all(m in methods for m in ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"))
    allowed = resp.headers["access-control-allow-headers"].lower()
    assert "authorization" in allowed and "content-type" in allowed  # what the frontend sends
    assert "access-control-allow-credentials" not in resp.headers  # bearer tokens, not cookies


def test_real_responses_carry_the_header_too(monkeypatch):
    """After the preflight the browser still needs the header on the actual (even failed) response."""
    client = _client(monkeypatch, VERCEL)
    resp = client.post("/api/v1/auth/login", headers={"Origin": VERCEL},
                       json={"email": "nobody@example.com", "password": "wrong-password"})
    assert resp.status_code == 401 and resp.headers["access-control-allow-origin"] == VERCEL


def test_unrelated_origins_are_refused(monkeypatch):
    client = _client(monkeypatch, VERCEL)
    for origin in ("https://evil.example", "https://its-personal-7dujighsp-xdark1.vercel.app.evil.example", "http://localhost:5173"):
        resp = client.options("/api/v1/auth/login", headers={"Origin": origin, **PREFLIGHT})
        assert resp.status_code == 400 and "access-control-allow-origin" not in resp.headers, origin


@pytest.mark.parametrize("value", [
    VERCEL, VERCEL + "/", f'"{VERCEL}"', f"'{VERCEL}'", f"  {VERCEL}  ", VERCEL.upper().replace("HTTPS://", "https://"),
    f'["{VERCEL}"]', f"{VERCEL}, http://localhost:5173",
])
def test_dashboard_formatting_is_normalised(value):
    """Trailing slash, quotes, spaces or capitals pasted into Railway used to break the exact match."""
    assert VERCEL in Settings(cors_origins=value).cors_origins


def test_local_development_default_still_works(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert Settings().cors_origins == ["http://localhost:5173"]


def test_optional_regex_allows_every_deployment_of_this_project_only(monkeypatch):
    client = _client(monkeypatch, VERCEL, regex=r"^https://its-personal-[a-z0-9]+-xdark1\.vercel\.app$")
    ok = client.options("/api/v1/auth/login", headers={"Origin": "https://its-personal-abc123xyz-xdark1.vercel.app", **PREFLIGHT})
    assert ok.status_code == 200 and ok.headers["access-control-allow-origin"] == "https://its-personal-abc123xyz-xdark1.vercel.app"
    other = client.options("/api/v1/auth/login", headers={"Origin": "https://someone-else-abc-xdark2.vercel.app", **PREFLIGHT})
    assert other.status_code == 400 and "access-control-allow-origin" not in other.headers


def test_production_refuses_wildcards():
    prod = {"app_env": "production", "jwt_secret": "x" * 48, "jwt_refresh_secret": "y" * 48,
            "database_url": "postgresql://u:p@db.example/neondb?sslmode=require"}
    with pytest.raises(ValueError, match="Wildcard"):
        Settings(**prod, cors_origins="*")
    with pytest.raises(ValueError, match="anchored"):
        Settings(**prod, cors_origins=VERCEL, cors_origin_regex=".*")
    assert Settings(**prod, cors_origins=VERCEL + "/").cors_origins == [VERCEL]

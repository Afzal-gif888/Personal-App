"""Print where the database is, for deployment logs. Never prints the URL, user or password.

    python -m scripts.db_info   ->   Database: postgresql host=ep-xxxx.neon.tech db=neondb sslmode=require
"""

from sqlalchemy.engine import make_url

from app.core.config import get_settings


def describe(url: str) -> str:
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite":
        return "Database: sqlite (local development only)"
    query = parsed.query
    parts = [f"host={parsed.host or '?'}", f"db={parsed.database or '?'}", f"sslmode={query.get('sslmode', 'default')}"]
    if "channel_binding" in query:
        parts.append(f"channel_binding={query['channel_binding']}")
    return f"Database: {parsed.get_backend_name()} " + " ".join(parts)


if __name__ == "__main__":
    try:
        print(describe(get_settings().database_url), flush=True)
    except Exception as exc:  # diagnostics only: never block startup, never echo the value
        print(f"Database: could not read DATABASE_URL ({type(exc).__name__})", flush=True)

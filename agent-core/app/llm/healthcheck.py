"""Check FreeLLMAPI connection without revealing secrets.

Usage:
    python healthcheck.py
    python healthcheck.py --chat
    python -m app.llm.healthcheck
    python -m llm.healthcheck
"""

import argparse
import asyncio
import os
import sys
from urllib.parse import urlsplit, urlunsplit
import httpx

try:
    from app.llm.freellmapi import FreeLLMAPIClient
except ImportError:
    try:
        from freellmapi import FreeLLMAPIClient
    except ImportError:
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, os.path.abspath(os.path.join(cur_dir, "..", "..")))
        from app.llm.freellmapi import FreeLLMAPIClient


def scrub_url(raw_url: str) -> str:
    """Remove sensitive userinfo/passwords from URL string if present."""
    try:
        parts = urlsplit(raw_url)
        if parts.password or parts.username:
            netloc = parts.hostname or ""
            if parts.port:
                netloc += f":{parts.port}"
            return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    except Exception:
        pass
    return raw_url


def mask_key(api_key: str | None) -> str:
    """Mask key so no secrets are ever revealed."""
    if not api_key:
        return "MISSING"
    return "Configured"


async def check(chat: bool = False, transport: httpx.AsyncBaseTransport | None = None) -> int:
    base_url = os.getenv("FREELLMAPI_BASE_URL", "http://127.0.0.1:31415/v1")
    api_key = os.getenv("FREELLMAPI_API_KEY")
    model = os.getenv("FREELLMAPI_MODEL", "auto")

    safe_url = scrub_url(base_url)
    print(f"{'Base URL:':<18} {safe_url}")
    print(f"{'Model:':<18} {model}")
    print(f"{'API Key:':<18} {mask_key(api_key)}")

    if not api_key:
        print("\n[!] Please set FREELLMAPI_API_KEY in your environment.")
        return 1

    client = FreeLLMAPIClient(base_url, api_key, model, transport=transport)
    try:
        # 1. Check reachability and models
        async with httpx.AsyncClient(timeout=10.0, transport=transport) as h:
            norm_base = base_url.rstrip("/")
            models_endpoint = f"{norm_base}/models"
            headers = {"Authorization": f"Bearer {api_key}"}
            r = await h.get(models_endpoint, headers=headers)
            if r.status_code == 200:
                data = r.json()
                models = [m.get("id") for m in data.get("data", [])] if isinstance(data, dict) else []
                print(f"{'Connection:':<18} OK")
                print(f"{'Models Found:':<18} {len(models)} models available")
            else:
                print(f"{'Connection:':<18} FAILED (HTTP {r.status_code})")
                return 1

        # 2. Check test completion if requested
        if chat:
            print("Running test completion...")
            reply = await client.chat_completion([{"role": "user", "content": "Reply with 'OK'."}], max_tokens=10)
            print(f"{'Chat Completion:':<18} OK (Response: '{reply.strip()}')")

        print("\nAll health checks passed.")
        return 0
    except Exception as e:
        err_msg = str(e)
        if api_key and api_key in err_msg:
            err_msg = err_msg.replace(api_key, "[REDACTED]")
        print(f"\n[!] Healthcheck error: {err_msg}")
        return 1
    finally:
        await client.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Check FreeLLMAPI gateway health")
    parser.add_argument("--chat", action="store_true", help="Run a test completion")
    args = parser.parse_args()
    code = asyncio.run(check(args.chat))
    sys.exit(code)


if __name__ == "__main__":
    main()

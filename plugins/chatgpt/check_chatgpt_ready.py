#!/usr/bin/env python3
"""Проверка, что endpoint готов для ChatGPT MCP connector."""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_token_from_env() -> str:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return os.environ.get("MCP_AUTH_TOKEN", "")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "MCP_AUTH_TOKEN":
            return value.strip().strip('"').strip("'")
    return os.environ.get("MCP_AUTH_TOKEN", "")


def request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    insecure: bool = False,
) -> tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    context = ssl._create_unverified_context() if insecure else None
    try:
        with urllib.request.urlopen(req, context=context, timeout=20) as resp:
            return resp.status, dict(resp.headers.items()), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers.items() if exc.headers else {}), exc.read()


def ok(label: str, detail: str = "") -> None:
    print(f"[OK]   {label}" + (f" — {detail}" if detail else ""))


def fail(label: str, detail: str = "") -> None:
    print(f"[FAIL] {label}" + (f" — {detail}" if detail else ""))


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверка готовности MCP для ChatGPT")
    parser.add_argument("--base", required=True, help="Базовый URL, например https://top10.example.com")
    parser.add_argument("--token", default=None, help="MCP_AUTH_TOKEN (иначе из .env)")
    parser.add_argument("--insecure", action="store_true", help="Не проверять TLS (только отладка)")
    args = parser.parse_args()

    base = args.base.rstrip("/")
    token = args.token if args.token is not None else load_token_from_env()
    failed = 0

    if not base.startswith("https://"):
        fail("HTTPS", f"ChatGPT требует https://, сейчас: {base}")
        failed += 1
    else:
        ok("HTTPS URL", base)

    # health
    status, _, body = request(f"{base}/health", insecure=args.insecure)
    try:
        payload: Any = json.loads(body.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        payload = {}
    if status == 200 and payload.get("ok") is True and payload.get("database") == "up":
        ok("/health", body.decode("utf-8", errors="replace"))
    else:
        fail("/health", f"HTTP {status}: {body[:200]!r}")
        failed += 1

    # MCP initialize
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        print("[WARN] MCP_AUTH_TOKEN не задан — если на сервере токен обязателен, initialize упадёт с 401")

    init_body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "chatgpt-ready-check", "version": "1.0"},
            },
        }
    ).encode("utf-8")

    status, resp_headers, body = request(
        f"{base}/mcp",
        method="POST",
        headers=headers,
        body=init_body,
        insecure=args.insecure,
    )
    text = body.decode("utf-8", errors="replace")
    if status == 401:
        fail("/mcp initialize", "401 Unauthorized — укажите верный --token / MCP_AUTH_TOKEN")
        failed += 1
    elif status >= 400:
        fail("/mcp initialize", f"HTTP {status}: {text[:300]}")
        failed += 1
    elif "obch-top10-mcp" in text or '"result"' in text:
        ok("/mcp initialize", f"HTTP {status}, ответ содержит MCP result")
    else:
        fail("/mcp initialize", f"Неожиданный ответ HTTP {status}: {text[:300]}")
        failed += 1

    # CORS preflight-ish check (ChatGPT browser-side)
    status, resp_headers, _ = request(
        f"{base}/mcp",
        method="OPTIONS",
        headers={
            "Origin": "https://chatgpt.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
        insecure=args.insecure,
    )
    acao = resp_headers.get("Access-Control-Allow-Origin") or resp_headers.get("access-control-allow-origin")
    if status in (200, 204) and acao:
        ok("CORS", f"Access-Control-Allow-Origin={acao}")
    else:
        fail("CORS", f"HTTP {status}, Allow-Origin={acao!r} — обновите приложение (есть cors в app.js)")
        failed += 1

    print()
    if failed:
        print(f"Итог: НЕ готово к ChatGPT ({failed} ошибок).")
        print("Частые причины: нет HTTPS/домена, неверный токен, MCP_ALLOWED_HOSTS без домена.")
        return 1

    print("Итог: готово к ChatGPT connector.")
    print(f"Connector URL:  {base}/mcp")
    print("Authentication: Token = MCP_AUTH_TOKEN из .env")
    return 0


if __name__ == "__main__":
    sys.exit(main())

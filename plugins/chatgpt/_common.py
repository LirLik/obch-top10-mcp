from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"
NGINX_SITE = Path("/etc/nginx/sites-available/obch-top10-mcp")
NGINX_ENABLED = Path("/etc/nginx/sites-enabled/obch-top10-mcp")
APP_PORT = 3920


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    print("+", " ".join(cmd))
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


def require_root(script_hint: str) -> None:
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        print(f"Запускайте от root: sudo python3 {script_hint}")
        sys.exit(1)


def public_ip() -> str | None:
    for cmd in (
        ["curl", "-4", "-sS", "--max-time", "5", "https://ifconfig.me"],
        ["curl", "-4", "-sS", "--max-time", "5", "https://api.ipify.org"],
    ):
        try:
            proc = run(cmd, check=False)
            ip = (proc.stdout or "").strip()
            if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", ip):
                return ip
        except Exception:
            continue
    return None


def normalize_domain(domain: str) -> str:
    domain = domain.strip().lower()
    domain = re.sub(r"^https?://", "", domain)
    domain = domain.split("/")[0].split(":")[0].rstrip(".")
    if not domain:
        print("Домен пустой")
        sys.exit(1)
    return domain


def merge_allowed_hosts(domain: str, server_ip: str | None = None) -> list[str]:
    existing: list[str] = []
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if line.startswith("MCP_ALLOWED_HOSTS="):
                raw = line.split("=", 1)[1].strip().strip('"').strip("'")
                existing = [x.strip() for x in raw.split(",") if x.strip()]
                break

    hosts: list[str] = []
    for item in [domain, server_ip, "127.0.0.1", "localhost", *existing]:
        if item and item not in hosts:
            hosts.append(item)
    return hosts


def update_env_hosts(hosts: list[str]) -> None:
    if not ENV_PATH.exists():
        example = PROJECT_ROOT / ".env.example"
        ENV_PATH.write_text(
            example.read_text(encoding="utf-8") if example.exists() else "",
            encoding="utf-8",
        )

    text = ENV_PATH.read_text(encoding="utf-8")
    line = "MCP_ALLOWED_HOSTS=" + ",".join(hosts)
    if re.search(r"^MCP_ALLOWED_HOSTS=", text, flags=re.M):
        text = re.sub(r"^MCP_ALLOWED_HOSTS=.*$", line, text, flags=re.M)
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text += line + "\n"
    ENV_PATH.write_text(text, encoding="utf-8")
    print(f"Обновлён {ENV_PATH}")
    print(f"  {line}")


def ensure_nginx_symlink() -> None:
    NGINX_SITE.parent.mkdir(parents=True, exist_ok=True)
    if NGINX_ENABLED.exists() or NGINX_ENABLED.is_symlink():
        if NGINX_ENABLED.resolve() != NGINX_SITE.resolve():
            NGINX_ENABLED.unlink()
            NGINX_ENABLED.symlink_to(NGINX_SITE)
    else:
        NGINX_ENABLED.symlink_to(NGINX_SITE)

    default_enabled = Path("/etc/nginx/sites-enabled/default")
    if default_enabled.exists() or default_enabled.is_symlink():
        default_enabled.unlink()
        print("Отключён sites-enabled/default")


def patch_or_write_nginx(domain: str, server_ip: str | None) -> None:
    names = [domain]
    if server_ip:
        names.append(server_ip)
    names.append("_")
    server_name = " ".join(dict.fromkeys(names))

    ensure_nginx_symlink()

    if NGINX_SITE.exists():
        text = NGINX_SITE.read_text(encoding="utf-8")
        if re.search(r"^\s*server_name\s+", text, flags=re.M):
            text = re.sub(
                r"^(\s*server_name\s+).*;\s*$",
                rf"\1{server_name};",
                text,
                flags=re.M,
                count=1,
            )
            # если есть второй server_name в ssl-блоке certbot — тоже обновим все
            text = re.sub(
                r"^(\s*server_name\s+)[^;]*;",
                rf"\1{server_name};",
                text,
                flags=re.M,
            )
            NGINX_SITE.write_text(text, encoding="utf-8")
            print(f"Nginx server_name → {server_name}")
        else:
            _write_fresh_nginx(server_name)
    else:
        _write_fresh_nginx(server_name)

    proc = run(["nginx", "-t"], check=False)
    if proc.stdout:
        print(proc.stdout.strip())
    if proc.stderr:
        print(proc.stderr.strip())
    if proc.returncode != 0:
        sys.exit(proc.returncode)
    run(["systemctl", "reload", "nginx"])


def _write_fresh_nginx(server_name: str) -> None:
    content = f"""server {{
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name {server_name};

    client_max_body_size 2m;

    location / {{
        proxy_pass http://127.0.0.1:{APP_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_read_timeout 3600s;
    }}
}}
"""
    NGINX_SITE.write_text(content, encoding="utf-8")
    print(f"Создан {NGINX_SITE}")


def restart_app() -> None:
    proc = run(["systemctl", "restart", "obch-top10-mcp"], check=False)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout)
        print("Не удалось перезапустить obch-top10-mcp")
        sys.exit(1)
    active = run(["systemctl", "is-active", "obch-top10-mcp"], check=False)
    print("obch-top10-mcp:", (active.stdout or "").strip())

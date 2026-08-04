#!/usr/bin/env python3
"""Настройка HTTPS (Nginx + Certbot) для obch-top10-mcp под ChatGPT MCP connector."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import socket
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


def require_root() -> None:
    if os.geteuid() != 0:
        print("Запускайте от root: sudo python3 plugins/chatgpt/setup_https.py --domain ...")
        sys.exit(1)


def resolve_ips(domain: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(domain, 80, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        print(f"DNS не резолвится для {domain}: {exc}")
        sys.exit(1)
    ips = sorted({item[4][0] for item in infos})
    return ips


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


def ensure_packages() -> None:
    if shutil.which("certbot") and Path("/usr/lib/python3/dist-packages/certbot_nginx").exists():
        return
    run(["apt-get", "update"])
    run(["apt-get", "install", "-y", "certbot", "python3-certbot-nginx", "curl"])


def write_nginx(domain: str, server_ip: str | None) -> None:
    names = [domain, "_"]
    if server_ip:
        names.insert(1, server_ip)
    server_name = " ".join(names)

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
    NGINX_SITE.parent.mkdir(parents=True, exist_ok=True)
    NGINX_SITE.write_text(content, encoding="utf-8")
    if NGINX_ENABLED.exists() or NGINX_ENABLED.is_symlink():
        NGINX_ENABLED.unlink()
    NGINX_ENABLED.symlink_to(NGINX_SITE)

    default_enabled = Path("/etc/nginx/sites-enabled/default")
    if default_enabled.exists() or default_enabled.is_symlink():
        default_enabled.unlink()
        print("Отключён sites-enabled/default")

    proc = run(["nginx", "-t"], check=False)
    print(proc.stdout)
    print(proc.stderr)
    if proc.returncode != 0:
        sys.exit(proc.returncode)
    run(["systemctl", "reload", "nginx"])


def update_env_hosts(domain: str, server_ip: str | None) -> None:
    hosts = [domain, "127.0.0.1", "localhost"]
    if server_ip:
        hosts.insert(1, server_ip)

    if not ENV_PATH.exists():
        print(f"Нет {ENV_PATH}, создаю из .env.example")
        example = PROJECT_ROOT / ".env.example"
        ENV_PATH.write_text(example.read_text(encoding="utf-8") if example.exists() else "", encoding="utf-8")

    text = ENV_PATH.read_text(encoding="utf-8")
    line = "MCP_ALLOWED_HOSTS=" + ",".join(hosts)
    if re.search(r"^MCP_ALLOWED_HOSTS=", text, flags=re.M):
        text = re.sub(r"^MCP_ALLOWED_HOSTS=.*$", line, text, flags=re.M)
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text += line + "\n"
    ENV_PATH.write_text(text, encoding="utf-8")
    print(f"Обновлён {ENV_PATH}: {line}")


def run_certbot(domain: str, email: str | None) -> None:
    cmd = [
        "certbot",
        "--nginx",
        "-d",
        domain,
        "--non-interactive",
        "--agree-tos",
        "--redirect",
    ]
    if email:
        cmd += ["--email", email]
    else:
        cmd += ["--register-unsafely-without-email"]
    proc = run(cmd, check=False)
    print(proc.stdout)
    print(proc.stderr)
    if proc.returncode != 0:
        print("Certbot не смог выпустить сертификат. Проверьте DNS A-запись и порт 80 с интернета.")
        sys.exit(proc.returncode)


def restart_app() -> None:
    run(["systemctl", "restart", "obch-top10-mcp"], check=False)
    run(["systemctl", "is-active", "obch-top10-mcp"], check=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="HTTPS для obch-top10-mcp (ChatGPT MCP)")
    parser.add_argument("--domain", required=True, help="Домен, например top10.example.com")
    parser.add_argument("--email", default=None, help="Email для Let's Encrypt (опционально)")
    parser.add_argument("--skip-dns-check", action="store_true")
    args = parser.parse_args()

    require_root()
    domain = args.domain.strip().lower().rstrip(".")

    ensure_packages()
    ips = resolve_ips(domain)
    pub = public_ip()
    print(f"DNS {domain} → {', '.join(ips)}")
    if pub:
        print(f"Публичный IP сервера → {pub}")

    if not args.skip_dns_check and pub and pub not in ips:
        print(
            f"ВНИМАНИЕ: DNS не указывает на этот сервер ({pub}). "
            "Certbot, скорее всего, упадёт. Исправьте A-запись или используйте --skip-dns-check."
        )
        sys.exit(1)

    write_nginx(domain, pub)
    update_env_hosts(domain, pub)
    run_certbot(domain, args.email)
    restart_app()

    print()
    print("HTTPS готов.")
    print(f"Сайт:      https://{domain}/")
    print(f"Health:    https://{domain}/health")
    print(f"MCP URL:   https://{domain}/mcp")
    print()
    print("Проверка:")
    print(f"  sudo python3 plugins/chatgpt/check_chatgpt_ready.py --base https://{domain}")
    print()
    print("В ChatGPT connector URL укажите:")
    print(f"  https://{domain}/mcp")
    print("Authentication: Token = значение MCP_AUTH_TOKEN из .env")


if __name__ == "__main__":
    main()

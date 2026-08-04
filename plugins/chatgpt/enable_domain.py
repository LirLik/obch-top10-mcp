#!/usr/bin/env python3
"""
Одна команда: разрешить домен (убирает Invalid Host), обновить Nginx, перезапустить сервис.
Опционально сразу включить HTTPS для ChatGPT.

Примеры:
  sudo python3 plugins/chatgpt/enable_domain.py ra-mcp-5.skobeltsyn.com
  sudo python3 plugins/chatgpt/enable_domain.py ra-mcp-5.skobeltsyn.com --https
"""

from __future__ import annotations

import argparse
import shutil
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from _common import (  # noqa: E402
    merge_allowed_hosts,
    normalize_domain,
    patch_or_write_nginx,
    public_ip,
    require_root,
    restart_app,
    run,
    update_env_hosts,
)


def resolve_ips(domain: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(domain, 80, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        print(f"DNS не резолвится для {domain}: {exc}")
        return []
    return sorted({item[4][0] for item in infos})


def ensure_certbot() -> None:
    has_plugin = Path("/usr/lib/python3/dist-packages/certbot_nginx").exists()
    if shutil.which("certbot") and has_plugin:
        return
    run(["apt-get", "update"])
    run(["apt-get", "install", "-y", "certbot", "python3-certbot-nginx", "curl"])


def run_certbot(domain: str, email: str | None) -> None:
    ensure_certbot()
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
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print(proc.stderr)
    if proc.returncode != 0:
        print("Certbot не смог выпустить сертификат. Проверьте DNS A-запись и порт 80.")
        sys.exit(proc.returncode)


def verify_http(domain: str) -> None:
    url = f"http://{domain}/health"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            print(f"Проверка {url}")
            print(f"  HTTP {resp.status}: {body}")
            compact = body.replace(" ", "")
            if '"ok":true' in compact:
                print("Invalid Host устранён, сайт отвечает.")
            else:
                print("Ответ неожиданный — проверьте: journalctl -u obch-top10-mcp -n 50")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"Проверка {url}: HTTP {exc.code}: {body[:300]}")
        if "Invalid Host" in body:
            print("Host всё ещё блокируется — смотрите MCP_ALLOWED_HOSTS и рестарт сервиса.")
            sys.exit(1)
    except Exception as exc:
        print(f"Не удалось проверить {url}: {exc}")
        print("Сервис мог подняться, проверьте вручную в браузере.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Разрешить домен для obch-top10-mcp (и опционально HTTPS)",
    )
    parser.add_argument(
        "domain",
        help="Домен, например ra-mcp-5.skobeltsyn.com (можно с http://)",
    )
    parser.add_argument(
        "--https",
        action="store_true",
        help="Сразу выпустить Let's Encrypt и настроить HTTPS для ChatGPT",
    )
    parser.add_argument("--email", default=None, help="Email для Let's Encrypt")
    parser.add_argument(
        "--skip-dns-check",
        action="store_true",
        help="Не требовать совпадения DNS с IP сервера (только для --https)",
    )
    args = parser.parse_args()

    require_root("plugins/chatgpt/enable_domain.py <domain>")

    domain = normalize_domain(args.domain)
    pub = public_ip()
    dns_ips = resolve_ips(domain)

    print(f"Домен: {domain}")
    if pub:
        print(f"IP сервера: {pub}")
    if dns_ips:
        print(f"DNS: {', '.join(dns_ips)}")
    else:
        print("DNS: не резолвится (для уже настроенного HTTP-прокси может быть ок)")

    hosts = merge_allowed_hosts(domain, pub)
    update_env_hosts(hosts)
    patch_or_write_nginx(domain, pub)
    restart_app()
    verify_http(domain)

    if args.https:
        if not args.skip_dns_check and pub and dns_ips and pub not in dns_ips:
            print(
                f"DNS {domain} не указывает на {pub}. "
                "Исправьте A-запись или повторите с --skip-dns-check --https"
            )
            sys.exit(1)
        if not dns_ips and not args.skip_dns_check:
            print("DNS пустой — HTTPS не запустить. Настройте A-запись или --skip-dns-check")
            sys.exit(1)
        run_certbot(domain, args.email)
        restart_app()
        print()
        print("HTTPS готов.")
        print(f"  Сайт:  https://{domain}/")
        print(f"  MCP:   https://{domain}/mcp")
        print(
            f"Проверка: sudo python3 plugins/chatgpt/check_chatgpt_ready.py --base https://{domain}"
        )
    else:
        print()
        print("Готово. Откройте:")
        print(f"  http://{domain}/")
        print()
        print("Для ChatGPT нужен HTTPS — одна команда:")
        print(f"  sudo python3 plugins/chatgpt/enable_domain.py {domain} --https")


if __name__ == "__main__":
    main()

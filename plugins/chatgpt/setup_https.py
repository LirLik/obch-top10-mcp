#!/usr/bin/env python3
"""Обёртка: то же, что enable_domain.py --https."""

from __future__ import annotations

import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from enable_domain import main as enable_main  # noqa: E402


def main() -> None:
    # превращаем: setup_https.py --domain X  →  enable_domain.py X --https
    argv = sys.argv[1:]
    domain = None
    rest: list[str] = ["--https"]
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("--domain", "-d") and i + 1 < len(argv):
            domain = argv[i + 1]
            i += 2
            continue
        if not arg.startswith("-") and domain is None:
            domain = arg
            i += 1
            continue
        rest.append(arg)
        i += 1

    if not domain:
        print("Использование: sudo python3 plugins/chatgpt/setup_https.py --domain ra-mcp-5.skobeltsyn.com")
        print("Или:            sudo python3 plugins/chatgpt/enable_domain.py ra-mcp-5.skobeltsyn.com --https")
        sys.exit(2)

    sys.argv = ["enable_domain.py", domain, *rest]
    enable_main()


if __name__ == "__main__":
    main()

# ChatGPT + HTTPS для obch-top10-mcp

ChatGPT **не принимает** `http://IP/...` как MCP-коннектор. Нужен публичный URL вида:

```text
https://ваш-домен/mcp
```

с валидным сертификатом (Let’s Encrypt). Ошибка *«Something went wrong… help.openai.com»* почти всегда из‑за HTTP, самоподписанного сертификата, недоступности с интернета или неверного URL.

Этот плагин — набор Python-скриптов **на сервере**: HTTPS через Nginx+Certbot и проверка готовности для ChatGPT.

## Требования

- Ubuntu-сервер с уже развёрнутым проектом (см. `docs/DEPLOY.md`)
- Домен с A-записью на IP сервера (например `top10.example.com` → `135.106.129.248`)
- Python 3.10+
- ChatGPT **Plus/Pro/Team/Enterprise** и включённый **Developer Mode**

## 1. На сервере: HTTPS

```bash
cd /opt/obch-top10-mcp
sudo python3 plugins/chatgpt/setup_https.py --domain top10.example.com
```

Скрипт:

1. проверит DNS;
2. обновит Nginx (`sites-available/obch-top10-mcp`);
3. выпустит сертификат Let’s Encrypt (certbot);
4. допишет домен в `MCP_ALLOWED_HOSTS` в `.env`;
5. перезапустит `nginx` и `obch-top10-mcp`.

Проверка:

```bash
sudo python3 plugins/chatgpt/check_chatgpt_ready.py --base https://top10.example.com
```

Все пункты должны быть `OK`.

## 2. В ChatGPT: коннектор

1. Профиль → **Settings** → **Apps & Connectors** (или **Connectors**).
2. Включите **Developer Mode** (Advanced / Security — зависит от версии UI).
3. **Create** / **Add custom connector**.
4. Заполните:

| Поле | Значение |
|------|----------|
| Name | `obch Top-10` |
| Connector URL | `https://top10.example.com/mcp` |
| Authentication | **Token** / API key |
| Token | значение `MCP_AUTH_TOKEN` из `.env` на сервере |

5. **Scan tools** → должны появиться `get_top10`, `sync_top10`, `save_top10`.
6. Create / Enable → в чате включите коннектор.

**Не указывайте** `http://135.106.129.248/...` и **не** вставляйте `?token=` в URL, если в UI есть отдельное поле Token — используйте Bearer/Token.

## 3. Если домена ещё нет

Без домена ChatGPT-коннектор стабильно не завести. Варианты:

1. Купить/привязать любой поддомен → шаг 1.
2. Временно туннель Cloudflare (быстрый HTTPS-URL):

```bash
# установка cloudflared — см. https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
cloudflared tunnel --url http://127.0.0.1:3920
```

В `.env` добавьте выданный хост `*.trycloudflare.com` в `MCP_ALLOWED_HOSTS` и перезапустите сервис. URL для ChatGPT: `https://xxxx.trycloudflare.com/mcp`.

## Полезные curl

```bash
curl -sS https://top10.example.com/health
curl -sS -X POST https://top10.example.com/mcp \
  -H "Authorization: Bearer ВАШ_ТОКЕН" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"chatgpt-check","version":"1.0"}}}'
```

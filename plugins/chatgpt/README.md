# ChatGPT + HTTPS для obch-top10-mcp

## Одна команда (главное)

На сервере, из каталога проекта:

```bash
cd /opt/obch-top10-mcp

# 1) Убрать Invalid Host + разретить домен
sudo python3 plugins/chatgpt/enable_domain.py ra-mcp-5.skobeltsyn.com

# 2) Сразу с HTTPS для ChatGPT
sudo python3 plugins/chatgpt/enable_domain.py ra-mcp-5.skobeltsyn.com --https
```

Можно передать URL целиком — скрипт сам вырежет домен:

```bash
sudo python3 plugins/chatgpt/enable_domain.py http://ra-mcp-5.skobeltsyn.com/
```

Что делает команда без `--https`:

1. дописывает домен (и IP сервера) в `MCP_ALLOWED_HOSTS` в `.env`;
2. обновляет `server_name` в Nginx;
3. перезапускает `obch-top10-mcp`;
4. проверяет `http://домен/health`.

С `--https` дополнительно выпускает Let’s Encrypt (certbot).

---

ChatGPT **не принимает** `http://IP/...`. Нужен:

```text
https://ra-mcp-5.skobeltsyn.com/mcp
```

## Проверка перед ChatGPT

```bash
sudo python3 plugins/chatgpt/check_chatgpt_ready.py --base https://ra-mcp-5.skobeltsyn.com
```

Все пункты должны быть `[OK]`.

## В ChatGPT

| Поле | Значение |
|------|----------|
| Name | `obch Top-10` |
| Connector URL | `https://ra-mcp-5.skobeltsyn.com/mcp` |
| Authentication | Token |
| Token | `MCP_AUTH_TOKEN` из `.env` |

Нужны Developer Mode и платный план ChatGPT.

Токен:

```bash
grep MCP_AUTH_TOKEN /opt/obch-top10-mcp/.env
```

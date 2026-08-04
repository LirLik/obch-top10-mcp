# obch-top10-mcp

Единый сервис для Топ-10 результатов **obch**:

- сайт (фронт)
- REST API
- MCP (Streamable HTTP + stdio)
- **MariaDB 10.6** (Prisma)

Один процесс `npm start` обслуживает всё.

## Локальный запуск (Windows / OpenServer)

1. В MariaDB 10.6 создайте БД:

```sql
CREATE DATABASE obch_top10_mcp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. Настройте проект:

```bash
cd C:\OpenServer\domains\obchs\obch-top10-mcp
copy .env.example .env
```

В `.env` укажите, например:

```env
DATABASE_URL="mysql://root:root@127.0.0.1:3306/obch_top10_mcp"
```

3. Установка и миграции:

```bash
npm install
npx prisma migrate deploy
```

4. Запуск:

```bash
npm start
```

| URL | Назначение |
|-----|------------|
| http://127.0.0.1:3920/ | сайт |
| http://127.0.0.1:3920/api/top10 | REST |
| http://127.0.0.1:3920/mcp | MCP |
| http://127.0.0.1:3920/health | health + БД |

Импорт старого `data/top10.json` (если есть):

```bash
npm run db:import-json
```

## MCP в Cursor

С запущенным сервером:

```json
{
  "mcpServers": {
    "obch-top10": {
      "url": "http://127.0.0.1:3920/mcp"
    }
  }
}
```

Локальный stdio без HTTP:

```bash
npm run stdio
```

## Отправка Топ-10 из obch

В `.env` obch:

```env
MCP_TOP10_URL=http://127.0.0.1:3920/api/top10
```

```bash
cd C:\OpenServer\domains\obchs\obch
php artisan stats:push-top10
```

## Деплой на сервер

Пошагово с нуля (Ubuntu, MariaDB, Nginx, systemd):

**[docs/DEPLOY.md](docs/DEPLOY.md)**

## HTTPS + ChatGPT connector

ChatGPT принимает только публичный `https://…/mcp` (не `http://IP`).

Плагин на сервере:

**[plugins/chatgpt/README.md](plugins/chatgpt/README.md)**

```bash
sudo python3 plugins/chatgpt/enable_domain.py ra-mcp-5.skobeltsyn.com
sudo python3 plugins/chatgpt/enable_domain.py ra-mcp-5.skobeltsyn.com --https
sudo python3 plugins/chatgpt/check_chatgpt_ready.py --base https://ra-mcp-5.skobeltsyn.com
```

## Структура

```
obch-top10-mcp/
  prisma/           # схема и миграции MariaDB
  public/           # фронт
  src/
    server.js       # HTTP entry
    app.js          # Express: сайт + API + MCP
    services/       # работа с БД
    stdio.js        # MCP stdio
  docs/DEPLOY.md
```

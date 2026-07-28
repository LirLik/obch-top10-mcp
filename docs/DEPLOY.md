# Инструкция: сервер с нуля → деплой → запуск obch-top10-mcp

Стек: **Ubuntu 22.04/24.04**, **Node.js 20**, **MariaDB 10.6**, **Nginx**, **systemd**.  
Без Docker — меньше места на диске.

Ниже у каждой проверки указан **ожидаемый результат** при правильной настройке.  
Подставьте свой домен вместо `top10.example.com` и свой токен вместо `ДЛИННЫЙ_ТОКЕН`.

---

## 0. Что уже установлено на сервере

Перед установкой проверьте, что уже есть — лишние шаги можно пропустить.

```bash
# ОС
lsb_release -a

# Node / npm (нужен Node 20.x)
node -v
npm -v

# MariaDB / MySQL
systemctl is-active mariadb 2>/dev/null || systemctl is-active mysql 2>/dev/null
mysql --version 2>/dev/null || mariadb --version 2>/dev/null

# Nginx
systemctl is-active nginx
nginx -v

# UFW
sudo ufw status

# Уже развёрнутый проект / служба
ls -la /opt/obch-top10-mcp 2>/dev/null
systemctl is-active obch-top10-mcp 2>/dev/null
curl -sS http://127.0.0.1:3920/health 2>/dev/null
```

| Команда | Уже ок | Нужно ставить / чинить |
|---------|--------|-------------------------|
| `node -v` → `v20.x.x` | Node есть | шаг 1.3 |
| `systemctl is-active mariadb` → `active` | MariaDB запущена | шаг 1.4 |
| `systemctl is-active nginx` → `active` | Nginx запущен | шаг 1.5 |
| `curl …/health` → JSON с `"ok":true` | приложение уже работает | можно сразу к разделу 4 |
| `ls /opt/obch-top10-mcp` показывает файлы | код уже на сервере | шаг 2.1 можно пропустить |

---

## 1. Подготовка сервера

Войдите по SSH как пользователь с `sudo`.

### 1.1. Обновление системы

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y curl ca-certificates gnupg ufw git
```

**Проверка**

```bash
curl --version | head -n 1
git --version
```

**Ожидаемо:** версии утилит без ошибок, например `curl 7.x…`, `git version 2.x…`.

### 1.2. Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

**Ожидаемо** в `ufw status`:

```text
Status: active

To                         Action      From
--                         ------      ----
OpenSSH                    ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
```

Порт приложения (3920) наружу **не открываем** — к нему ходит только Nginx на localhost.

**Проверка**

```bash
sudo ufw status | grep -E '3920|Status'
```

**Ожидаемо:** `Status: active`, строки с `3920` **нет**.

### 1.3. Node.js 20

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

**Проверка**

```bash
node -v
npm -v
which node
```

**Ожидаемо:**

```text
v20.x.x
10.x.x   # или другая актуальная npm
/usr/bin/node
```

Если `node -v` показывает `v18` / `v12` — версия не подходит, переустановите Node 20.

### 1.4. MariaDB 10.6

На Ubuntu 22.04 обычно ставят MariaDB из репозитория (версия может быть 10.6+):

```bash
sudo apt install -y mariadb-server
sudo systemctl enable --now mariadb
sudo mysql_secure_installation
```

Если нужна именно ветка 10.6 с официального зеркала MariaDB — следуйте [документации MariaDB](https://mariadb.org/download/) для вашего релиза Ubuntu, затем:

```bash
sudo systemctl enable --now mariadb
```

**Проверка службы и версии**

```bash
systemctl is-active mariadb
mysql --version || mariadb --version
sudo mysql -e "SELECT VERSION();"
```

**Ожидаемо:**

```text
active
mariadb  Ver 15.1 Distrib 10.6.x-MariaDB ...
# и в SELECT VERSION() что-то вроде:
10.6.x-MariaDB
```

Создайте БД и пользователя:

```bash
sudo mysql
```

В консоли MariaDB:

```sql
CREATE DATABASE obch_top10_mcp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'obch_top10'@'localhost' IDENTIFIED BY 'СИЛЬНЫЙ_ПАРОЛЬ';
GRANT ALL PRIVILEGES ON obch_top10_mcp.* TO 'obch_top10'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

Если БД/пользователь уже есть — команды `CREATE` могут выдать ошибку «already exists»; это нормально, переходите к проверке.

**Проверка доступа пользователя**

```bash
mysql -u obch_top10 -p -e "USE obch_top10_mcp; SELECT DATABASE(); SELECT 1 AS ok;"
```

**Ожидаемо** (после ввода пароля):

```text
+-----------------+
| DATABASE()      |
+-----------------+
| obch_top10_mcp  |
+-----------------+
+----+
| ok |
+----+
|  1 |
+----+
```

Ошибка `Access denied` → неверный пароль или пользователь не создан.  
Ошибка `Unknown database` → БД не создана.

### 1.5. Nginx

```bash
sudo apt install -y nginx
sudo systemctl enable --now nginx
```

**Проверка**

```bash
systemctl is-active nginx
curl -sI http://127.0.0.1/ | head -n 1
```

**Ожидаемо:**

```text
active
HTTP/1.1 200 OK
```

(или `301`/`302`, если дефолтный сайт уже настроен иначе — главное не `Connection refused`).

### 1.6. Пользователь для приложения

```bash
sudo adduser --system --group --home /opt/obch-top10-mcp --shell /usr/sbin/nologin obchtop10
sudo mkdir -p /opt/obch-top10-mcp
sudo chown -R obchtop10:obchtop10 /opt/obch-top10-mcp
```

**Проверка**

```bash
id obchtop10
ls -ld /opt/obch-top10-mcp
```

**Ожидаемо:**

```text
uid=...(...obchtop10) gid=...(...obchtop10) groups=...(...obchtop10)
drwxr-xr-x ... obchtop10 obchtop10 ... /opt/obch-top10-mcp
```

Если пользователь уже есть: `adduser: The user 'obchtop10' already exists` — ок, продолжайте.

---

## 2. Развёртывание проекта

### 2.1. Код на сервер

Вариант A — git:

```bash
sudo -u obchtop10 git clone <URL_РЕПОЗИТОРИЯ> /opt/obch-top10-mcp
cd /opt/obch-top10-mcp
```

Вариант B — архив с вашей машины:

```bash
# локально
cd C:\OpenServer\domains\obchs
tar --exclude=obch-top10-mcp/node_modules -czf obch-top10-mcp.tgz obch-top10-mcp

# на сервере
scp obch-top10-mcp.tgz user@SERVER:/tmp/
sudo tar -xzf /tmp/obch-top10-mcp.tgz -C /opt
sudo chown -R obchtop10:obchtop10 /opt/obch-top10-mcp
cd /opt/obch-top10-mcp
```

**Проверка**

```bash
cd /opt/obch-top10-mcp
ls package.json src/server.js prisma/schema.prisma public/index.html docs/DEPLOY.md
```

**Ожидаемо:** все пять путей существуют (команда `ls` без `No such file`).

### 2.2. Переменные окружения

```bash
sudo -u obchtop10 cp .env.example .env
sudo -u obchtop10 nano .env
```

Минимум:

```env
HOST=127.0.0.1
PORT=3920
DATABASE_URL="mysql://obch_top10:СИЛЬНЫЙ_ПАРОЛЬ@127.0.0.1:3306/obch_top10_mcp"
OBCH_STATS_URL=https://ваш-obch-домен/api/stats
MCP_AUTH_TOKEN=длинный_случайный_токен
MCP_ALLOWED_HOSTS=top10.example.com,127.0.0.1,localhost
```

Сгенерировать токен:

```bash
openssl rand -hex 32
```

**Проверка содержимого `.env` (без показа пароля целиком)**

```bash
cd /opt/obch-top10-mcp
grep -E '^(HOST|PORT|DATABASE_URL|OBCH_STATS_URL|MCP_AUTH_TOKEN|MCP_ALLOWED_HOSTS)=' .env | sed -E 's#(mysql://[^:]+:)[^@]+#\1***#'
```

**Ожидаемо:** строки `HOST`, `PORT`, `DATABASE_URL` (пароль скрыт как `***`), `OBCH_STATS_URL`, при необходимости `MCP_AUTH_TOKEN`, `MCP_ALLOWED_HOSTS`. Пустых значений быть не должно.

### 2.3. Зависимости и миграции

```bash
cd /opt/obch-top10-mcp
sudo -u obchtop10 npm ci
sudo -u obchtop10 npx prisma migrate deploy
sudo -u obchtop10 npx prisma generate
```

**Проверка npm**

```bash
test -d node_modules/@prisma/client && echo "prisma client: OK"
test -d node_modules/express && echo "express: OK"
```

**Ожидаемо:**

```text
prisma client: OK
express: OK
```

**Проверка миграций**

```bash
sudo -u obchtop10 npx prisma migrate status
```

**Ожидаемо** что-то вроде:

```text
Database schema is up to date!
```

или сообщение, что все миграции применены (нет pending).

**Проверка таблиц в БД**

```bash
mysql -u obch_top10 -p -e "USE obch_top10_mcp; SHOW TABLES; DESCRIBE scores; DESCRIBE sync_events;"
```

**Ожидаемо:** таблицы `scores`, `sync_events` и их поля (`rank`, `player_name`, `score`, … / `payload_json`, …).

---

## 3. Запуск приложения

### 3.1. systemd unit

```bash
sudo nano /etc/systemd/system/obch-top10-mcp.service
```

Содержимое:

```ini
[Unit]
Description=obch Top-10 MCP (site + API + MCP)
After=network.target mariadb.service
Wants=mariadb.service

[Service]
Type=simple
User=obchtop10
Group=obchtop10
WorkingDirectory=/opt/obch-top10-mcp
EnvironmentFile=/opt/obch-top10-mcp/.env
ExecStart=/usr/bin/node /opt/obch-top10-mcp/src/server.js
Restart=always
RestartSec=3
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
```

Запуск:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now obch-top10-mcp
```

**Проверка службы**

```bash
systemctl is-active obch-top10-mcp
systemctl is-enabled obch-top10-mcp
systemctl status obch-top10-mcp --no-pager
```

**Ожидаемо:**

```text
active
enabled
```

В `status` — `Active: active (running)`, без бесконечного restart-loop.

**Проверка логов старта**

```bash
sudo journalctl -u obch-top10-mcp -n 30 --no-pager
```

**Ожидаемо** строки вида:

```text
obch-top10-mcp
  сайт:  http://127.0.0.1:3920/
  API:   http://127.0.0.1:3920/api/top10
  MCP:   http://127.0.0.1:3920/mcp
```

**Проверка health на localhost**

```bash
curl -sS http://127.0.0.1:3920/health
echo
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3920/health
```

**Ожидаемо:**

```json
{"ok":true,"service":"obch-top10-mcp","database":"up"}
```

```text
200
```

Если `"database":"down"` — смотрите `DATABASE_URL` и MariaDB (раздел 7).

### 3.2. Nginx reverse proxy

```bash
sudo nano /etc/nginx/sites-available/obch-top10-mcp
```

```nginx
server {
    listen 80;
    server_name top10.example.com;

    client_max_body_size 2m;

    location / {
        proxy_pass http://127.0.0.1:3920;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_read_timeout 3600s;
    }
}
```

```bash
sudo ln -sf /etc/nginx/sites-available/obch-top10-mcp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**Проверка конфига Nginx**

```bash
sudo nginx -t
```

**Ожидаемо:**

```text
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

**Проверка через Nginx (по Host)**

```bash
curl -sS -H "Host: top10.example.com" http://127.0.0.1/health
echo
curl -sS -o /dev/null -w "%{http_code}\n" -H "Host: top10.example.com" http://127.0.0.1/
```

**Ожидаемо:**

```json
{"ok":true,"service":"obch-top10-mcp","database":"up"}
```

```text
200
```

HTML главной должен содержать `obch` / `Top-10` (проверка):

```bash
curl -sS -H "Host: top10.example.com" http://127.0.0.1/ | grep -o 'obch' | head -n 1
```

**Ожидаемо:** строка `obch`.

### 3.3. HTTPS (рекомендуется)

DNS A-запись домена должна указывать на IP сервера.

**Проверка DNS**

```bash
getent hosts top10.example.com
# или
dig +short top10.example.com
```

**Ожидаемо:** IP вашего сервера.

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d top10.example.com
```

**Проверка HTTPS**

```bash
curl -sS https://top10.example.com/health
echo
curl -sS -o /dev/null -w "%{http_code}\n" https://top10.example.com/health
```

**Ожидаемо:** тот же JSON `ok/database:up` и код `200`.

После выпуска сертификата при необходимости обновите `MCP_ALLOWED_HOSTS` в `.env` и перезапустите:

```bash
sudo systemctl restart obch-top10-mcp
```

---

## 4. Полная проверка после деплоя

Замените `BASE` на ваш URL (`https://top10.example.com` или `http://127.0.0.1:3920`).

```bash
BASE="https://top10.example.com"
TOKEN="ДЛИННЫЙ_ТОКЕН"
```

### 4.1. Health

```bash
curl -sS "$BASE/health"; echo
```

**Ожидаемо:**

```json
{"ok":true,"service":"obch-top10-mcp","database":"up"}
```

### 4.2. Сайт

```bash
curl -sS -o /dev/null -w "%{http_code}\n" "$BASE/"
curl -sS "$BASE/" | grep -E 'Top-10|obch' | head -n 3
```

**Ожидаемо:** HTTP `200` и в HTML есть бренд/заголовок Топ-10.  
В браузере: открывается страница лидерборда без ошибки прокси.

### 4.3. API GET

```bash
curl -sS "$BASE/api/top10"; echo
```

**Ожидаемо (пустая БД):**

```json
{"updated_at":null,"source":null,"scores":[],"empty":true,"message":"Топ-10 пока пуст. ..."}
```

**Ожидаемо (после push/POST):** JSON с `"empty":false` и массивом `scores` (до 10 элементов), полями `player_name`, `score`, `rank`.

### 4.4. API POST (запись в MariaDB)

Без токена (если `MCP_AUTH_TOKEN` задан):

```bash
curl -sS -o /dev/null -w "%{http_code}\n" -X POST "$BASE/api/top10" \
  -H "Content-Type: application/json" \
  -d '{"source":"check","scores":[{"player_name":"Тест","score":1}]}'
```

**Ожидаемо:** `401`.

С токеном:

```bash
curl -sS -X POST "$BASE/api/top10" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source":"manual-check","scores":[{"player_name":"Тест","score":100,"lines_cleared":1,"level":1,"duration_seconds":10}]}'
echo
```

**Ожидаемо:** HTTP-ответ `201` (смотрите `curl -w` при желании) и тело вида:

```json
{
  "updated_at": "2026-...",
  "source": "manual-check",
  "scores": [
    {
      "rank": 1,
      "id": null,
      "player_name": "Тест",
      "score": 100,
      "lines_cleared": 1,
      "level": 1,
      "duration_seconds": 10,
      "created_at": null
    }
  ],
  "empty": false
}
```

Повторный GET должен вернуть этого игрока:

```bash
curl -sS "$BASE/api/top10" | grep -o '"player_name":"Тест"'
```

**Ожидаемо:** `"player_name":"Тест"`.

Проверка в БД:

```bash
mysql -u obch_top10 -p -e "USE obch_top10_mcp; SELECT rank, player_name, score, source FROM scores ORDER BY rank; SELECT id, source, scores_count FROM sync_events ORDER BY id DESC LIMIT 3;"
```

**Ожидаемо:** строка в `scores` с `Тест` / `100`; в `sync_events` свежая запись с `source=manual-check`.

### 4.5. MCP (Streamable HTTP)

```bash
curl -sS -X POST "$BASE/mcp?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"deploy-check","version":"1.0"}}}'
echo
```

**Ожидаемо:** ответ SSE/JSON с `serverInfo.name` = `obch-top10-mcp`, без HTML-ошибки Nginx, например фрагмент:

```text
data: {"result":{"protocolVersion":"2024-11-05",...,"serverInfo":{"name":"obch-top10-mcp","version":"1.1.0"}},"jsonrpc":"2.0","id":1}
```

Без токена (если токен включён):

```bash
curl -sS -o /dev/null -w "%{http_code}\n" -X POST "$BASE/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"x","version":"1"}}}'
```

**Ожидаемо:** `401`.

### Cursor MCP

```json
{
  "mcpServers": {
    "obch-top10": {
      "url": "https://top10.example.com/mcp?token=ДЛИННЫЙ_ТОКЕН"
    }
  }
}
```

**Ожидаемо в Cursor:** сервер `obch-top10` в статусе подключён/зелёный; инструменты `get_top10`, `sync_top10`, `save_top10` видны; вызов `get_top10` возвращает таблицу результатов.

---

## 5. Интеграция с obch

В `.env` проекта obch:

```env
MCP_TOP10_URL=https://top10.example.com/api/top10
MCP_TOP10_TOKEN=ДЛИННЫЙ_ТОКЕН
```

**Проверка, что переменные подхватились**

```bash
cd /path/to/obch
php artisan tinker --execute="echo config('app.name').PHP_EOL; echo env('MCP_TOP10_URL').PHP_EOL;"
```

(либо просто убедитесь, что в `.env` строки заданы; после правки `.env` при необходимости `php artisan config:clear`).

Отправка Топ-10:

```bash
cd /path/to/obch
php artisan stats:push-top10
```

**Ожидаемо в консоли:**

```text
Топ-10 отправлен в MCP API: https://top10.example.com/api/top10
+---+-------+------+-------+---------+-----------+
| # | Игрок | Очки | Линии | Уровень | Длит. (с) |
+---+-------+------+-------+---------+-----------+
| 1 | ...   | ...  | ...   | ...     | ...       |
...
```

Ошибка `Не задан MCP_TOP10_URL` → переменная не прописана.  
`HTTP 401` → неверный `MCP_TOP10_TOKEN`.  
`HTTP 403` → домен не в `MCP_ALLOWED_HOSTS` на стороне MCP.

**Проверка на стороне MCP после push**

```bash
curl -sS "$BASE/api/top10"; echo
```

**Ожидаемо:** `"empty":false` и те же имена/очки, что в таблице artisan.

---

## 6. Обновление версии на сервере

```bash
cd /opt/obch-top10-mcp
sudo -u obchtop10 git pull   # или заново залить файлы
sudo -u obchtop10 npm ci
sudo -u obchtop10 npx prisma migrate deploy
sudo systemctl restart obch-top10-mcp
```

**Проверка после обновления**

```bash
systemctl is-active obch-top10-mcp
curl -sS http://127.0.0.1:3920/health; echo
sudo -u obchtop10 npx prisma migrate status
```

**Ожидаемо:** `active`, health с `"database":"up"`, миграции up to date.

---

## 7. Типичные проблемы

| Симптом | Что проверить |
|---------|----------------|
| `database: down` в `/health` | `DATABASE_URL`, `systemctl status mariadb`, пароль пользователя БД |
| `401` на POST/MCP | `MCP_AUTH_TOKEN` и `Authorization: Bearer …` или `?token=` |
| `403` Host | `MCP_ALLOWED_HOSTS` содержит домен из заголовка `Host` |
| Сайт пустой после push | `php artisan stats:push-top10`, логи `journalctl -u obch-top10-mcp -n 50` |
| MCP не коннектится | HTTPS, Nginx `proxy_buffering off`, токен в URL |
| `Connection refused` на `:3920` | `systemctl status obch-top10-mcp`, логи unit |
| Nginx 502 | приложение не запущено или слушает не `127.0.0.1:3920` |

**Быстрый сбор диагностики**

```bash
systemctl is-active mariadb nginx obch-top10-mcp
curl -sS http://127.0.0.1:3920/health; echo
sudo journalctl -u obch-top10-mcp -n 50 --no-pager
sudo nginx -t
```

При нормальной работе все три службы `active`, health = `ok` + `database:up`.

---

## Краткий чеклист

1. Раздел 0: понять, что уже установлено  
2. Ubuntu + UFW (22/80/443) — `ufw status` = active  
3. Node 20 (`node -v`) + MariaDB (`SELECT VERSION()`) + Nginx (`active`)  
4. БД `obch_top10_mcp`, пользователь заходит, таблицы после migrate есть  
5. Код в `/opt/obch-top10-mcp`, `.env` заполнен  
6. `systemctl is-active obch-top10-mcp` → `active`  
7. `curl /health` → `"ok":true,"database":"up"`  
8. Nginx → 200 на `/` и `/health`  
9. POST `/api/top10` с токеном → данные в `scores`  
10. Cursor → `/mcp`, obch → `stats:push-top10` с таблицей в консоли  

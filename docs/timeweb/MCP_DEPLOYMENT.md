# MCP server — deployment runbook

Этот документ описывает шаги для развёртывания `mcp.medhistory.ru` на Timeweb.
Локальная разработка через ngrok — отдельно, см. README.

## Предусловия

- Основной [DEPLOYMENT.md](DEPLOYMENT.md) — Timeweb настроен, контейнеры поднимаются.
- DNS `medhistory.ru` управляется (нужно добавить subdomain).

## Шаг 1. DNS

Добавить у регистратора:

```
mcp.medhistory.ru.   A   194.87.140.190
```

Проверить пропагацию: `dig +short mcp.medhistory.ru` должен вернуть `194.87.140.190`.

## Шаг 2. Выпустить SSL-сертификат

На Timeweb сервере (`ssh -i ~/.ssh/medhistory_deploy root@194.87.140.190`):

```bash
cd /root/medhistory

# Standalone не подойдёт — порт 80 занят nginx. Используем webroot режим.
docker compose -f docker-compose.prod.yml run --rm --entrypoint "" certbot \
  certbot certonly --webroot -w /var/www/certbot \
  -d mcp.medhistory.ru \
  --email <твой_email> --agree-tos --no-eff-email --non-interactive

# Должно появиться:  /etc/letsencrypt/live/mcp.medhistory.ru/fullchain.pem
docker compose -f docker-compose.prod.yml run --rm --entrypoint "" certbot \
  ls /etc/letsencrypt/live/mcp.medhistory.ru/
```

Если `certbot` упадёт — скорее всего nginx ещё не знает про subdomain (server_name не совпадает). Тогда сначала **временно** добавить только HTTP-блок для `mcp.medhistory.ru` в `nginx/nginx.conf` (без `ssl_certificate` директив!), перезагрузить nginx, выпустить сертификат, потом добавить HTTPS-блок.

## Шаг 3. nginx-конфиг

Финальные блоки уже в [nginx/nginx.conf](../../nginx/nginx.conf) — два `server` блока для `mcp.medhistory.ru` (HTTP redirect + HTTPS proxy с префиксом `/mcp`).

Перезагрузить nginx:

```bash
docker compose -f docker-compose.prod.yml exec nginx nginx -t
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

## Шаг 4. Backend env

Добавить в `/root/medhistory/.env.production` (на Timeweb):

```
MCP_ENABLED=true
MCP_OAUTH_ENABLED=true
MCP_PUBLIC_URL=https://mcp.medhistory.ru
MCP_CONSENT_URL=https://medhistory.ru/oauth/consent
# MCP_BEARER_TOKEN и MCP_USER_ID не нужны в OAuth-режиме (но могут оставаться пустыми/закомментированными)
```

Обновить `docker-compose.prod.yml` если переменные не пробрасываются (см. соответствующие правки в [docker-compose.yml](../../docker-compose.yml)).

## Шаг 5. Применить миграцию OAuth-таблиц

```bash
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U medhistory_user medhistory \
  < backend/migrations/011_mcp_oauth.sql
```

## Шаг 6. Собрать и перезапустить backend

```bash
cd /root/medhistory
git pull
docker compose -f docker-compose.prod.yml build backend
docker compose -f docker-compose.prod.yml up -d backend
docker compose -f docker-compose.prod.yml logs backend --tail 50
```

В логах ожидается:
```
🔌 MCP mounted at /mcp for user ...   (если MCP_USER_ID задан, иначе строка может отличаться)
```

## Шаг 7. Smoke-тест endpoints

```bash
# OAuth metadata discovery
curl -i https://mcp.medhistory.ru/.well-known/oauth-authorization-server

# должно отдать JSON с issuer, authorization_endpoint, token_endpoint и т.п.

# Защищённый MCP endpoint без токена → 401
curl -i -X POST https://mcp.medhistory.ru/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"0"}}}'
```

## Шаг 8. Усилить DNS rebinding protection

После того как всё работает, в [backend/mcp_server/server.py](../../backend/mcp_server/server.py)
включить обратно проверку Host:

```python
transport_security=TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=["mcp.medhistory.ru"],
    allowed_origins=["https://mcp.medhistory.ru"],
),
```

Перезапустить backend.

## Шаг 9. Проверка end-to-end

1. Залогиниться в `https://medhistory.ru`.
2. Перейти на `https://medhistory.ru/settings/integrations`. URL для подключения должен показываться: `https://mcp.medhistory.ru/mcp`.
3. В claude.ai → Settings → Connectors → Add custom connector. URL: `https://mcp.medhistory.ru/mcp`. OAuth поля пустые. Нажать Add.
4. Браузер откроет `https://medhistory.ru/oauth/consent?req=...`. Нажать «Разрешить».
5. Вернётся в claude.ai. Должны появиться 11 тулов.
6. Спросить «Покажи мой профиль» — должно прилететь имя/возраст залогиненного пользователя.

## Откат

Если что-то ломает основной API — выключить MCP без отката всего деплоя:

```bash
# Снять переменные и перезапустить
sed -i 's/^MCP_OAUTH_ENABLED=true/MCP_OAUTH_ENABLED=false/' /root/medhistory/.env.production
sed -i 's/^MCP_ENABLED=true/MCP_ENABLED=false/' /root/medhistory/.env.production
docker compose -f docker-compose.prod.yml up -d backend
```

`mcp.medhistory.ru` будет возвращать 502/500 (бэкенд не примонтировал sub-app), но основной `medhistory.ru` останется рабочим.

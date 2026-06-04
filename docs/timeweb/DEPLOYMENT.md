# Production deployment — Timeweb Cloud

Продакшн развёрнут на **Timeweb Cloud** (после переезда с Yandex Cloud).

## Инфраструктура

| Параметр | Значение |
|----------|----------|
| Провайдер | Timeweb Cloud |
| IP | `194.87.140.190` (статический) |
| Регион | `ru-3` |
| Конфигурация | 2 vCPU, 4 GB RAM, 50 GB NVMe, 1000 Mbps |
| OS | Ubuntu 22.04 LTS |
| Стоимость | 1000 руб/мес |
| Swap | 2 GB |
| Firewall (ufw) | 22, 80, 443 |
| Docker | 29.4.0 |
| Docker Compose | v5.1.2 |
| Server ID (twc) | `7504157` |

## Доступ

- **SSH-ключ**: `~/.ssh/medhistory_deploy` (на локальной машине)
- **Подключение**: `ssh -i ~/.ssh/medhistory_deploy root@194.87.140.190`
- **Паролевая авторизация**: отключена
- **CLI Timeweb**: `twc` (`pipx install twc-cli`, конфиг в `~/.twcrc`)

## Flow развёртывания

```
git push → main
    ↓
workflow_dispatch (ручной запуск GH Actions)
    ↓
.github/workflows/deploy.yml
    ↓
rsync исходников → /root/medhistory/
    ↓
docker login на сервере (Docker Hub)
    ↓
docker compose build --no-cache
    ↓
docker compose up -d
```

Workflow запускается вручную через **Actions → Deploy to Production → Run workflow**.

## GitHub Secrets

| Secret | Назначение |
|--------|------------|
| `SERVER_IP` | `194.87.140.190` |
| `SERVER_USER` | `root` |
| `SSH_PRIVATE_KEY` | Приватный ключ `medhistory_deploy` |
| `DOCKER_USERNAME` | Docker Hub логин |
| `DOCKER_PASSWORD` | Docker Hub Access Token (read-only) |

## Конфигурация на сервере

```
/root/medhistory/
├── .env.production          ← секреты, НЕ в git
├── docker-compose.prod.yml
├── nginx/nginx.conf         ← основной конфиг с SSL (пока не активен)
├── nginx-temp/nginx.conf    ← временный HTTP-only конфиг
└── ... (синхронизируется из репозитория через rsync)
```

### Docker daemon

`/etc/docker/daemon.json`:
```json
{ "dns": ["8.8.8.8", "8.8.4.4", "1.1.1.1"] }
```
Нужно чтобы apt-get и npm внутри образов резолвили DNS при сборке.

## Запущенные сервисы

| Контейнер | Роль |
|-----------|------|
| `postgres` | Реляционные данные |
| `mongodb` | Метаданные документов, результаты анализов |
| `minio` | Сырые файлы |
| `backend` | FastAPI |
| `frontend` | Vite build + nginx:alpine |
| `nginx` | Reverse proxy (HTTPS в основном конфиге) |
| `certbot` | Автообновление SSL |
| `n8n` | Telegram bot workflows |
| `cloudflared` | HTTPS-туннель для n8n webhook |

## Важные фиксы по ходу миграции

1. **`node:20-alpine` → `node:20-slim`** в [frontend/Dockerfile.prod](../../frontend/Dockerfile.prod) — на Alpine musl libc `npm ci` падал с "Exit handler never called!" и не устанавливал `node_modules/.bin/`. Debian-based образ работает корректно.

2. **Docker Hub rate limit** — неавторизованные pulls ограничены 100/6ч. В workflow добавлен шаг `docker login` перед сборкой (credentials из `DOCKER_USERNAME` / `DOCKER_PASSWORD`).

3. **SSH keepalive** в workflow — `ServerAliveInterval=30`, `--progress=plain` для непрерывного вывода при долгих сборках.

4. **Swap 2 GB** — при параллельной сборке backend + frontend 4 GB RAM было впритык.

5. **DNS в Docker daemon** — без него `apt-get install` в backend-контейнере падал с `Temporary failure resolving 'deb.debian.org'`.

## Текущее состояние

- **DNS `medhistory.ru`** указывает на Timeweb IP `194.87.140.190`.
- **SSL-сертификат** Let's Encrypt выпущен, автообновление выполняет контейнер `certbot`.
- **nginx** работает по HTTPS через основной конфиг [nginx/nginx.conf](../../nginx/nginx.conf).
- Приложение доступно на https://medhistory.ru
- Поддомен `www.medhistory.ru` пока не настроен.

## TODO — `www.medhistory.ru`

1. **Добавить A-запись** `www.medhistory.ru` на `194.87.140.190`.
2. **Перевыпустить SSL** через certbot с обоими доменами:
   ```bash
   ssh root@194.87.140.190
   cd ~/medhistory
   docker compose -f docker-compose.prod.yml --env-file .env.production run --rm certbot \
     certonly --webroot -w /var/www/certbot \
     -d medhistory.ru -d www.medhistory.ru \
     --email <email> --agree-tos --no-eff-email
   ```
3. **Обновить nginx.conf** если пути к сертификатам изменятся.
4. **Перезапустить nginx**:
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.production up -d nginx
   ```

## Полезные команды

```bash
# Статус контейнеров
ssh root@194.87.140.190 "cd ~/medhistory && docker compose -f docker-compose.prod.yml --env-file .env.production ps"

# Логи сервиса
ssh root@194.87.140.190 "docker logs medhistory-backend-1 --tail=100"

# Ручной деплой через gh CLI
gh workflow run deploy.yml --repo becho96/medhistory --field ref=main --field service=all

# Просмотр последнего run
gh run list --repo becho96/medhistory --workflow=deploy.yml --limit 1

# Управление сервером через twc
twc server get 7504157
twc server reboot 7504157
```

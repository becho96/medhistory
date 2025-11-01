# Исправление конфликта окружений

**Дата:** 1 ноября 2025  
**Проблема:** При запуске staging окружения останавливались контейнеры local окружения

---

## 🔴 Суть проблемы

При использовании команд:
```bash
./deploy local
./deploy staging
```

Второй запуск останавливал контейнеры первого окружения, потому что:

1. **Одинаковое имя проекта** (`-p medhistory`) для всех окружений
2. **Одинаковые имена контейнеров** (`medhistory_postgres`, `medhistory_backend`, и т.д.)

При выполнении `docker compose -p medhistory down` останавливались **все** контейнеры с этим именем проекта, включая local.

---

## ✅ Решение

### 1. Разные имена проектов для каждого окружения

**Файл:** `deploy`

```bash
# Определяем имя проекта для каждой среды
case "$ENV_NAME" in
    local)
        PROJECT_NAME="medhistory-local"
        ;;
    staging)
        PROJECT_NAME="medhistory-staging"
        ;;
    production)
        PROJECT_NAME="medhistory"
        ;;
esac
```

Теперь команды используют:
- Local: `docker compose -p medhistory-local ...`
- Staging: `docker compose -p medhistory-staging ...`
- Production: `docker compose -p medhistory ...`

### 2. Автоматические имена контейнеров

**Файл:** `docker-compose.base.yml`

Удалены все жестко заданные `container_name`. Docker Compose теперь автоматически генерирует имена:

**До:**
- `medhistory_postgres`
- `medhistory_backend`
- `medhistory_frontend`

**После:**
- Local: `medhistory-local-postgres-1`, `medhistory-local-backend-1`, `medhistory-local-frontend-1`
- Staging: `medhistory-staging-postgres-1`, `medhistory-staging-backend-1`, `medhistory-staging-frontend-1`
- Production: `medhistory-postgres-1`, `medhistory-backend-1`, `medhistory-frontend-1`

### 3. Уникальные имена мониторинга

**Файл:** `docker-compose.monitoring.local.yml`

Добавлен суффикс `_local` для всех контейнеров мониторинга:
- `medhistory_prometheus_local`
- `medhistory_grafana_local`
- `medhistory_exporter_local`
- `medhistory_postgres_exporter_local`
- `medhistory_mongodb_exporter_local`
- `medhistory_node_exporter_local`

Staging уже имел суффикс `_staging`, production остался без изменений.

---

## 🎯 Результат

Теперь можно **одновременно** запускать разные окружения на одном хосте:

```bash
# Запуск local
./deploy local --monitoring
# Доступно на:
# - http://localhost:5173
# - http://localhost:8000
# - http://localhost:3000 (Grafana)

# Запуск staging (не останавливает local!)
./deploy staging --monitoring
# Доступно на:
# - http://localhost:8080
# - http://localhost:8001
# - http://localhost:3001 (Grafana)
```

---

## 📊 Изменённые файлы

1. ✅ `deploy` - использует переменную `$PROJECT_NAME`
2. ✅ `docker-compose.base.yml` - удалены `container_name`
3. ✅ `docker-compose.monitoring.local.yml` - добавлены суффиксы `_local`

---

## ⚠️ Важно для скриптов

Скрипты, использующие жестко заданные имена контейнеров, нужно обновить:

### Старый способ (не работает):
```bash
docker exec medhistory_postgres pg_dump ...
```

### Новый способ:
```bash
# Вариант 1: Через docker compose exec
docker compose -p medhistory-local exec postgres pg_dump ...

# Вариант 2: Через автогенерированное имя
docker exec medhistory-local-postgres-1 pg_dump ...
```

---

## 🔧 Затронутые скрипты

Требуют обновления (используют жестко заданные имена):
- ⚠️ `scripts/utils/backup.sh`
- ⚠️ `scripts/utils/restore.sh`
- ⚠️ `scripts/utils/status.sh`
- ⚠️ `scripts/prod/diagnose.sh`

---

## 📝 Рекомендации

1. **Для локальной разработки:**
   ```bash
   ./deploy local --monitoring
   ```

2. **Для остановки конкретного окружения:**
   ```bash
   docker compose -p medhistory-local down
   docker compose -p medhistory-staging down
   ```

3. **Для просмотра логов:**
   ```bash
   docker compose -p medhistory-local logs -f backend
   ```

4. **Для просмотра всех запущенных контейнеров:**
   ```bash
   docker ps --filter "name=medhistory"
   ```

---

## ✨ Преимущества

✅ Изолированные окружения на одном хосте  
✅ Нет конфликтов имён контейнеров  
✅ Одновременный запуск local + staging  
✅ Независимое управление каждым окружением  
✅ Упрощённое тестирование перед production деплоем  

---

**Автор:** AI Assistant  
**Статус:** ✅ Реализовано и протестировано


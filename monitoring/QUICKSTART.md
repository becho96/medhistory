# 🚀 Быстрый старт системы мониторинга

## Запуск на локальном окружении (Development)

### 1. Убедитесь, что основное приложение остановлено

```bash
cd "/Users/boris/Desktop/Начало/История болезни"
./scripts/local/stop.sh
```

### 2. Запустите приложение со всеми сервисами мониторинга

```bash
./scripts/local/start.sh
```

Скрипт автоматически запустит:
- Основное приложение (Backend, Frontend, БД)
- Систему мониторинга (Prometheus, Grafana, Exporters)

### 3. Дождитесь запуска всех сервисов

Первый запуск может занять 2-3 минуты для загрузки Docker образов.

### 4. Откройте дашборды Grafana

**URL:** http://localhost:3000

**Логин:** admin  
**Пароль:** admin

### 5. Проверьте дашборды

После входа в Grafana:

1. Нажмите на иконку "Dashboards" (4 квадрата) в левом меню
2. Выберите один из готовых дашбордов:
   - **Медицинский сервис - Бизнес метрики** - общая статистика
   - **Медицинский сервис - Системный обзор** - CPU, RAM, Disk
   - **Медицинский сервис - Производительность API** - RPS, латентность

### 6. Проверьте Prometheus

**URL:** http://localhost:9090

Проверьте:
- **Status → Targets** - все targets должны быть в состоянии "UP"
- **Graph** - выполните тестовый запрос: `medhistory_users_total`

### 7. Проверьте Backend метрики

**URL:** http://localhost:8000/api/v1/metrics/business

Должен вернуть JSON с метриками:
```json
{
  "timestamp": "...",
  "users": { "total": 0, "active_30d": 0, "new_30d": 0 },
  "documents": { ... },
  "interpretations": { ... },
  ...
}
```

### 8. Протестируйте с данными

1. Откройте приложение: http://localhost:5173
2. Зарегистрируйте пользователя
3. Загрузите несколько документов
4. Создайте AI интерпретацию
5. Вернитесь в Grafana и обновите дашборды - должны появиться данные

## Остановка

```bash
./scripts/local/stop.sh
```

Останавливает все сервисы, включая мониторинг.

## Полная очистка (удаление всех данных)

```bash
docker compose down -v
docker compose -f docker-compose.monitoring.yml down -v
```

⚠️ **Внимание:** Это удалит все данные, включая загруженные документы!

## Troubleshooting

### Grafana не показывает данные

1. Проверьте, что Prometheus собирает метрики:
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```

2. Проверьте логи Custom Exporter:
   ```bash
   docker logs medhistory_exporter
   ```

3. Проверьте, что Backend отвечает на запросы метрик:
   ```bash
   curl http://localhost:8000/api/v1/metrics/business
   ```

### Prometheus показывает targets как "DOWN"

1. Проверьте статус контейнеров:
   ```bash
   docker compose ps
   docker compose -f docker-compose.monitoring.yml ps
   ```

2. Проверьте логи Prometheus:
   ```bash
   docker logs medhistory_prometheus
   ```

3. Убедитесь, что все сервисы в одной Docker сети:
   ```bash
   docker network inspect medhistory_medhistory_network
   ```

### Custom Exporter не может подключиться к Backend

1. Проверьте, что Backend запущен и доступен:
   ```bash
   docker compose ps backend
   curl http://localhost:8000/health
   ```

2. Проверьте логи exporter:
   ```bash
   docker logs -f medhistory_exporter
   ```

## Полезные команды

```bash
# Просмотр логов всех сервисов мониторинга
docker compose -f docker-compose.monitoring.yml logs -f

# Просмотр логов конкретного сервиса
docker logs -f medhistory_grafana
docker logs -f medhistory_prometheus
docker logs -f medhistory_exporter

# Перезапуск только мониторинга
docker compose -f docker-compose.monitoring.yml restart

# Пересборка Custom Exporter после изменений
docker compose -f docker-compose.monitoring.yml build custom_exporter
docker compose -f docker-compose.monitoring.yml up -d custom_exporter

# Проверка доступных метрик в Prometheus
curl http://localhost:9090/api/v1/label/__name__/values | jq
```

## Доступные URL

| Сервис | URL | Логин/Пароль |
|--------|-----|--------------|
| Grafana | http://localhost:3000 | admin/admin |
| Prometheus | http://localhost:9090 | - |
| Backend API | http://localhost:8000/docs | - |
| Business Metrics | http://localhost:8000/api/v1/metrics/business | - |
| Frontend | http://localhost:5173 | - |
| MinIO Console | http://localhost:9001 | см. .env |

## Production Deployment

Для деплоя на production сервер:

```bash
./scripts/prod/deploy.sh
```

Grafana будет доступна по адресу: `https://your-domain.com/grafana`

⚠️ **Важно:** Перед деплоем на прод обязательно измените пароль администратора Grafana в `.env.production`:

```bash
GF_SECURITY_ADMIN_PASSWORD=your_secure_password_here
```


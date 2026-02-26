#!/bin/bash
# Применение миграции analyte_synonyms и seed из lab_combinations.csv
# в локальном Docker-контуре (тестовый контур).
#
# Запускает скрипты внутри контейнера backend (подключение postgres:5432).
# Требует: docker compose up -d (postgres, backend)
#
# Запуск: ./scripts/apply_analyte_mapping_local.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Подгружаем .env для POSTGRES_*
[ -f "$PROJECT_ROOT/.env.local" ] && set -a && source "$PROJECT_ROOT/.env.local" && set +a
[ -f "$PROJECT_ROOT/.env" ] && set -a && source "$PROJECT_ROOT/.env" && set +a

# Используем проект medhistory (как в Docker Desktop)
COMPOSE_PROJECT="medhistory"

# Ищем backend-контейнер
CONTAINER=$(docker compose -p "$COMPOSE_PROJECT" -f "$PROJECT_ROOT/docker-compose.yml" ps -q backend 2>/dev/null || true)
if [ -z "$CONTAINER" ]; then
  echo "Ошибка: контейнер backend не запущен. Выполните: docker compose up -d"
  exit 1
fi

echo "=========================================="
echo "Тестовый контур (локальный Docker)"
echo "Контейнер: backend"
echo "=========================================="
echo ""

# 1. Миграция (внутри backend, DATABASE_URL уже настроен)
echo "1. Применение миграции analyte_synonyms (unit, unit_lower, coefficient)..."
docker compose -p "$COMPOSE_PROJECT" -f "$PROJECT_ROOT/docker-compose.yml" exec -T backend python3 -m scripts.apply_analyte_synonym_unit_migration || exit 1
echo ""

# 2. Seed из CSV (монтируем корень проекта, DATABASE_URL из compose)
echo "2. Заполнение таблиц из lab_combinations.csv..."
docker compose -p "$COMPOSE_PROJECT" -f "$PROJECT_ROOT/docker-compose.yml" run --rm \
  -v "$PROJECT_ROOT:/project:ro" \
  -w /project \
  -e DATABASE_URL="postgresql://${POSTGRES_USER:-medhistory_user}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-medhistory}" \
  backend python3 scripts/seed_analyte_mappings_from_csv.py --csv lab_combinations.csv || exit 1
echo ""

echo "=========================================="
echo "Готово. Нажмите «Обновить кэш» в db-viewer (Маппинг анализов)"
echo "=========================================="

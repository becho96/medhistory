#!/bin/bash
# Шаг 4: Применение сгенерированного SQL к локальной PostgreSQL.
#
# Использование (с хоста):
#   bash analytics/04_apply.sh
#
# Предварительно убедись, что rebuild.sql уже скопирован в контейнер:
#   docker cp analytics/generated/rebuild.sql medhistory-backend-1:/analytics/generated/rebuild.sql

set -e

CONTAINER="medhistory-backend-1"
SQL_FILE="/analytics/generated/rebuild.sql"
PG_URL="postgresql://medhistory_user:medhistory_local_pass@postgres:5432/medhistory"

echo "📋 Копирую rebuild.sql в контейнер..."
docker cp "$(dirname "$0")/generated/rebuild.sql" "$CONTAINER:$SQL_FILE"

echo "🔄 Применяю SQL..."
docker exec "$CONTAINER" psql "$PG_URL" -f "$SQL_FILE"

echo ""
echo "✅ Готово. Теперь:"
echo "   1. Перезапусти backend для сброса кэша нормализации:"
echo "      docker restart $CONTAINER"
echo "   2. Проверь покрытие:"
echo "      docker exec $CONTAINER python /analytics/check_analyte_coverage.py"

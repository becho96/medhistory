#!/bin/bash
# Проверка крайних записей в analyte_synonyms на production
# Подключение через SSH к серверу 93.77.182.26

SERVER="93.77.182.26"
USER="yc-user"
PG_CMD='docker exec medhistory-postgres-1 psql -U medhistory_user -d medhistory -t -A'

# Альтернативное имя контейнера (Docker Compose v1)
PG_CMD_ALT='docker exec medhistory_postgres_1 psql -U medhistory_user -d medhistory -t -A'

echo "=========================================="
echo "Проверка analyte_synonyms на production"
echo "Сервер: $SERVER"
echo "=========================================="
echo ""

# Определить имя контейнера
CONTAINER=$(ssh -l $USER $SERVER 'docker ps --format "{{.Names}}" | grep -i postgres' 2>/dev/null | head -1)
if [ -z "$CONTAINER" ]; then
  echo "❌ Не найден контейнер PostgreSQL"
  exit 1
fi
echo "📦 Контейнер PostgreSQL: $CONTAINER"
echo ""

# 1. Общая статистика
echo "📊 1. Общая статистика:"
ssh -l $USER $SERVER "docker exec $CONTAINER psql -U medhistory_user -d medhistory -c \"
SELECT 
  (SELECT COUNT(*) FROM analyte_synonyms) as total_synonyms,
  (SELECT COUNT(*) FROM analyte_standards) as total_standards,
  (SELECT COUNT(DISTINCT analyte_id) FROM analyte_synonyms) as analytes_with_synonyms;
\""
echo ""

# 2. Последние 20 записей (сортировка по created_at)
echo "📋 2. Последние 20 записей в analyte_synonyms (ORDER BY created_at DESC):"
ssh -l $USER $SERVER "docker exec $CONTAINER psql -U medhistory_user -d medhistory -c \"
SELECT s.id, s.synonym, s.synonym_lower, a.canonical_name, s.created_at
FROM analyte_synonyms s
LEFT JOIN analyte_standards a ON a.id = s.analyte_id
ORDER BY s.created_at DESC
LIMIT 20;
\""
echo ""

# 3. Проверка целостности: synonym_lower = LOWER(synonym)
echo "🔍 3. Проверка: synonym_lower должен быть = LOWER(synonym):"
ssh -l $USER $SERVER "docker exec $CONTAINER psql -U medhistory_user -d medhistory -c \"
SELECT id, synonym, synonym_lower,
  CASE WHEN synonym_lower = LOWER(synonym) THEN 'OK' ELSE '❌ MISMATCH' END as check_result
FROM analyte_synonyms
ORDER BY created_at DESC
LIMIT 20;
\""
echo ""

# 4. Записи с невалидным analyte_id (orphans)
echo "⚠️  4. Записи с analyte_id не из analyte_standards (сироты):"
ssh -l $USER $SERVER "docker exec $CONTAINER psql -U medhistory_user -d medhistory -c \"
SELECT s.id, s.synonym, s.analyte_id
FROM analyte_synonyms s
LEFT JOIN analyte_standards a ON a.id = s.analyte_id
WHERE a.id IS NULL;
\""
ORPHAN_COUNT=$(ssh -l $USER $SERVER "docker exec $CONTAINER psql -U medhistory_user -d medhistory -t -c \"SELECT COUNT(*) FROM analyte_synonyms s LEFT JOIN analyte_standards a ON a.id = s.analyte_id WHERE a.id IS NULL;\"" 2>/dev/null | tr -d ' ')
if [ "$ORPHAN_COUNT" = "0" ] || [ -z "$ORPHAN_COUNT" ]; then
  echo "   (нет сирот — все analyte_id валидны)"
else
  echo "   Найдено сирот: $ORPHAN_COUNT"
fi
echo ""

# 5. Пустые или null critical fields
echo "⚠️  5. Записи с пустым synonym или synonym_lower:"
ssh -l $USER $SERVER "docker exec $CONTAINER psql -U medhistory_user -d medhistory -c \"
SELECT id, synonym, synonym_lower, analyte_id
FROM analyte_synonyms
WHERE synonym IS NULL OR synonym = '' OR synonym_lower IS NULL OR synonym_lower = '';
\""
echo ""

# 6. Дубликаты по synonym_lower (нарушение unique)
echo "📋 6. Проверка уникальности synonym_lower (дубликаты):"
ssh -l $USER $SERVER "docker exec $CONTAINER psql -U medhistory_user -d medhistory -c \"
SELECT synonym_lower, COUNT(*) as cnt
FROM analyte_synonyms
GROUP BY synonym_lower
HAVING COUNT(*) > 1;
\""
echo ""
echo "✅ Проверка завершена"

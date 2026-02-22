#!/bin/bash
# Исправление synonym_lower: привести к LOWER(synonym) для записей с MISMATCH
# Запускать на production через SSH

SERVER="93.77.182.26"
USER="yc-user"

CONTAINER=$(ssh -l $USER $SERVER 'docker ps --format "{{.Names}}" | grep -i postgres' 2>/dev/null | head -1)
if [ -z "$CONTAINER" ]; then
  echo "❌ Не найден контейнер PostgreSQL"
  exit 1
fi

echo "📦 Контейнер: $CONTAINER"
echo ""
echo "🔧 Записи, требующие исправления (synonym_lower != LOWER(synonym)):"
ssh -l $USER $SERVER "docker exec $CONTAINER psql -U medhistory_user -d medhistory -c \"
SELECT COUNT(*) as to_fix FROM analyte_synonyms WHERE synonym_lower != LOWER(synonym);
\""
echo ""
echo "📋 Пример (первые 5):"
ssh -l $USER $SERVER "docker exec $CONTAINER psql -U medhistory_user -d medhistory -c \"
SELECT synonym, synonym_lower, LOWER(synonym) as correct_lower
FROM analyte_synonyms WHERE synonym_lower != LOWER(synonym)
LIMIT 5;
\""
echo ""
read -p "Исправить? (y/n): " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
  echo "Отменено."
  exit 0
fi

echo "Обновление synonym_lower..."
ssh -l $USER $SERVER "docker exec $CONTAINER psql -U medhistory_user -d medhistory -c \"
UPDATE analyte_synonyms 
SET synonym_lower = LOWER(synonym)
WHERE synonym_lower != LOWER(synonym);
\""

UPDATED=$(ssh -l $USER $SERVER "docker exec $CONTAINER psql -U medhistory_user -d medhistory -t -c \"SELECT COUNT(*) FROM analyte_synonyms WHERE synonym_lower != LOWER(synonym);\"" 2>/dev/null | tr -d ' ')
echo "✅ Готово. Оставшихся несовпадений: $UPDATED"
echo ""
echo "⚠️  После исправления перезапустите backend для обновления кэша:"
echo "   ssh -l $USER $SERVER 'cd ~/medhistory && docker compose -f docker-compose.prod.yml restart backend'"

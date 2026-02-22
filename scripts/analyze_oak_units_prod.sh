#!/bin/bash
# Анализ недостающих unit_conversions для 8 анализов ОАК на production
# Подключается по SSH к серверу
# Запуск: ./scripts/analyze_oak_units_prod.sh

set -e
SERVER="93.77.182.26"
USER="yc-user"

CONTAINER_PG=$(ssh -l $USER $SERVER 'docker ps --format "{{.Names}}" | grep -i postgres' 2>/dev/null | head -1)
CONTAINER_MONGO=$(ssh -l $USER $SERVER 'docker ps --format "{{.Names}}" | grep -i mongo' 2>/dev/null | head -1)

if [ -z "$CONTAINER_PG" ] || [ -z "$CONTAINER_MONGO" ]; then
  echo "❌ Не найдены контейнеры PostgreSQL или MongoDB"
  exit 1
fi

echo "=========================================="
echo "Анализ unit_conversions для ОАК [Production]"
echo "Сервер: $SERVER | PG: $CONTAINER_PG | Mongo: $CONTAINER_MONGO"
echo "=========================================="
echo ""

# 1. OAK анализы и их unit_conversions
echo "📋 1. ОАК анализы и текущие unit_conversions:"
ssh -l $USER $SERVER "docker exec $CONTAINER_PG psql -U medhistory_user -d medhistory -c \"
SELECT a.canonical_name, a.standard_unit,
  COALESCE(string_agg(uc.from_unit, ', ' ORDER BY uc.from_unit), '(нет)') as units_in_table
FROM analyte_standards a
LEFT JOIN unit_conversions uc ON uc.analyte_id = a.id
WHERE a.canonical_name IN (
  'Эозинофилы (абс)', 'Лимфоциты (%)', 'Моноциты (%)', 'Нейтрофилы (%)',
  'Базофилы (абс)', 'Моноциты (абс)', 'Нейтрофилы (абс)', 'Лимфоциты (абс)'
)
GROUP BY a.id, a.canonical_name, a.standard_unit
ORDER BY a.canonical_name;
\""
echo ""

# 2. Единицы из документов MongoDB (анализы ОАК: эозин, лимф, моноцит, нейтрофил, базофил)
echo "📋 2. (test_name, unit) в документах — анализы ОАК:"
ssh -l $USER $SERVER 'cd ~/medhistory 2>/dev/null; set -a; [ -f .env.production ] && . ./.env.production; set +a;
  docker exec '"$CONTAINER_MONGO"' mongosh -u "${MONGO_INITDB_ROOT_USERNAME:-admin}" -p "${MONGO_PASSWORD}" --authenticationDatabase admin medhistory --quiet --eval "
db.document_metadata.aggregate([
  {\$match: {\"extracted_data.lab_results\": {\$exists: true, \$ne: []}}},
  {\$unwind: \"\$extracted_data.lab_results\"},
  {\$match: {
    \"extracted_data.lab_results.test_name\": {
      \$regex: \"эозин|лимфоцит|моноцит|нейтрофил|базофил|абсолютное|относительное\",
      \$options: \"i\"
    }
  }},
  {\$group: {
    _id: {
      name: \"\$extracted_data.lab_results.test_name\",
      unit: {\$ifNull: [\"\$extracted_data.lab_results.unit\", \"\"]}
    },
    count: {\$sum: 1}
  }},
  {\$sort: {\"_id.name\": 1}},
  {\$limit: 60}
]).forEach(r => print(r._id.name + \" | unit=\" + r._id.unit + \" | \" + r.count));
"'
echo ""

# 3. Рекомендуемые unit для добавления (из типичных вариантов)
echo "=========================================="
echo "📝 3. Рекомендуемые unit для unit_conversions:"
echo ""
echo "Анализы в % (Лимфоциты %, Моноциты %, Нейтрофилы %, Эозинофилы %, Базофилы %):"
echo "  standard_unit: %"
echo "  Добавить from_unit: '%' (если нет)"
echo ""
echo "Анализы в абс (×10⁹/л):"
echo "  standard_unit: ×10⁹/л"
echo "  Варианты в документах: 10*9/л, 10^9/л, х10^9/л, тыс/мкл"
echo "  Добавить недостающие (coefficient=1.0)"
echo ""
echo "Проверка наличия '%' и '10*9/л' в unit_conversions для ОАК:"
ssh -l $USER $SERVER "docker exec $CONTAINER_PG psql -U medhistory_user -d medhistory -c \"
SELECT a.canonical_name, uc.from_unit
FROM analyte_standards a
JOIN unit_conversions uc ON uc.analyte_id = a.id
WHERE a.canonical_name IN (
  'Эозинофилы (абс)', 'Лимфоциты (%)', 'Моноциты (%)', 'Нейтрофилы (%)',
  'Базофилы (абс)', 'Моноциты (абс)', 'Нейтрофилы (абс)', 'Лимфоциты (абс)'
)
AND (uc.from_unit_lower IN ('%', '10*9/л', '10^9/л', 'х10^9/л', 'тыс/мкл', '×10⁹/л')
     OR uc.from_unit ILIKE '%10%9%')
ORDER BY a.canonical_name, uc.from_unit;
\""
echo ""
echo "✅ Для добавления единиц используйте db-viewer (Маппинг анализов) или SQL INSERT в unit_conversions"

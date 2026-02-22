#!/bin/bash
# Добавление недостающих unit_conversions для ОАК на production
# Подключается по SSH к серверу и выполняет INSERT
# Запуск: ./scripts/add_oak_unit_conversions_prod.sh

set -e
SERVER="93.77.182.26"
USER="yc-user"

CONTAINER_PG=$(ssh -l $USER $SERVER 'docker ps --format "{{.Names}}" | grep -i postgres' 2>/dev/null | head -1)
if [ -z "$CONTAINER_PG" ]; then
  echo "❌ Не найден контейнер PostgreSQL"
  exit 1
fi

echo "=========================================="
echo "Добавление unit_conversions для ОАК [Production]"
echo "Сервер: $SERVER | PG: $CONTAINER_PG"
echo "=========================================="
echo ""

# Добавляем: 10^9/л, x10*9/л, количество/100 клеток
# ON CONFLICT DO NOTHING — не дублируем, если уже есть

echo "📝 Добавление недостающих единиц..."

ssh -l $USER $SERVER "docker exec -i $CONTAINER_PG psql -U medhistory_user -d medhistory" << 'EOSQL'
-- 1. 10^9/л для 5 анализов (абс)
INSERT INTO unit_conversions (id, analyte_id, from_unit, from_unit_lower, coefficient)
SELECT gen_random_uuid(), a.id, '10^9/л', '10^9/л', 1.0
FROM analyte_standards a
WHERE a.canonical_name IN ('Лимфоциты (абс)', 'Нейтрофилы (абс)', 'Моноциты (абс)', 'Эозинофилы (абс)', 'Базофилы (абс)')
ON CONFLICT (analyte_id, from_unit_lower) DO NOTHING;

-- 2. x10*9/л (латинская x) для Нейтрофилы (абс)
INSERT INTO unit_conversions (id, analyte_id, from_unit, from_unit_lower, coefficient)
SELECT gen_random_uuid(), a.id, 'x10*9/л', 'x10*9/л', 1.0
FROM analyte_standards a
WHERE a.canonical_name = 'Нейтрофилы (абс)'
ON CONFLICT (analyte_id, from_unit_lower) DO NOTHING;

-- 3. количество/100 клеток (= %) для анализов в %
INSERT INTO unit_conversions (id, analyte_id, from_unit, from_unit_lower, coefficient)
SELECT gen_random_uuid(), a.id, 'количество/100 клеток', 'количество/100 клеток', 1.0
FROM analyte_standards a
WHERE a.canonical_name IN ('Лимфоциты (%)', 'Моноциты (%)', 'Нейтрофилы (%)')
ON CONFLICT (analyte_id, from_unit_lower) DO NOTHING;
EOSQL

echo ""
echo "✅ Готово."
echo ""
echo "⚠️  Перезапустите backend для обновления кэша:"
echo "   ssh -l $USER $SERVER 'cd ~/medhistory && docker compose -f docker-compose.prod.yml restart backend'"

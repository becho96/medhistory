#!/bin/bash

# Быстрая проверка состояния продакшн БД

set -e

echo "🔍 Проверка состояния продакшн БД..."
echo

# Проверяем количество записей в таблицах
ssh yc-user@158.160.99.232 'docker exec medhistory-postgres-1 psql -U medhistory_user -d medhistory' <<'SQL'
\echo '=== Состояние справочника ==='
\echo ''

SELECT 
    'analyte_categories' as table_name,
    COUNT(*) as count 
FROM analyte_categories
UNION ALL
SELECT 
    'analyte_standards',
    COUNT(*) 
FROM analyte_standards
UNION ALL
SELECT 
    'analyte_synonyms',
    COUNT(*) 
FROM analyte_synonyms
ORDER BY table_name;

\echo ''
\echo '=== Топ-10 анализов с синонимами ==='
\echo ''

SELECT 
    a.canonical_name,
    COUNT(s.id) as synonym_count
FROM analyte_standards a
LEFT JOIN analyte_synonyms s ON s.analyte_id = a.id
GROUP BY a.canonical_name
ORDER BY synonym_count DESC
LIMIT 10;
SQL

echo
echo "✅ Проверка завершена"

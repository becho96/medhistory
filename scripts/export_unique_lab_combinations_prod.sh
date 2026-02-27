#!/bin/bash
# Обёртка для export_unique_lab_combinations.py --prod
# Рекомендуемый способ: python3 scripts/export_unique_lab_combinations.py --prod -o output.csv
# Этот скрипт — запасной вариант (запуск через SSH на сервере).
# Запуск: ./scripts/export_unique_lab_combinations_prod.sh [output.csv]

set -e
OUTPUT="${1:-unique_lab_combinations.csv}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Экспорт lab combinations [Production]"
echo "Выходной файл: $OUTPUT"
echo "=========================================="
echo ""
echo "Запуск скрипта локально с SSH-туннелем..."
echo ""

cd "$PROJECT_ROOT"
python3 scripts/export_unique_lab_combinations.py --prod -o "$OUTPUT"

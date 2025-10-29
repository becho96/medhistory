#!/bin/bash

# MedHistory Stop Script

echo "🛑 Остановка MedHistory..."
echo ""

docker compose stop

echo ""
echo "✅ Все сервисы остановлены"
echo ""
echo "💡 Для полного удаления контейнеров (данные сохранятся):"
echo "   docker compose down"
echo ""
echo "⚠️  Для удаления ВСЕХ данных (включая документы!):"
echo "   docker compose down -v"


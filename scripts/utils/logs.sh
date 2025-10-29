#!/bin/bash

# ==================================================
# MedHistory Logs Viewer
# ==================================================
# Удобный просмотр логов всех или отдельных сервисов
#
# Использование:
#   ./scripts/logs.sh [service_name] [options]
#
# Примеры:
#   ./scripts/logs.sh              # Все логи
#   ./scripts/logs.sh backend      # Только backend
#   ./scripts/logs.sh -f           # Follow режим
#   ./scripts/logs.sh backend -f   # Backend в follow режиме
# ==================================================

# Определяем compose файл
if [ -f .env.production ] && [ -f docker-compose.prod.yml ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    ENV_FILE=".env.production"
else
    COMPOSE_FILE="docker-compose.yml"
    ENV_FILE=".env"
fi

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}📋 MedHistory Logs${NC}"
echo -e "${YELLOW}Compose file: ${COMPOSE_FILE}${NC}"
echo ""

# Если нет аргументов, показываем все логи
if [ $# -eq 0 ]; then
    docker compose -f "${COMPOSE_FILE}" logs --tail=100
    exit 0
fi

# Проверяем флаг -f (follow)
FOLLOW_FLAG=""
SERVICE=""

for arg in "$@"; do
    if [ "$arg" = "-f" ] || [ "$arg" = "--follow" ]; then
        FOLLOW_FLAG="-f"
    else
        SERVICE="$arg"
    fi
done

# Показываем логи
if [ -n "$SERVICE" ]; then
    if [ -n "$FOLLOW_FLAG" ]; then
        docker compose -f "${COMPOSE_FILE}" logs -f "${SERVICE}"
    else
        docker compose -f "${COMPOSE_FILE}" logs --tail=100 "${SERVICE}"
    fi
else
    if [ -n "$FOLLOW_FLAG" ]; then
        docker compose -f "${COMPOSE_FILE}" logs -f
    else
        docker compose -f "${COMPOSE_FILE}" logs --tail=100
    fi
fi


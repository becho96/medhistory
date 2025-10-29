#!/bin/bash

# ==================================================
# Скрипт обновления Backend
# ==================================================

set -e

# Загрузка конфигурации
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../config.sh"

# Параметры из аргументов (переопределяют config.sh)
SERVER_IP="${1:-$PROD_SERVER_IP}"
SSH_USER="${2:-$PROD_SERVER_USER}"
SERVER="${SSH_USER}@${SERVER_IP}"

print_info "🔧 Обновление Backend..."
echo ""

# Синхронизация
echo -e "${COLOR_YELLOW}📤 Синхронизация файлов с сервером...${COLOR_NC}"
rsync -avz --progress \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude 'venv' \
  --exclude 'uploads' \
  "${PROJECT_ROOT}/backend/" "${SERVER}:${REMOTE_PROJECT_DIR}/backend/"

# Пересборка на сервере
echo ""
echo -e "${COLOR_YELLOW}🔨 Пересборка Docker образа...${COLOR_NC}"
ssh "${SERVER}" "cd ${REMOTE_PROJECT_DIR} && \
  docker compose -f docker-compose.prod.yml build --no-cache backend"

# Перезапуск
echo ""
echo -e "${COLOR_YELLOW}🔄 Перезапуск контейнера...${COLOR_NC}"
ssh "${SERVER}" "cd ${REMOTE_PROJECT_DIR} && \
  docker compose -f docker-compose.prod.yml up -d backend"

# Ожидание
echo ""
echo -e "${COLOR_YELLOW}⏳ Ожидание запуска (15 секунд)...${COLOR_NC}"
sleep 15

# Проверка
echo ""
echo -e "${COLOR_YELLOW}✅ Проверка health endpoint...${COLOR_NC}"
if curl -s "http://${SERVER_IP}/health" | grep -q "healthy"; then
    print_success "Backend работает корректно"
else
    print_error "Ошибка! Проверьте логи:"
    ssh "${SERVER}" "cd ${REMOTE_PROJECT_DIR} && docker compose -f docker-compose.prod.yml logs --tail=50 backend"
    exit 1
fi

echo ""
print_success "Backend успешно обновлен!"
echo -e "${COLOR_BLUE}🌐 API Docs: http://${SERVER_IP}/docs${COLOR_NC}"
echo ""


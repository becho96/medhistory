#!/bin/bash

# ==================================================
# Скрипт обновления Frontend
# ==================================================

set -e

# Загрузка конфигурации
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../config.sh"

# Параметры из аргументов (переопределяют config.sh)
SERVER_IP="${1:-$PROD_SERVER_IP}"
SSH_USER="${2:-$PROD_SERVER_USER}"
SERVER="${SSH_USER}@${SERVER_IP}"

print_info "🎨 Обновление Frontend..."
echo ""

# Проверка сборки локально
echo -e "${COLOR_YELLOW}📦 Проверка сборки локально...${COLOR_NC}"
cd "${PROJECT_ROOT}/frontend"
if npm run build; then
    print_success "Локальная сборка успешна"
else
    print_error "Ошибка сборки! Проверьте код."
    exit 1
fi
cd "${PROJECT_ROOT}"

# Синхронизация
echo ""
echo -e "${COLOR_YELLOW}📤 Синхронизация файлов с сервером...${COLOR_NC}"
rsync -avz --progress \
  --exclude 'node_modules' \
  --exclude 'dist' \
  "${PROJECT_ROOT}/frontend/" "${SERVER}:${REMOTE_PROJECT_DIR}/frontend/"

# Пересборка на сервере
echo ""
echo -e "${COLOR_YELLOW}🔨 Пересборка Docker образа...${COLOR_NC}"
ssh "${SERVER}" "cd ${REMOTE_PROJECT_DIR} && \
  docker compose -f docker-compose.prod.yml build --no-cache frontend"

# Перезапуск
echo ""
echo -e "${COLOR_YELLOW}🔄 Перезапуск контейнера...${COLOR_NC}"
ssh "${SERVER}" "cd ${REMOTE_PROJECT_DIR} && \
  docker compose -f docker-compose.prod.yml up -d frontend"

# Ожидание
echo ""
echo -e "${COLOR_YELLOW}⏳ Ожидание запуска (10 секунд)...${COLOR_NC}"
sleep 10

# Проверка
echo ""
echo -e "${COLOR_YELLOW}✅ Проверка...${COLOR_NC}"
ssh "${SERVER}" "docker ps | grep medhistory_frontend"

echo ""
print_success "Frontend успешно обновлен!"
echo -e "${COLOR_BLUE}🌐 Проверьте: http://${SERVER_IP}${COLOR_NC}"
echo ""


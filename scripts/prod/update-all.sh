#!/bin/bash

# ==================================================
# Скрипт полного обновления приложения
# ==================================================

set -e

# Загрузка конфигурации
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../config.sh"

# Параметры из аргументов (переопределяют config.sh)
SERVER_IP="${1:-$PROD_SERVER_IP}"
SSH_USER="${2:-$PROD_SERVER_USER}"
SERVER="${SSH_USER}@${SERVER_IP}"

print_info "🔄 Полное обновление MedHistory..."
echo ""

# Подтверждение
echo -e "${COLOR_YELLOW}⚠️  Это полное обновление приложения.${COLOR_NC}"
echo -e "${COLOR_YELLOW}Приложение будет недоступно ~1-2 минуты.${COLOR_NC}"
read -p "Продолжить? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Отменено"
    exit 0
fi

# Бэкап
echo ""
echo -e "${COLOR_YELLOW}💾 Создание бэкапа...${COLOR_NC}"
ssh "${SERVER}" "cd ${REMOTE_PROJECT_DIR} && ./scripts/utils/backup.sh ${REMOTE_BACKUP_DIR}"
print_success "Бэкап создан"

# Синхронизация
echo ""
echo -e "${COLOR_YELLOW}📤 Синхронизация всех файлов...${COLOR_NC}"
rsync -avz --progress \
  --exclude 'node_modules' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude 'frontend/dist' \
  --exclude 'backend/uploads' \
  --exclude '.git' \
  "${PROJECT_ROOT}/" "${SERVER}:${REMOTE_PROJECT_DIR}/"

print_success "Файлы синхронизированы"

# Остановка
echo ""
echo -e "${COLOR_YELLOW}🛑 Остановка приложения...${COLOR_NC}"
ssh "${SERVER}" "cd ${REMOTE_PROJECT_DIR} && \
  docker compose -f docker-compose.prod.yml down"

# Пересборка
echo ""
echo -e "${COLOR_YELLOW}🔨 Пересборка всех образов...${COLOR_NC}"
ssh "${SERVER}" "cd ${REMOTE_PROJECT_DIR} && \
  docker compose -f docker-compose.prod.yml build --no-cache"

# Запуск
echo ""
echo -e "${COLOR_YELLOW}🚀 Запуск приложения...${COLOR_NC}"
ssh "${SERVER}" "cd ${REMOTE_PROJECT_DIR} && \
  docker compose -f docker-compose.prod.yml --env-file .env.production up -d"

# Ожидание
echo ""
echo -e "${COLOR_YELLOW}⏳ Ожидание запуска всех сервисов (45 секунд)...${COLOR_NC}"
sleep 45

# Проверка
echo ""
echo -e "${COLOR_YELLOW}✅ Проверка сервисов...${COLOR_NC}"

# Проверка контейнеров
echo -e "${COLOR_BLUE}Статус контейнеров:${COLOR_NC}"
ssh "${SERVER}" "docker ps --format 'table {{.Names}}\t{{.Status}}' | grep medhistory"

# Проверка health
echo ""
if curl -s "http://${SERVER_IP}/health" | grep -q "healthy"; then
    print_success "Health check: OK"
else
    print_error "Health check: FAILED"
    echo -e "${COLOR_YELLOW}Логи backend:${COLOR_NC}"
    ssh "${SERVER}" "cd ${REMOTE_PROJECT_DIR} && docker compose -f docker-compose.prod.yml logs --tail=30 backend"
    exit 1
fi

echo ""
print_success "Приложение успешно обновлено!"
echo ""
echo -e "${COLOR_BLUE}🌐 URL:${COLOR_NC}"
echo "  - Приложение: http://${SERVER_IP}"
echo "  - API Docs:   http://${SERVER_IP}/docs"
echo ""
print_warning "Рекомендуется проверить работу всех функций"
echo ""


#!/bin/bash

# ==================================================
# MedHistory Deployment Script
# ==================================================
# Автоматический деплой на production сервер
#
# Использование:
#   ./scripts/prod/deploy.sh
#
# Настройка через переменные окружения или config.sh
# ==================================================

set -e

# Загрузка конфигурации
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../config.sh"

# Параметры из аргументов (переопределяют config.sh)
SERVER_IP="${1:-$PROD_SERVER_IP}"
SSH_USER="${2:-$PROD_SERVER_USER}"
SERVER="${SSH_USER}@${SERVER_IP}"

echo -e "${COLOR_GREEN}🚀 Начало деплоя MedHistory${COLOR_NC}"
echo -e "${COLOR_YELLOW}Сервер: ${SERVER}${COLOR_NC}"
echo -e "${COLOR_YELLOW}Время: $(date)${COLOR_NC}"
echo ""

# Проверка подключения к серверу
echo -e "${COLOR_YELLOW}🔍 Проверка подключения к серверу...${COLOR_NC}"
if ! ssh -o ConnectTimeout=5 "${SERVER}" "echo 'Connected'" > /dev/null 2>&1; then
    print_error "Не удается подключиться к серверу"
    echo "  Проверьте IP адрес и SSH доступ"
    exit 1
fi
print_success "Подключение установлено"

# Проверка наличия .env.production
if [ ! -f "${PROJECT_ROOT}/.env.production" ]; then
    print_error "Файл .env.production не найден"
    echo "  Создайте файл .env.production в корне проекта"
    exit 1
fi

# Проверка критических переменных
echo -e "${COLOR_YELLOW}🔍 Проверка переменных окружения...${COLOR_NC}"
if grep -q "your_secure_postgres_password_here" "${PROJECT_ROOT}/.env.production" || \
   grep -q "your-openrouter-api-key-here" "${PROJECT_ROOT}/.env.production"; then
    print_error "В .env.production остались дефолтные значения"
    echo "  Заполните все переменные в .env.production"
    exit 1
fi
print_success "Переменные окружения настроены"

# Создание временного архива проекта
echo ""
echo -e "${COLOR_YELLOW}📦 Создание архива проекта...${COLOR_NC}"
TEMP_ARCHIVE="/tmp/medhistory_deploy_$(date +%Y%m%d_%H%M%S).tar.gz"

tar --exclude='node_modules' \
    --exclude='backend/__pycache__' \
    --exclude='backend/app/__pycache__' \
    --exclude='frontend/dist' \
    --exclude='.git' \
    --exclude='backups' \
    --exclude='.env' \
    -czf "${TEMP_ARCHIVE}" \
    -C "$(dirname "${PROJECT_ROOT}")" \
    "$(basename "${PROJECT_ROOT}")"

print_success "Архив создан: ${TEMP_ARCHIVE}"

# Загрузка на сервер
echo ""
echo -e "${COLOR_YELLOW}⬆️  Загрузка на сервер...${COLOR_NC}"
ssh "${SERVER}" "mkdir -p ~/medhistory_temp"
scp "${TEMP_ARCHIVE}" "${SERVER}:~/medhistory_temp/project.tar.gz"
scp "${PROJECT_ROOT}/.env.production" "${SERVER}:~/medhistory_temp/.env.production"
print_success "Файлы загружены"

# Удаление временного архива
rm "${TEMP_ARCHIVE}"

# Развертывание на сервере
echo ""
echo -e "${COLOR_YELLOW}🔧 Развертывание на сервере...${COLOR_NC}"

ssh "${SERVER}" bash << 'ENDSSH'
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Backup старой версии если есть
if [ -d ~/medhistory ]; then
    echo -e "${YELLOW}📦 Создание бэкапа старой версии...${NC}"
    if [ -f ~/medhistory/scripts/utils/backup.sh ]; then
        cd ~/medhistory
        ./scripts/utils/backup.sh ~/backups || echo "Бэкап не удался (возможно первый запуск)"
    fi
    
    echo -e "${YELLOW}🛑 Остановка старых контейнеров...${NC}"
    cd ~/medhistory
    docker compose -f docker-compose.prod.yml down || echo "Контейнеры не запущены"
    
    echo -e "${YELLOW}📁 Архивация старой версии...${NC}"
    mv ~/medhistory ~/medhistory_old_$(date +%Y%m%d_%H%M%S)
fi

# Распаковка новой версии
echo -e "${YELLOW}📦 Распаковка новой версии...${NC}"
cd ~
tar -xzf ~/medhistory_temp/project.tar.gz
mv "$(tar -tzf ~/medhistory_temp/project.tar.gz | head -1 | cut -f1 -d"/")" medhistory
cp ~/medhistory_temp/.env.production ~/medhistory/.env.production

# Очистка temp
rm -rf ~/medhistory_temp

# Запуск контейнеров
echo -e "${YELLOW}🚀 Запуск контейнеров...${NC}"
cd ~/medhistory
docker compose -f docker-compose.prod.yml --env-file .env.production build --no-cache
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# Ожидание запуска
echo -e "${YELLOW}⏳ Ожидание запуска сервисов (30 сек)...${NC}"
sleep 30

# Проверка статуса
echo -e "${YELLOW}🔍 Проверка статуса...${NC}"
docker compose -f docker-compose.prod.yml ps

echo -e "${GREEN}✅ Деплой завершен!${NC}"
ENDSSH

echo ""
print_success "Деплой успешно завершен!"
echo ""
echo -e "${COLOR_YELLOW}🌐 Проверьте работу приложения:${COLOR_NC}"
echo "   Frontend: http://${SERVER_IP}"
echo "   API Docs: http://${SERVER_IP}/docs"
echo "   Health:   http://${SERVER_IP}/health"
echo ""
echo -e "${COLOR_YELLOW}📊 Просмотр логов:${COLOR_NC}"
echo "   ssh ${SERVER} 'cd ~/medhistory && docker compose -f docker-compose.prod.yml logs -f'"
echo ""


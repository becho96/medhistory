#!/bin/bash

# ==================================================
# MedHistory Restore Script
# ==================================================
# Восстанавливает данные из бэкапа
#
# Использование:
#   ./scripts/restore.sh <backup_file.tar.gz>
#
# Пример:
#   ./scripts/restore.sh ./backups/medhistory_backup_20241019_120000.tar.gz
# ==================================================

set -e

# Проверка аргументов
if [ $# -eq 0 ]; then
    echo "Ошибка: Не указан файл бэкапа"
    echo "Использование: $0 <backup_file.tar.gz>"
    exit 1
fi

BACKUP_FILE="$1"

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Проверка файла
if [ ! -f "${BACKUP_FILE}" ]; then
    echo -e "${RED}✗ Ошибка: Файл бэкапа не найден: ${BACKUP_FILE}${NC}"
    exit 1
fi

echo -e "${YELLOW}⚠️  ВНИМАНИЕ: Восстановление удалит все текущие данные!${NC}"
echo -e "${YELLOW}Файл бэкапа: ${BACKUP_FILE}${NC}"
echo ""
read -p "Вы уверены? Введите 'yes' для продолжения: " confirm

if [ "$confirm" != "yes" ]; then
    echo -e "${YELLOW}Отменено пользователем${NC}"
    exit 0
fi

echo ""
echo -e "${GREEN}🔄 Начало восстановления MedHistory${NC}"
echo -e "${YELLOW}Время: $(date)${NC}"

# Создать временную директорию
TEMP_DIR=$(mktemp -d)
trap "rm -rf ${TEMP_DIR}" EXIT

echo ""
echo -e "${YELLOW}📦 Распаковка бэкапа...${NC}"
tar -xzf "${BACKUP_FILE}" -C "${TEMP_DIR}"
BACKUP_NAME=$(ls "${TEMP_DIR}")
BACKUP_PATH="${TEMP_DIR}/${BACKUP_NAME}"
echo -e "${GREEN}✓${NC} Бэкап распакован"

# Проверка контейнеров
if ! docker ps | grep -q "medhistory_postgres"; then
    echo -e "${RED}✗ Ошибка: PostgreSQL контейнер не запущен${NC}"
    echo "   Запустите контейнеры: docker-compose up -d"
    exit 1
fi

if ! docker ps | grep -q "medhistory_mongodb"; then
    echo -e "${RED}✗ Ошибка: MongoDB контейнер не запущен${NC}"
    exit 1
fi

if ! docker ps | grep -q "medhistory_minio"; then
    echo -e "${RED}✗ Ошибка: MinIO контейнер не запущен${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}📊 Восстановление PostgreSQL...${NC}"
docker exec -i medhistory_postgres psql -U medhistory_user -d medhistory -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker exec -i medhistory_postgres psql -U medhistory_user -d medhistory < "${BACKUP_PATH}/postgres.sql"
echo -e "${GREEN}✓${NC} PostgreSQL восстановлен"

echo ""
echo -e "${YELLOW}📊 Восстановление MongoDB...${NC}"
docker cp "${BACKUP_PATH}/mongodb" medhistory_mongodb:/tmp/mongodb_restore
docker exec medhistory_mongodb mongorestore \
    --username admin \
    --password "${MONGO_PASSWORD:-mongodb_secure_pass}" \
    --authenticationDatabase admin \
    --db medhistory \
    --drop \
    /tmp/mongodb_restore/medhistory
docker exec medhistory_mongodb rm -rf /tmp/mongodb_restore
echo -e "${GREEN}✓${NC} MongoDB восстановлен"

echo ""
echo -e "${YELLOW}📦 Восстановление MinIO (файлы)...${NC}"
docker exec medhistory_minio mc alias set local http://localhost:9000 \
    "${MINIO_ROOT_USER:-minio_admin}" \
    "${MINIO_ROOT_PASSWORD:-minio_secure_pass_123}"

docker cp "${BACKUP_PATH}/minio" medhistory_minio:/tmp/minio_restore
docker exec medhistory_minio rm -rf /data/medhistory-files
docker exec medhistory_minio mkdir -p /data/medhistory-files
docker exec medhistory_minio cp -r /tmp/minio_restore/* /data/medhistory-files/
docker exec medhistory_minio rm -rf /tmp/minio_restore
echo -e "${GREEN}✓${NC} MinIO восстановлен"

echo ""
echo -e "${YELLOW}🔄 Перезапуск сервисов...${NC}"
docker-compose restart backend
echo -e "${GREEN}✓${NC} Сервисы перезапущены"

echo ""
echo -e "${GREEN}✅ Восстановление успешно завершено!${NC}"
echo -e "${YELLOW}Время:${NC} $(date)"
echo ""
echo -e "${YELLOW}💡 Совет:${NC} Проверьте работу приложения:"
echo "   http://localhost:5173"


#!/bin/bash

# ==================================================
# MedHistory Backup Script
# ==================================================
# Создает полный бэкап всех данных приложения
#
# Использование:
#   ./scripts/backup.sh [output_directory]
#
# Пример:
#   ./scripts/backup.sh ./backups
# ==================================================

set -e

# Настройки
BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="medhistory_backup_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔄 Начало создания бэкапа MedHistory${NC}"
echo -e "${YELLOW}Время: $(date)${NC}"
echo ""

# Создать директорию для бэкапа
mkdir -p "${BACKUP_PATH}"
echo -e "${GREEN}✓${NC} Создана директория: ${BACKUP_PATH}"

# Проверка, что контейнеры запущены
if ! docker ps | grep -q "medhistory_postgres"; then
    echo -e "${RED}✗ Ошибка: PostgreSQL контейнер не запущен${NC}"
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
echo -e "${YELLOW}📊 Бэкап PostgreSQL...${NC}"
docker exec medhistory_postgres pg_dump -U medhistory_user medhistory > "${BACKUP_PATH}/postgres.sql"
echo -e "${GREEN}✓${NC} PostgreSQL бэкап создан: postgres.sql"

echo ""
echo -e "${YELLOW}📊 Бэкап MongoDB...${NC}"
docker exec medhistory_mongodb mongodump \
    --username admin \
    --password "${MONGO_PASSWORD:-mongodb_secure_pass}" \
    --authenticationDatabase admin \
    --db medhistory \
    --out /tmp/mongodb_backup

docker cp medhistory_mongodb:/tmp/mongodb_backup "${BACKUP_PATH}/mongodb"
docker exec medhistory_mongodb rm -rf /tmp/mongodb_backup
echo -e "${GREEN}✓${NC} MongoDB бэкап создан: mongodb/"

echo ""
echo -e "${YELLOW}📦 Бэкап MinIO (файлы)...${NC}"
docker exec medhistory_minio mc alias set local http://localhost:9000 \
    "${MINIO_ROOT_USER:-minio_admin}" \
    "${MINIO_ROOT_PASSWORD:-minio_secure_pass_123}"

docker exec medhistory_minio mc mirror /data/medhistory-files /tmp/minio_backup
docker cp medhistory_minio:/tmp/minio_backup "${BACKUP_PATH}/minio"
docker exec medhistory_minio rm -rf /tmp/minio_backup
echo -e "${GREEN}✓${NC} MinIO бэкап создан: minio/"

echo ""
echo -e "${YELLOW}🗜️  Создание архива...${NC}"
cd "${BACKUP_DIR}"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
rm -rf "${BACKUP_NAME}"
echo -e "${GREEN}✓${NC} Архив создан: ${BACKUP_NAME}.tar.gz"

# Информация о размере
BACKUP_SIZE=$(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)
echo ""
echo -e "${GREEN}✅ Бэкап успешно создан!${NC}"
echo -e "${YELLOW}Файл:${NC} ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo -e "${YELLOW}Размер:${NC} ${BACKUP_SIZE}"
echo -e "${YELLOW}Время:${NC} $(date)"

echo ""
echo -e "${YELLOW}💡 Совет:${NC} Скопируйте бэкап в безопасное место:"
echo "   scp ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz user@backup-server:/backups/"
echo ""
echo -e "${YELLOW}💡 Для восстановления используйте:${NC}"
echo "   ./scripts/restore.sh ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"


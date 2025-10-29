#!/bin/bash

# ==================================================
# MedHistory Status Checker
# ==================================================
# Проверка статуса всех сервисов и их здоровья
# ==================================================

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     MedHistory System Status Check    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Определяем compose файл
if [ -f .env.production ] && [ -f docker-compose.prod.yml ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    ENV_FILE=".env.production"
    echo -e "${YELLOW}Environment: PRODUCTION${NC}"
else
    COMPOSE_FILE="docker-compose.yml"
    ENV_FILE=".env"
    echo -e "${YELLOW}Environment: DEVELOPMENT${NC}"
fi

echo ""
echo -e "${YELLOW}📊 Docker Containers:${NC}"
docker compose -f "${COMPOSE_FILE}" ps

echo ""
echo -e "${YELLOW}💾 Disk Usage:${NC}"
df -h | grep -E "Filesystem|/$"

echo ""
echo -e "${YELLOW}🧠 Memory Usage:${NC}"
free -h

echo ""
echo -e "${YELLOW}💻 CPU Load:${NC}"
uptime

echo ""
echo -e "${YELLOW}🐳 Docker Resources:${NC}"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

echo ""
echo -e "${YELLOW}🔍 Health Checks:${NC}"

# Проверка backend health
if curl -s http://localhost/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Backend API: healthy"
else
    echo -e "${RED}✗${NC} Backend API: unhealthy"
fi

# Проверка frontend
if curl -s http://localhost/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Frontend: healthy"
else
    echo -e "${RED}✗${NC} Frontend: unhealthy"
fi

# Проверка PostgreSQL
if docker exec medhistory_postgres pg_isready -U medhistory_user > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} PostgreSQL: healthy"
else
    echo -e "${RED}✗${NC} PostgreSQL: unhealthy"
fi

# Проверка MongoDB
if docker exec medhistory_mongodb mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} MongoDB: healthy"
else
    echo -e "${RED}✗${NC} MongoDB: unhealthy"
fi

# Проверка MinIO
if curl -s http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} MinIO: healthy"
else
    echo -e "${RED}✗${NC} MinIO: unhealthy"
fi

echo ""
echo -e "${YELLOW}📈 Database Sizes:${NC}"

# PostgreSQL размер базы
PG_SIZE=$(docker exec medhistory_postgres psql -U medhistory_user -d medhistory -t -c "SELECT pg_size_pretty(pg_database_size('medhistory'));" 2>/dev/null | xargs)
if [ -n "$PG_SIZE" ]; then
    echo -e "  PostgreSQL: ${PG_SIZE}"
fi

# MongoDB размер базы
MONGO_SIZE=$(docker exec medhistory_mongodb mongosh --quiet --eval "db.stats().dataSize" medhistory 2>/dev/null)
if [ -n "$MONGO_SIZE" ]; then
    MONGO_SIZE_MB=$(echo "scale=2; $MONGO_SIZE / 1024 / 1024" | bc)
    echo -e "  MongoDB: ${MONGO_SIZE_MB} MB"
fi

# MinIO размер бакета
MINIO_SIZE=$(docker exec medhistory_minio du -sh /data/medhistory-files 2>/dev/null | cut -f1)
if [ -n "$MINIO_SIZE" ]; then
    echo -e "  MinIO (files): ${MINIO_SIZE}"
fi

echo ""
echo -e "${YELLOW}📝 Recent Logs (errors only):${NC}"
docker compose -f "${COMPOSE_FILE}" logs --tail=20 | grep -i "error" || echo "  No recent errors"

echo ""
echo -e "${GREEN}✅ Status check complete${NC}"


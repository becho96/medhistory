#!/bin/bash

# ==================================================
# MedHistory Server Setup Script
# ==================================================
# Настройка нового сервера для деплоя MedHistory
# Запускать на свежей Ubuntu 22.04 ВМ
#
# Использование:
#   curl -sSL https://your-repo/scripts/setup-server.sh | bash
#   или
#   ./scripts/setup-server.sh
# ==================================================

set -e

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Настройка сервера для MedHistory${NC}"
echo -e "${YELLOW}Время: $(date)${NC}"
echo ""

# Проверка что скрипт запущен не от root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}✗ Не запускайте скрипт от root${NC}"
    echo "  Запустите от обычного пользователя с sudo правами"
    exit 1
fi

# Проверка Ubuntu
if [ ! -f /etc/lsb-release ]; then
    echo -e "${RED}✗ Этот скрипт предназначен для Ubuntu${NC}"
    exit 1
fi

# Обновление системы
echo -e "${YELLOW}📦 Обновление системы...${NC}"
sudo apt update
sudo apt upgrade -y
echo -e "${GREEN}✓${NC} Система обновлена"

# Установка базовых утилит
echo ""
echo -e "${YELLOW}🔧 Установка базовых утилит...${NC}"
sudo apt install -y \
    curl \
    wget \
    git \
    nano \
    vim \
    htop \
    net-tools \
    ufw \
    fail2ban \
    unattended-upgrades
echo -e "${GREEN}✓${NC} Базовые утилиты установлены"

# Настройка автоматических обновлений безопасности
echo ""
echo -e "${YELLOW}🔒 Настройка автоматических обновлений безопасности...${NC}"
sudo dpkg-reconfigure -plow unattended-upgrades
echo -e "${GREEN}✓${NC} Автообновления настроены"

# Установка Docker
echo ""
echo -e "${YELLOW}🐳 Установка Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
    
    # Добавление текущего пользователя в группу docker
    sudo usermod -aG docker $USER
    echo -e "${GREEN}✓${NC} Docker установлен"
else
    echo -e "${YELLOW}Docker уже установлен${NC}"
fi

# Установка Docker Compose
echo ""
echo -e "${YELLOW}🐳 Установка Docker Compose...${NC}"
if ! docker compose version &> /dev/null; then
    sudo apt install -y docker-compose-plugin
    echo -e "${GREEN}✓${NC} Docker Compose установлен"
else
    echo -e "${YELLOW}Docker Compose уже установлен${NC}"
fi

# Настройка Firewall (UFW)
echo ""
echo -e "${YELLOW}🔥 Настройка Firewall...${NC}"
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS

# Подтверждение UFW
echo "y" | sudo ufw enable
echo -e "${GREEN}✓${NC} Firewall настроен"

# Настройка fail2ban
echo ""
echo -e "${YELLOW}🛡️  Настройка fail2ban...${NC}"
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
echo -e "${GREEN}✓${NC} fail2ban настроен"

# Создание директорий
echo ""
echo -e "${YELLOW}📁 Создание директорий...${NC}"
mkdir -p ~/medhistory
mkdir -p ~/backups
echo -e "${GREEN}✓${NC} Директории созданы"

# Настройка swap (если нет)
echo ""
echo -e "${YELLOW}💾 Проверка swap...${NC}"
if [ $(swapon --show | wc -l) -eq 0 ]; then
    echo -e "${YELLOW}Создание swap файла (4GB)...${NC}"
    sudo fallocate -l 4G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo -e "${GREEN}✓${NC} Swap создан"
else
    echo -e "${YELLOW}Swap уже настроен${NC}"
fi

# Настройка системных лимитов
echo ""
echo -e "${YELLOW}⚙️  Настройка системных лимитов...${NC}"
sudo tee -a /etc/security/limits.conf > /dev/null << EOF
* soft nofile 65536
* hard nofile 65536
* soft nproc 65536
* hard nproc 65536
EOF
echo -e "${GREEN}✓${NC} Системные лимиты настроены"

# Настройка timezone
echo ""
echo -e "${YELLOW}🕐 Настройка timezone...${NC}"
sudo timedatectl set-timezone Europe/Moscow
echo -e "${GREEN}✓${NC} Timezone: $(timedatectl | grep "Time zone")"

# Установка дополнительных утилит для мониторинга
echo ""
echo -e "${YELLOW}📊 Установка утилит мониторинга...${NC}"
sudo apt install -y \
    iotop \
    iftop \
    ncdu \
    nethogs
echo -e "${GREEN}✓${NC} Утилиты мониторинга установлены"

# Информация о версиях
echo ""
echo -e "${GREEN}✅ Настройка сервера завершена!${NC}"
echo ""
echo -e "${YELLOW}📋 Установленные версии:${NC}"
echo "  Docker: $(docker --version)"
echo "  Docker Compose: $(docker compose version)"
echo "  Ubuntu: $(lsb_release -d | cut -f2)"
echo ""

# Важное уведомление
echo -e "${YELLOW}⚠️  ВАЖНО:${NC}"
echo "  1. Перезагрузите сервер для применения всех настроек:"
echo "     ${GREEN}sudo reboot${NC}"
echo ""
echo "  2. После перезагрузки проверьте Docker:"
echo "     ${GREEN}docker ps${NC}"
echo ""
echo "  3. Готовы к деплою! Используйте:"
echo "     ${GREEN}./scripts/deploy.sh <server_ip> <ssh_user>${NC}"
echo ""
echo -e "${YELLOW}💡 Рекомендации:${NC}"
echo "  - Настройте SSH ключи для безопасного доступа"
echo "  - Смените SSH порт с 22 на другой"
echo "  - Настройте регулярные бэкапы (cron)"
echo "  - Установите мониторинг (Prometheus + Grafana)"
echo ""


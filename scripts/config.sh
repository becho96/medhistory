#!/bin/bash

# ==================================================
# MedHistory Scripts Configuration
# ==================================================
# Конфигурационный файл для всех скриптов управления
# 
# Использование:
#   source scripts/config.sh
# ==================================================

# Продакшн сервер (Яндекс.Облако)
export PROD_SERVER_IP="${PROD_SERVER_IP:-46.21.244.23}"
export PROD_SERVER_USER="${PROD_SERVER_USER:-yc-user}"
export PROD_SERVER="${PROD_SERVER_USER}@${PROD_SERVER_IP}"

# Локальные пути
export PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export SCRIPTS_DIR="${PROJECT_ROOT}/scripts"

# Удаленные пути
export REMOTE_PROJECT_DIR="${REMOTE_PROJECT_DIR:-~/medhistory}"
export REMOTE_BACKUP_DIR="${REMOTE_BACKUP_DIR:-~/backups}"

# Docker Compose файлы
export DEV_COMPOSE_FILE="docker-compose.yml"
export PROD_COMPOSE_FILE="docker-compose.prod.yml"

# Цвета для вывода
export COLOR_GREEN='\033[0;32m'
export COLOR_YELLOW='\033[1;33m'
export COLOR_RED='\033[0;31m'
export COLOR_BLUE='\033[0;34m'
export COLOR_NC='\033[0m' # No Color

# Функции для красивого вывода
print_success() {
    echo -e "${COLOR_GREEN}✅ $1${COLOR_NC}"
}

print_error() {
    echo -e "${COLOR_RED}❌ $1${COLOR_NC}"
}

print_warning() {
    echo -e "${COLOR_YELLOW}⚠️  $1${COLOR_NC}"
}

print_info() {
    echo -e "${COLOR_BLUE}ℹ️  $1${COLOR_NC}"
}

print_header() {
    echo -e "${COLOR_BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${COLOR_NC}"
    echo -e "${COLOR_BLUE}$1${COLOR_NC}"
    echo -e "${COLOR_BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${COLOR_NC}"
}

# Проверка конфигурации
check_config() {
    if [ -z "$PROD_SERVER_IP" ]; then
        print_error "PROD_SERVER_IP не задан!"
        return 1
    fi
    
    if [ -z "$PROD_SERVER_USER" ]; then
        print_error "PROD_SERVER_USER не задан!"
        return 1
    fi
    
    return 0
}

# Определение текущей среды
detect_environment() {
    if [ -f "${PROJECT_ROOT}/.env.production" ] && [ -f "${PROJECT_ROOT}/docker-compose.prod.yml" ]; then
        echo "production"
    else
        echo "development"
    fi
}

# Экспорт функций
export -f print_success
export -f print_error
export -f print_warning
export -f print_info
export -f print_header
export -f check_config
export -f detect_environment


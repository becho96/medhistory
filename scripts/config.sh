#!/bin/bash

# ==================================================
# MedHistory Scripts Configuration
# ==================================================
# Конфигурационный файл для всех скриптов управления
# 
# Использование:
#   source scripts/config.sh [environment]
#   где environment: local, staging, production
# ==================================================

# Определение текущей среды (по умолчанию local)
export DEPLOY_ENV="${1:-${DEPLOY_ENV:-local}}"

# Локальные пути
export PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export SCRIPTS_DIR="${PROJECT_ROOT}/scripts"
export ENVIRONMENTS_DIR="${PROJECT_ROOT}/environments"

# Docker Compose файлы
export BASE_COMPOSE_FILE="docker-compose.base.yml"
export LOCAL_COMPOSE_FILE="docker-compose.local.yml"
export STAGING_COMPOSE_FILE="docker-compose.staging.yml"
export PROD_COMPOSE_FILE="docker-compose.prod.yml"
export MONITORING_LOCAL_COMPOSE_FILE="docker-compose.monitoring.local.yml"
export MONITORING_STAGING_COMPOSE_FILE="docker-compose.monitoring.staging.yml"
export MONITORING_PROD_COMPOSE_FILE="docker-compose.monitoring.prod.yml"

# Конфигурация для разных сред
case "$DEPLOY_ENV" in
  local|dev|development)
    export ENV_NAME="local"
    export ENV_FILE="${PROJECT_ROOT}/.env.local"
    export COMPOSE_FILES="-f ${BASE_COMPOSE_FILE} -f ${LOCAL_COMPOSE_FILE}"
    export MONITORING_COMPOSE="-f ${MONITORING_LOCAL_COMPOSE_FILE}"
    export IS_REMOTE=false
    ;;
    
  staging|stage|test)
    export ENV_NAME="staging"
    export ENV_FILE="${PROJECT_ROOT}/.env.staging"
    export COMPOSE_FILES="-f ${BASE_COMPOSE_FILE} -f ${STAGING_COMPOSE_FILE}"
    export MONITORING_COMPOSE="-f ${MONITORING_STAGING_COMPOSE_FILE}"
    export IS_REMOTE=false
    ;;
    
  production|prod|live)
    export ENV_NAME="production"
    export ENV_FILE="${PROJECT_ROOT}/.env.production"
    export COMPOSE_FILES="-f ${BASE_COMPOSE_FILE} -f ${PROD_COMPOSE_FILE}"
    export MONITORING_COMPOSE="-f ${MONITORING_PROD_COMPOSE_FILE}"
    export IS_REMOTE=true
    
    # Продакшн сервер (Яндекс.Облако)
    export PROD_SERVER_IP="${PROD_SERVER_IP:-46.21.244.23}"
    export PROD_SERVER_USER="${PROD_SERVER_USER:-yc-user}"
    export PROD_SERVER="${PROD_SERVER_USER}@${PROD_SERVER_IP}"
    
    # Удаленные пути
    export REMOTE_PROJECT_DIR="${REMOTE_PROJECT_DIR:-~/medhistory}"
    export REMOTE_BACKUP_DIR="${REMOTE_BACKUP_DIR:-~/backups}"
    ;;
    
  *)
    echo "❌ Неизвестная среда: $DEPLOY_ENV"
    echo "   Доступные среды: local, staging, production"
    exit 1
    ;;
esac

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

# Проверка наличия .env файла для среды
check_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        print_error "Файл конфигурации не найден: $ENV_FILE"
        print_info "Создайте файл из шаблона:"
        print_info "  cp ${ENVIRONMENTS_DIR}/${ENV_NAME}.env $ENV_FILE"
        print_info "  # Затем отредактируйте $ENV_FILE и заполните все значения"
        return 1
    fi
    return 0
}

# Проверка продакшн конфигурации
check_prod_config() {
    if [ "$IS_REMOTE" = true ]; then
        if [ -z "$PROD_SERVER_IP" ]; then
            print_error "PROD_SERVER_IP не задан в $ENV_FILE"
            return 1
        fi
        
        if [ -z "$PROD_SERVER_USER" ]; then
            print_error "PROD_SERVER_USER не задан в $ENV_FILE"
            return 1
        fi
    fi
    
    return 0
}

# Загрузка переменных окружения из файла
load_env() {
    if [ -f "$ENV_FILE" ]; then
        set -a
        source "$ENV_FILE"
        set +a
        print_success "Загружена конфигурация: $ENV_NAME"
    else
        print_error "Файл конфигурации не найден: $ENV_FILE"
        return 1
    fi
}

# Вывод информации о текущей среде
print_env_info() {
    print_header "Информация о среде"
    echo "Среда:           $ENV_NAME"
    echo "Конфиг файл:     $ENV_FILE"
    echo "Compose файлы:   $COMPOSE_FILES"
    echo "Удаленный деплой: $IS_REMOTE"
    if [ "$IS_REMOTE" = true ]; then
        echo "Сервер:          $PROD_SERVER"
    fi
    echo ""
}

# Экспорт функций
export -f print_success
export -f print_error
export -f print_warning
export -f print_info
export -f print_header
export -f check_env_file
export -f check_prod_config
export -f load_env
export -f print_env_info


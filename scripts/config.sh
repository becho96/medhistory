#!/bin/bash

# ==================================================
# MedHistory Scripts Configuration
# ==================================================
# Конфигурационный файл для скриптов управления
# ==================================================

# Локальные пути
export PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export SCRIPTS_DIR="${PROJECT_ROOT}/scripts"
export ENV_FILE="${PROJECT_ROOT}/.env.local"

# Цвета для вывода
export COLOR_GREEN='\033[0;32m'
export COLOR_YELLOW='\033[1;33m'
export COLOR_RED='\033[0;31m'
export COLOR_BLUE='\033[0;34m'
export COLOR_NC='\033[0m'

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

# Проверка наличия .env файла
check_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        print_error "Файл конфигурации не найден: $ENV_FILE"
        print_info "Создайте файл .env.local с необходимыми переменными"
        return 1
    fi
    return 0
}

# Загрузка переменных окружения из файла
load_env() {
    if [ -f "$ENV_FILE" ]; then
        set -a
        source "$ENV_FILE"
        set +a
        print_success "Загружена конфигурация"
    else
        print_error "Файл конфигурации не найден: $ENV_FILE"
        return 1
    fi
}

# Экспорт функций
export -f print_success
export -f print_error
export -f print_warning
export -f print_info
export -f print_header
export -f check_env_file
export -f load_env

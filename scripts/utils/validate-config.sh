#!/bin/bash

# ==================================================
# MedHistory Configuration Validator
# ==================================================
# Проверяет корректность конфигурации перед деплоем
#
# Использование:
#   ./scripts/utils/validate-config.sh
# ==================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env.local"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

print_error() {
    echo -e "${RED}❌ $1${NC}"
    ((ERRORS++))
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((WARNINGS++))
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_check() {
    echo -e "   🔍 Проверка: $1"
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 Валидация конфигурации"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Проверка существования файла
print_check "Существование файла конфигурации"
if [ ! -f "$ENV_FILE" ]; then
    print_error "Файл не найден: $ENV_FILE"
    echo ""
    echo "Создайте файл .env.local с необходимыми переменными"
    exit 1
fi
print_success "Файл найден: $ENV_FILE"
echo ""

# Загрузка переменных
set -a
source "$ENV_FILE"
set +a

# ==================================================
# Обязательные переменные
# ==================================================
echo "📋 Проверка обязательных переменных"
echo ""

REQUIRED_VARS=(
    "POSTGRES_PASSWORD"
    "MONGO_PASSWORD"
    "MINIO_ROOT_PASSWORD"
    "OPENROUTER_API_KEY"
    "JWT_SECRET"
)

for var in "${REQUIRED_VARS[@]}"; do
    print_check "$var"
    if [ -z "${!var}" ]; then
        print_error "$var не задана"
    else
        print_success "$var задана"
    fi
done
echo ""

# ==================================================
# Проверка дефолтных значений
# ==================================================
echo "🔒 Проверка безопасности"
echo ""

INSECURE_PATTERNS=(
    "your_openrouter_api_key_here"
    "change_me"
)

print_check "Поиск небезопасных паттернов"
FOUND_INSECURE=false
for pattern in "${INSECURE_PATTERNS[@]}"; do
    if grep -qi "$pattern" "$ENV_FILE"; then
        print_error "Найден небезопасный паттерн: '$pattern'"
        FOUND_INSECURE=true
    fi
done

if [ "$FOUND_INSECURE" = false ]; then
    print_success "Небезопасные паттерны не найдены"
fi
echo ""

# ==================================================
# Проверка OpenRouter API Key
# ==================================================
echo "🔑 Проверка API ключей"
echo ""

print_check "OPENROUTER_API_KEY"
if [ -z "$OPENROUTER_API_KEY" ]; then
    print_error "OPENROUTER_API_KEY не задан"
elif [[ "$OPENROUTER_API_KEY" =~ ^sk-or- ]]; then
    print_success "OPENROUTER_API_KEY имеет правильный формат"
else
    print_warning "OPENROUTER_API_KEY может иметь неправильный формат (должен начинаться с 'sk-or-')"
fi
echo ""

# ==================================================
# Проверка Docker
# ==================================================
echo "🐳 Проверка Docker окружения"
echo ""

print_check "Docker установлен"
if command -v docker &> /dev/null; then
    print_success "Docker найден: $(docker --version)"
else
    print_error "Docker не установлен"
fi

print_check "Docker Compose установлен"
if command -v docker compose &> /dev/null; then
    print_success "Docker Compose найден"
elif command -v docker-compose &> /dev/null; then
    print_success "Docker Compose (legacy) найден"
else
    print_error "Docker Compose не установлен"
fi

print_check "Docker daemon запущен"
if docker info &> /dev/null; then
    print_success "Docker daemon работает"
else
    print_error "Docker daemon не запущен"
fi

echo ""

# ==================================================
# Итоговая статистика
# ==================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Результаты валидации"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ Все проверки пройдены успешно!${NC}"
    echo ""
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Найдено предупреждений: $WARNINGS${NC}"
    echo ""
    echo "Можно продолжать, но рекомендуется исправить предупреждения"
    exit 0
else
    echo -e "${RED}❌ Найдено ошибок: $ERRORS${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Найдено предупреждений: $WARNINGS${NC}"
    fi
    echo ""
    echo "Исправьте ошибки в файле: $ENV_FILE"
    echo ""
    exit 1
fi

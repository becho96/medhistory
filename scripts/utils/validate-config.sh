#!/bin/bash

# ==================================================
# MedHistory Configuration Validator
# ==================================================
# Проверяет корректность конфигурации перед деплоем
#
# Использование:
#   ./scripts/utils/validate-config.sh [environment]
# ==================================================

set -e

ENV_NAME="${1:-local}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

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

# Определение файла конфигурации
case "$ENV_NAME" in
    local|dev|development)
        ENV_FILE="${PROJECT_ROOT}/.env.local"
        ;;
    staging|stage|test)
        ENV_FILE="${PROJECT_ROOT}/.env.staging"
        ;;
    production|prod|live)
        ENV_FILE="${PROJECT_ROOT}/.env.production"
        ;;
    *)
        echo -e "${RED}❌ Неизвестная среда: $ENV_NAME${NC}"
        exit 1
        ;;
esac

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 Валидация конфигурации: $(echo $ENV_NAME | tr '[:lower:]' '[:upper:]')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Проверка существования файла
print_check "Существование файла конфигурации"
if [ ! -f "$ENV_FILE" ]; then
    print_error "Файл не найден: $ENV_FILE"
    echo ""
    echo "Создайте файл из шаблона:"
    echo "  cp ${PROJECT_ROOT}/environments/${ENV_NAME}.env $ENV_FILE"
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
    "ENVIRONMENT"
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
echo "🔒 Проверка безопасности паролей"
echo ""

# Для local среды проверка мягче
if [ "$ENV_NAME" = "local" ]; then
    INSECURE_PATTERNS=(
        "your_openrouter_api_key_here"
        "change_me"
    )
else
    INSECURE_PATTERNS=(
        "your_openrouter_api_key_here"
        "change_me"
        "your_secure"
        "your_very_secure"
        "example"
        "test"
        "123456"
    )
fi

print_check "Поиск небезопасных паролей"
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
# Проверка длины паролей
# ==================================================
echo "📏 Проверка длины секретов"
echo ""

# JWT Secret
print_check "Длина JWT_SECRET"
if [ -n "$JWT_SECRET" ]; then
    JWT_LEN=${#JWT_SECRET}
    if [ $JWT_LEN -lt 32 ]; then
        if [ "$ENV_NAME" = "local" ]; then
            print_warning "JWT_SECRET короткий ($JWT_LEN символов). Минимум 32 для production"
        else
            print_error "JWT_SECRET слишком короткий ($JWT_LEN символов). Минимум 32"
        fi
    else
        print_success "JWT_SECRET достаточной длины ($JWT_LEN символов)"
    fi
fi

# PostgreSQL Password
print_check "Длина POSTGRES_PASSWORD"
if [ -n "$POSTGRES_PASSWORD" ]; then
    PG_LEN=${#POSTGRES_PASSWORD}
    if [ $PG_LEN -lt 16 ] && [ "$ENV_NAME" != "local" ]; then
        print_warning "POSTGRES_PASSWORD короткий ($PG_LEN символов). Рекомендуется минимум 16"
    else
        print_success "POSTGRES_PASSWORD достаточной длины"
    fi
fi

# MongoDB Password
print_check "Длина MONGO_PASSWORD"
if [ -n "$MONGO_PASSWORD" ]; then
    MONGO_LEN=${#MONGO_PASSWORD}
    if [ $MONGO_LEN -lt 16 ] && [ "$ENV_NAME" != "local" ]; then
        print_warning "MONGO_PASSWORD короткий ($MONGO_LEN символов). Рекомендуется минимум 16"
    else
        print_success "MONGO_PASSWORD достаточной длины"
    fi
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
# Проверка URL
# ==================================================
echo "🌐 Проверка URL"
echo ""

print_check "VITE_API_URL"
if [ -n "$VITE_API_URL" ]; then
    if [[ "$VITE_API_URL" =~ ^https?:// ]]; then
        print_success "VITE_API_URL: $VITE_API_URL"
    else
        print_warning "VITE_API_URL не начинается с http:// или https://"
    fi
else
    print_error "VITE_API_URL не задан"
fi
echo ""

# ==================================================
# Production специфичные проверки
# ==================================================
if [ "$ENV_NAME" = "production" ]; then
    echo "🚀 Production специфичные проверки"
    echo ""
    
    print_check "PROD_SERVER_IP"
    if [ -z "$PROD_SERVER_IP" ]; then
        print_error "PROD_SERVER_IP не задан"
    else
        # Проверка формата IP
        if [[ "$PROD_SERVER_IP" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
            print_success "PROD_SERVER_IP: $PROD_SERVER_IP"
        else
            print_warning "PROD_SERVER_IP может иметь неправильный формат"
        fi
    fi
    
    print_check "PROD_SERVER_USER"
    if [ -z "$PROD_SERVER_USER" ]; then
        print_error "PROD_SERVER_USER не задан"
    else
        print_success "PROD_SERVER_USER: $PROD_SERVER_USER"
    fi
    
    print_check "ENVIRONMENT должен быть 'production'"
    if [ "$ENVIRONMENT" != "production" ]; then
        print_error "ENVIRONMENT должен быть 'production', текущее значение: '$ENVIRONMENT'"
    else
        print_success "ENVIRONMENT: production"
    fi
    
    echo ""
fi

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
    if [ "$ENV_NAME" = "production" ]; then
        echo "Рекомендуется исправить предупреждения перед production деплоем"
        exit 1
    else
        echo "Можно продолжать, но рекомендуется исправить предупреждения"
        exit 0
    fi
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


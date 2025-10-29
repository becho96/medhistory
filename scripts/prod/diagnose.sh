#!/bin/bash

# ==================================================
# Скрипт диагностики проблем на продакшне
# ==================================================

set -e

# Загрузка конфигурации
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../config.sh"

# Параметры из аргументов (переопределяют config.sh)
SERVER_IP="${1:-$PROD_SERVER_IP}"
SSH_USER="${2:-$PROD_SERVER_USER}"
SERVER="${SSH_USER}@${SERVER_IP}"

echo "🔍 Диагностика проблем на продакшне"
echo "📡 Сервер: ${SERVER}"
echo "================================================"
echo ""

# Шаг 1: Проверка логов backend
print_header "ШАГ 1: Проверка логов Backend (последние 100 строк)"
ssh "${SERVER}" "cd ${REMOTE_PROJECT_DIR} && docker compose -f docker-compose.prod.yml logs backend --tail=100" 2>&1 | tail -50
echo ""

# Шаг 2: Проверка статуса контейнеров
print_header "ШАГ 2: Статус Docker контейнеров"
ssh "${SERVER}" 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
echo ""

# Шаг 3: Проверка переменных окружения backend
print_header "ШАГ 3: Переменные окружения Backend"
echo "DATABASE_URL:"
ssh "${SERVER}" 'docker exec medhistory_backend env | grep DATABASE_URL' 2>&1 || print_error "Не найдена"
echo ""
echo "JWT_SECRET:"
ssh "${SERVER}" 'docker exec medhistory_backend env | grep JWT_SECRET | sed "s/=.*$/=***masked***/"' 2>&1 || print_error "Не найдена"
echo ""
echo "ENVIRONMENT:"
ssh "${SERVER}" 'docker exec medhistory_backend env | grep ENVIRONMENT' 2>&1 || print_error "Не найдена"
echo ""

# Шаг 4: Проверка базы данных PostgreSQL
print_header "ШАГ 4: Проверка PostgreSQL"

echo "4.1. Список таблиц:"
ssh "${SERVER}" 'docker exec medhistory_postgres psql -U medhistory_user -d medhistory -c "\dt"' 2>&1
echo ""

echo "4.2. Структура таблицы users:"
ssh "${SERVER}" 'docker exec medhistory_postgres psql -U medhistory_user -d medhistory -c "\d users"' 2>&1 || print_error "Таблица users не существует!"
echo ""

echo "4.3. Проверка расширения UUID:"
ssh "${SERVER}" 'docker exec medhistory_postgres psql -U medhistory_user -d medhistory -c "SELECT * FROM pg_extension WHERE extname = '"'"'uuid-ossp'"'"';"' 2>&1
echo ""

# Шаг 5: Тест API регистрации напрямую через backend
print_header "ШАГ 5: Тест API регистрации напрямую"
TIMESTAMP=$(date +%s)
TEST_EMAIL="test_${TIMESTAMP}@test.com"

echo "Попытка регистрации с email: $TEST_EMAIL"
ssh "${SERVER}" "docker exec medhistory_backend curl -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{\"email\":\"$TEST_EMAIL\",\"password\":\"testpass123\",\"full_name\":\"Test User\"}' \
  -w '\nHTTP Status: %{http_code}\n' 2>&1"
echo ""

# Шаг 6: Тест API регистрации через nginx
print_header "ШАГ 6: Тест API регистрации через Nginx"
TIMESTAMP=$(date +%s)
TEST_EMAIL2="test_${TIMESTAMP}_nginx@test.com"

echo "Попытка регистрации через nginx с email: $TEST_EMAIL2"
ssh "${SERVER}" "curl -X POST http://localhost/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{\"email\":\"$TEST_EMAIL2\",\"password\":\"testpass123\",\"full_name\":\"Test User\"}' \
  -w '\nHTTP Status: %{http_code}\n' 2>&1"
echo ""

# Шаг 7: Проверка nginx логов
print_header "ШАГ 7: Логи Nginx (последние 30 строк)"
ssh "${SERVER}" "cd ${REMOTE_PROJECT_DIR} && docker compose -f docker-compose.prod.yml logs nginx --tail=30" 2>&1 | tail -20
echo ""

# Шаг 8: Проверка error.log nginx
print_header "ШАГ 8: Nginx Error Log"
ssh "${SERVER}" 'docker exec medhistory_nginx cat /var/log/nginx/error.log 2>&1 | tail -20' || print_warning "Файл error.log пуст или не доступен"
echo ""

# Шаг 9: Проверка CORS в main.py
print_header "ШАГ 9: Проверка CORS настроек"
echo "Содержимое CORS настроек в backend:"
ssh "${SERVER}" "docker exec medhistory_backend cat /app/main.py | grep -A 8 'CORS middleware'" 2>&1 || print_error "Не удалось прочитать main.py"
echo ""

# Шаг 10: Проверка .env.production
print_header "ШАГ 10: Проверка .env файла"
ssh "${SERVER}" "test -f ${REMOTE_PROJECT_DIR}/.env.production && echo 'Файл .env.production существует' || echo 'Файл .env.production НЕ существует'"
ssh "${SERVER}" "test -f ${REMOTE_PROJECT_DIR}/.env && cat ${REMOTE_PROJECT_DIR}/.env | grep -E 'VITE_API_URL|POSTGRES_PASSWORD|JWT_SECRET' | sed 's/PASSWORD=.*/PASSWORD=***masked***/g' | sed 's/SECRET=.*/SECRET=***masked***/g'" 2>&1 || print_warning ".env файл не найден"
echo ""

# Итоги
print_header "📊 ИТОГИ ДИАГНОСТИКИ"
echo ""
echo "Для дальнейшей диагностики откройте браузер и:"
echo "1. Перейдите на http://${SERVER_IP}"
echo "2. Откройте DevTools (F12) → Console"
echo "3. Откройте вкладку Network"
echo "4. Попробуйте зарегистрироваться"
echo "5. Проверьте запрос /api/v1/auth/register в Network"
echo ""
print_warning "Проверьте вывод выше на наличие ошибок!"
echo ""
echo "================================================"
print_success "Диагностика завершена"


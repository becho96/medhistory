#!/bin/bash

# ============================================================
# Скрипт проверки соответствия названий анализов
# ============================================================
# Использование: ./scripts/check-analytes.sh
# ============================================================

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Определяем директории
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}🔍 Проверка соответствия названий анализов${NC}"
echo -e "${BLUE}============================================================${NC}"
echo

# Проверка наличия .env.production
if [ ! -f "$PROJECT_ROOT/.env.production" ]; then
    echo -e "${RED}❌ Файл .env.production не найден!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ .env.production найден${NC}"

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 не установлен!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 найден: $(python3 --version)${NC}"

# Проверка и установка зависимостей
echo
echo -e "${YELLOW}📦 Проверка зависимостей...${NC}"

# asyncpg
if ! python3 -c "import asyncpg" 2>/dev/null; then
    echo -e "${YELLOW}⚠ asyncpg не установлен. Устанавливаю...${NC}"
    pip3 install asyncpg
fi
echo -e "${GREEN}✓ asyncpg установлен${NC}"

# python-dotenv
if ! python3 -c "import dotenv" 2>/dev/null; then
    echo -e "${YELLOW}⚠ python-dotenv не установлен. Устанавливаю...${NC}"
    pip3 install python-dotenv
fi
echo -e "${GREEN}✓ python-dotenv установлен${NC}"

# motor (MongoDB async driver)
if ! python3 -c "import motor" 2>/dev/null; then
    echo -e "${YELLOW}⚠ motor не установлен. Устанавливаю...${NC}"
    pip3 install motor
fi
echo -e "${GREEN}✓ motor установлен${NC}"

# Запуск скрипта проверки
echo
echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}▶ Запуск проверки...${NC}"
echo -e "${BLUE}============================================================${NC}"
echo

cd "$PROJECT_ROOT"
python3 "$SCRIPT_DIR/check-analytes-mismatch.py"

exit_code=$?

echo
if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}✅ Проверка завершена${NC}"
    echo -e "${GREEN}============================================================${NC}"
else
    echo -e "${RED}============================================================${NC}"
    echo -e "${RED}❌ Проверка завершилась с ошибкой${NC}"
    echo -e "${RED}============================================================${NC}"
fi

exit $exit_code

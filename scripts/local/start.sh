#!/bin/bash

# MedHistory Startup Script

echo "🏥 Запуск MedHistory..."
echo ""

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker Desktop: https://www.docker.com/products/docker-desktop/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен."
    exit 1
fi

# Проверка .env файла
if [ ! -f .env ]; then
    echo "⚠️  Файл .env не найден!"
    echo ""
    echo "Создаю .env из примера..."
    cp .env.example .env 2>/dev/null || cat > .env << 'EOF'
# Database Passwords
POSTGRES_PASSWORD=medhistory_secure_pass
MONGO_PASSWORD=mongodb_secure_pass

# MinIO Credentials
MINIO_ROOT_USER=minio_admin
MINIO_ROOT_PASSWORD=minio_secure_pass_123

# OpenRouter API Key (замените на ваш ключ!)
OPENROUTER_API_KEY=your_openrouter_api_key_here

# JWT Secret
JWT_SECRET=jwt_super_secret_key_change_in_production

# Frontend API URL
VITE_API_URL=http://localhost:8000
EOF
    
    echo ""
    echo "⚠️  ВАЖНО: Отредактируйте .env и укажите ваш OPENROUTER_API_KEY!"
    echo "   Получить ключ: https://openrouter.ai/keys"
    echo ""
    read -p "Нажмите Enter когда укажете ключ..."
fi

# Проверка OpenRouter API Key
if grep -q "your_openrouter_api_key_here" .env; then
    echo ""
    echo "⚠️  ВНИМАНИЕ: Вы не указали OpenRouter API ключ в .env файле!"
    echo "   Сервис не сможет анализировать документы без ключа."
    echo ""
    read -p "Продолжить без ключа? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Отменено. Укажите ключ в .env и запустите снова."
        exit 1
    fi
fi

echo "✅ Запускаю контейнеры..."
docker compose up -d

echo ""
echo "⏳ Ожидание готовности сервисов (это может занять 1-2 минуты)..."
sleep 5

# Проверка статуса
echo ""
echo "📊 Статус сервисов:"
docker compose ps

echo ""
echo "✅ MedHistory запущен!"
echo ""
echo "🌐 Доступные сервисы:"
echo "   • Приложение:      http://localhost:5173"
echo "   • API документация: http://localhost:8000/docs"
echo "   • MinIO Console:    http://localhost:9001"
echo ""
echo "📝 Полезные команды:"
echo "   • Просмотр логов:   docker compose logs -f"
echo "   • Остановка:        docker compose stop"
echo "   • Перезапуск:       docker compose restart"
echo ""
echo "💡 Первый запуск?"
echo "   1. Откройте http://localhost:5173"
echo "   2. Зарегистрируйтесь"
echo "   3. Загрузите первый документ"
echo ""
echo "🎉 Готово к использованию!"


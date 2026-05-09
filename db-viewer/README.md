# DB Viewer

Веб-интерфейс для просмотра содержимого PostgreSQL и MongoDB с поддержкой переключения между локальным и production окружением.

## Возможности

- 🔄 **Переключение окружений** — Local / Production (Timeweb Cloud)
- 🐘 **PostgreSQL** — просмотр таблиц, колонок, данных
- 🍃 **MongoDB** — просмотр коллекций и документов
- 📊 Количество записей в каждой таблице/коллекции
- 📝 Информация о структуре (колонки, типы)
- 🔍 Просмотр данных с пагинацией
- 🎨 Подсветка типов данных (UUID, ObjectId, даты, boolean)
- 📋 Просмотр вложенных JSON объектов

## Быстрый запуск

### 1. Установка зависимостей

```bash
cd db-viewer
pip install -r requirements.txt
```

### 2. Запуск для локальной разработки

Убедитесь, что локальный Docker запущен:

```bash
cd ..
docker compose up -d
```

Запустите DB Viewer:

```bash
cd db-viewer
python app.py
```

Откройте в браузере: http://localhost:5050

## Конфигурация

### Переменные окружения

#### Локальное окружение (по умолчанию)

```bash
# PostgreSQL
PG_HOST=localhost
PG_PORT=5432
PG_DB=medhistory
PG_USER=medhistory_user
PG_PASSWORD=medhistory_local_pass

# MongoDB
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_USER=admin
MONGO_PASSWORD=mongodb_secure_pass
MONGO_DB=medhistory
```

#### Production окружение (Timeweb Cloud)

Для подключения к production серверу требуется SSH туннель:

```bash
# SSH доступ
PROD_SSH_HOST=194.87.140.190
PROD_SSH_PORT=22
PROD_SSH_USER=root
PROD_SSH_KEY=~/.ssh/medhistory_deploy

# PostgreSQL (пароли с сервера)
PROD_PG_DB=medhistory
PROD_PG_USER=medhistory_user
PROD_PG_PASSWORD=<production_password>

# MongoDB
PROD_MONGO_DB=medhistory
PROD_MONGO_USER=admin
PROD_MONGO_PASSWORD=<production_password>

# Backend API (для сброса кэша маппинга анализов после добавления синонима)
# Если не задано — используется http://PROD_SSH_HOST
PROD_BACKEND_URL=http://194.87.140.190
```

### Запуск с переменными окружения

```bash
# Через экспорт
export PROD_PG_PASSWORD=your_password
export PROD_MONGO_PASSWORD=your_password
python app.py

# Или через dotenv файл
# Создайте файл .env в директории db-viewer и добавьте переменные
```

## Архитектура подключения к Production

```
┌──────────────┐     SSH Tunnel      ┌─────────────────────────────┐
│              │ ═══════════════════►│   Timeweb Cloud Server      │
│  DB Viewer   │     Port 15432 ────►│   PostgreSQL (5432)         │
│  (localhost) │     Port 17017 ────►│   MongoDB (27017)           │
│              │                     │   194.87.140.190            │
└──────────────┘                     └─────────────────────────────┘
```

При переключении на Production:
1. Создаётся SSH туннель к серверу
2. Локальный порт 15432 → PostgreSQL на сервере (5432)
3. Локальный порт 17017 → MongoDB на сервере (27017)

## Требования

- Python 3.8+
- SSH ключ для доступа к production серверу (для production режима)
- Библиотека `sshtunnel` (автоматически устанавливается)

## Troubleshooting

### Ошибка "no password supplied" / "Connection refused" (Production)

Для режима Production нужны пароли из `.env.production`:
- `PROD_PG_PASSWORD` — пароль PostgreSQL на production
- `PROD_MONGO_PASSWORD` — пароль MongoDB на production

Docker Compose загружает их из `.env.production` (файл должен существовать).

### Ошибка "SSH ключ не найден"

При запуске в Docker монтируется директория `~/.ssh` с хоста. Варианты:

1. **Стандартный ключ** — проверьте, что `~/.ssh/medhistory_deploy` существует
2. **Альтернативный ключ** — переопределите через `.env.local`:
   ```bash
   PROD_SSH_KEY=/root/.ssh/id_rsa
   ```
3. **Папка ~/.ssh не существует** — при первом `ssh` обычно создаётся автоматически
4. **Локальный запуск** (без Docker):
   ```bash
   cd db-viewer && python app.py
   ```

### Ошибка подключения к Production

1. Проверьте, что SSH ключ добавлен к серверу
2. Проверьте, что сервер доступен: `ssh -i ~/.ssh/medhistory_deploy root@194.87.140.190`
3. Проверьте пароли от баз данных

### Библиотека sshtunnel не установлена

```bash
pip install sshtunnel
```

## Скриншоты

### Переключение окружений
- **Local** — подключение к локальным Docker контейнерам
- **Production** — подключение через SSH туннель к Timeweb Cloud

### Просмотр данных
- Список таблиц PostgreSQL и коллекций MongoDB
- Информация о колонках и типах данных
- Пагинация для больших таблиц
- Просмотр вложенных JSON объектов

# 🔧 Управление сервером MedHistory

Руководство по повседневному управлению и мониторингу сервера.

---

## 📊 Мониторинг

### Быстрая проверка состояния

```bash
# Комплексная проверка
ssh -l yc-user 93.77.182.26 << 'EOF'
echo "=== 🖥️  Server Status ==="
echo "Hostname: $(hostname)"
echo "Uptime: $(uptime -p)"
echo ""
echo "=== 💾 Disk Usage ==="
df -h / | tail -1
echo ""
echo "=== 🧠 Memory Usage ==="
free -h | grep Mem
echo ""
echo "=== 🐳 Docker Containers ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "=== 📈 Top Processes ==="
ps aux --sort=-%cpu | head -6
EOF
```

### Использование ресурсов

```bash
# CPU и память в реальном времени
ssh -l yc-user 93.77.182.26 'htop'

# Docker статистика
ssh -l yc-user 93.77.182.26 'docker stats --no-stream'

# Использование диска по директориям
ssh -l yc-user 93.77.182.26 'sudo du -sh /var/lib/docker/* | sort -rh | head -10'

# Inode usage
ssh -l yc-user 93.77.182.26 'df -i'
```

### Логи системы

```bash
# Системные логи
ssh -l yc-user 93.77.182.26 'sudo journalctl -xe --no-pager | tail -50'

# Docker daemon логи
ssh -l yc-user 93.77.182.26 'sudo journalctl -u docker --no-pager | tail -50'

# Ошибки в системных логах
ssh -l yc-user 93.77.182.26 'sudo journalctl -p err --no-pager | tail -20'
```

---

## 🐳 Управление Docker

### Контейнеры

```bash
# Список запущенных контейнеров
ssh -l yc-user 93.77.182.26 'docker ps'

# Все контейнеры (включая остановленные)
ssh -l yc-user 93.77.182.26 'docker ps -a'

# Логи контейнера
ssh -l yc-user 93.77.182.26 'docker logs medhistory_backend'
ssh -l yc-user 93.77.182.26 'docker logs -f --tail=100 medhistory_backend'

# Войти в контейнер
ssh -t -l yc-user 93.77.182.26 'docker exec -it medhistory_backend bash'

# Статистика контейнеров
ssh -l yc-user 93.77.182.26 'docker stats --no-stream'

# Перезапустить контейнер
ssh -l yc-user 93.77.182.26 'docker restart medhistory_backend'

# Остановить контейнер
ssh -l yc-user 93.77.182.26 'docker stop medhistory_backend'

# Удалить контейнер
ssh -l yc-user 93.77.182.26 'docker rm medhistory_backend'
```

### Docker Compose

```bash
# Запуск приложения
ssh -l yc-user 93.77.182.26 'cd ~/medhistory && docker compose -f docker-compose.prod.yml --env-file .env.production up -d'

# Остановка приложения
ssh -l yc-user 93.77.182.26 'cd ~/medhistory && docker compose -f docker-compose.prod.yml down'

# Перезапуск всех сервисов
ssh -l yc-user 93.77.182.26 'cd ~/medhistory && docker compose -f docker-compose.prod.yml restart'

# Перезапуск конкретного сервиса
ssh -l yc-user 93.77.182.26 'cd ~/medhistory && docker compose -f docker-compose.prod.yml restart backend'

# Логи всех сервисов
ssh -l yc-user 93.77.182.26 'cd ~/medhistory && docker compose -f docker-compose.prod.yml logs -f'

# Логи конкретного сервиса
ssh -l yc-user 93.77.182.26 'cd ~/medhistory && docker compose -f docker-compose.prod.yml logs -f backend'

# Статус сервисов
ssh -l yc-user 93.77.182.26 'cd ~/medhistory && docker compose -f docker-compose.prod.yml ps'

# Пересборка и перезапуск
ssh -l yc-user 93.77.182.26 'cd ~/medhistory && docker compose -f docker-compose.prod.yml up -d --build'

# Пересборка без кэша
ssh -l yc-user 93.77.182.26 'cd ~/medhistory && docker compose -f docker-compose.prod.yml build --no-cache'
```

### Очистка Docker

```bash
# Удалить неиспользуемые образы
ssh -l yc-user 93.77.182.26 'docker image prune -a'

# Удалить остановленные контейнеры
ssh -l yc-user 93.77.182.26 'docker container prune'

# Удалить неиспользуемые volumes
ssh -l yc-user 93.77.182.26 'docker volume prune'

# Полная очистка (осторожно!)
ssh -l yc-user 93.77.182.26 'docker system prune -a --volumes'

# Проверка занимаемого места
ssh -l yc-user 93.77.182.26 'docker system df'
```

---

## 🗄️ Управление базами данных

### PostgreSQL

```bash
# Подключение к PostgreSQL
ssh -l yc-user 93.77.182.26 'docker exec -it medhistory_postgres psql -U medhistory_user -d medhistory'

# Выполнить SQL запрос
ssh -l yc-user 93.77.182.26 'docker exec medhistory_postgres psql -U medhistory_user -d medhistory -c "SELECT COUNT(*) FROM users;"'

# Список таблиц
ssh -l yc-user 93.77.182.26 'docker exec medhistory_postgres psql -U medhistory_user -d medhistory -c "\dt"'

# Размер БД
ssh -l yc-user 93.77.182.26 'docker exec medhistory_postgres psql -U medhistory_user -d medhistory -c "SELECT pg_size_pretty(pg_database_size('\''medhistory'\''));"'

# Бэкап PostgreSQL
ssh -l yc-user 93.77.182.26 'docker exec medhistory_postgres pg_dump -U medhistory_user medhistory' > postgres_backup_$(date +%Y%m%d).sql

# Восстановление
cat postgres_backup_20251028.sql | ssh -l yc-user 93.77.182.26 'docker exec -i medhistory_postgres psql -U medhistory_user -d medhistory'
```

### MongoDB

```bash
# Подключение к MongoDB
ssh -l yc-user 93.77.182.26 'docker exec -it medhistory_mongodb mongosh medhistory'

# Список коллекций
ssh -l yc-user 93.77.182.26 'docker exec medhistory_mongodb mongosh medhistory --eval "db.getCollectionNames()"'

# Количество документов
ssh -l yc-user 93.77.182.26 'docker exec medhistory_mongodb mongosh medhistory --eval "db.documents.countDocuments()"'

# Размер БД
ssh -l yc-user 93.77.182.26 'docker exec medhistory_mongodb mongosh medhistory --eval "db.stats(1024*1024)"'

# Бэкап MongoDB
ssh -l yc-user 93.77.182.26 'docker exec medhistory_mongodb mongodump --db medhistory --out /tmp/backup'
ssh -l yc-user 93.77.182.26 'docker cp medhistory_mongodb:/tmp/backup ~/mongo_backup_$(date +%Y%m%d)'

# Восстановление
scp -r ~/mongo_backup_20251028 yc-user@93.77.182.26:~/restore
ssh -l yc-user 93.77.182.26 'docker exec medhistory_mongodb mongorestore --db medhistory ~/restore'
```

### MinIO (хранилище файлов)

```bash
# Проверка работы MinIO
curl http://93.77.182.26:9000/minio/health/live

# Логи MinIO
ssh -l yc-user 93.77.182.26 'docker logs medhistory_minio'

# Войти в MinIO CLI
ssh -l yc-user 93.77.182.26 'docker exec -it medhistory_minio mc alias set minio http://localhost:9000 admin <PASSWORD>'

# Список bucket'ов
ssh -l yc-user 93.77.182.26 'docker exec medhistory_minio mc ls minio/'

# Размер хранилища
ssh -l yc-user 93.77.182.26 'docker exec medhistory_minio mc du minio/documents'
```

---

## 📦 Обновление приложения

### Используя скрипты

```bash
# Полное обновление
cd "/Users/boris/Desktop/Начало/История болезни"
./scripts/update-all.sh

# Только backend
./scripts/update-backend.sh

# Только frontend
./scripts/update-frontend.sh
```

### Ручное обновление

```bash
# 1. Синхронизация файлов
cd "/Users/boris/Desktop/Начало/История болезни"
rsync -avz --progress \
  --exclude 'node_modules' \
  --exclude '__pycache__' \
  --exclude 'frontend/dist' \
  . yc-user@93.77.182.26:~/medhistory/

# 2. Пересборка на сервере
ssh -l yc-user 93.77.182.26 'cd ~/medhistory && docker compose -f docker-compose.prod.yml build --no-cache'

# 3. Перезапуск
ssh -l yc-user 93.77.182.26 'cd ~/medhistory && docker compose -f docker-compose.prod.yml up -d'

# 4. Проверка логов
ssh -l yc-user 93.77.182.26 'cd ~/medhistory && docker compose -f docker-compose.prod.yml logs -f'
```

---

## 💾 Резервное копирование

### Бэкап всего приложения

```bash
# На сервере (создать бэкап)
ssh -l yc-user 93.77.182.26 'cd ~/medhistory && ./scripts/backup.sh ~/backups'

# Скачать бэкап локально
scp yc-user@93.77.182.26:~/backups/medhistory_backup_*.tar.gz ~/Downloads/
```

### Автоматические бэкапы (cron)

```bash
# Настроить на сервере
ssh -l yc-user 93.77.182.26

# Добавить в crontab
crontab -e

# Добавить строку (бэкап каждый день в 3:00)
0 3 * * * cd ~/medhistory && ./scripts/backup.sh ~/backups

# Очистка старых бэкапов (оставить последние 7 дней)
0 4 * * * find ~/backups -name "medhistory_backup_*.tar.gz" -mtime +7 -delete
```

### Восстановление из бэкапа

```bash
# 1. Загрузить бэкап на сервер (если нужно)
scp ~/Downloads/medhistory_backup_20251028.tar.gz yc-user@93.77.182.26:~/backups/

# 2. Восстановить
ssh -l yc-user 93.77.182.26 'cd ~/medhistory && ./scripts/restore.sh ~/backups/medhistory_backup_20251028.tar.gz'
```

---

## 🔄 Обновление системы

### Ubuntu

```bash
# Обновление пакетов
ssh -l yc-user 93.77.182.26 'sudo apt update && sudo apt upgrade -y'

# Обновление только security патчей
ssh -l yc-user 93.77.182.26 'sudo unattended-upgrade'

# Очистка
ssh -l yc-user 93.77.182.26 'sudo apt autoremove -y && sudo apt autoclean'

# Проверка доступных обновлений
ssh -l yc-user 93.77.182.26 'apt list --upgradable'
```

### Docker

```bash
# Обновление Docker
ssh -l yc-user 93.77.182.26 'sudo apt update && sudo apt install --only-upgrade docker-ce docker-ce-cli containerd.io'

# Проверка версии
ssh -l yc-user 93.77.182.26 'docker --version'
```

---

## 🔐 Безопасность

### Проверка безопасности

```bash
# Проверка открытых портов
ssh -l yc-user 93.77.182.26 'sudo ss -tulpn'

# Активные соединения
ssh -l yc-user 93.77.182.26 'sudo netstat -an | grep ESTABLISHED'

# Неудачные попытки входа
ssh -l yc-user 93.77.182.26 'sudo lastb | head -20'

# История команд root
ssh -l yc-user 93.77.182.26 'sudo cat /root/.bash_history | tail -50'
```

### Обновление SSL сертификатов (если используются)

```bash
# Продление Let's Encrypt сертификата
ssh -l yc-user 93.77.182.26 'sudo certbot renew'

# Автоматическое продление (cron)
ssh -l yc-user 93.77.182.26 'sudo crontab -e'
# Добавить: 0 0 * * * certbot renew --quiet
```

---

## 📈 Оптимизация производительности

### Очистка логов

```bash
# Размер логов Docker
ssh -l yc-user 93.77.182.26 'sudo du -sh /var/lib/docker/containers/*/*-json.log | sort -rh | head -10'

# Очистка логов контейнера
ssh -l yc-user 93.77.182.26 'sudo truncate -s 0 /var/lib/docker/containers/<CONTAINER_ID>/<CONTAINER_ID>-json.log'

# Ограничение размера логов (в docker-compose.yml)
# logging:
#   driver: "json-file"
#   options:
#     max-size: "10m"
#     max-file: "3"
```

### Swap (если нужно)

```bash
# Проверка swap
ssh -l yc-user 93.77.182.26 'free -h'

# Создание swap файла (4GB)
ssh -l yc-user 93.77.182.26 << 'EOF'
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
EOF
```

---

## 🚨 Аварийные процедуры

### Контейнер не запускается

```bash
# 1. Проверить логи
ssh -l yc-user 93.77.182.26 'cd ~/medhistory && docker compose -f docker-compose.prod.yml logs backend'

# 2. Пересоздать контейнер
ssh -l yc-user 93.77.182.26 'cd ~/medhistory && docker compose -f docker-compose.prod.yml up -d --force-recreate backend'

# 3. Полная пересборка
ssh -l yc-user 93.77.182.26 'cd ~/medhistory && docker compose -f docker-compose.prod.yml down && docker compose -f docker-compose.prod.yml build --no-cache && docker compose -f docker-compose.prod.yml up -d'
```

### Диск заполнен

```bash
# 1. Проверить что занимает место
ssh -l yc-user 93.77.182.26 'sudo du -sh /* | sort -rh | head -10'

# 2. Очистить Docker
ssh -l yc-user 93.77.182.26 'docker system prune -a --volumes'

# 3. Очистить логи
ssh -l yc-user 93.77.182.26 'sudo journalctl --vacuum-time=7d'

# 4. Очистить apt кэш
ssh -l yc-user 93.77.182.26 'sudo apt clean'
```

### Сервер не отвечает

```bash
# 1. Проверить доступность
ping 93.77.182.26

# 2. Перезагрузить через YC CLI
/Users/boris/yandex-cloud/bin/yc compute instance restart medhistory-server

# 3. Посмотреть serial console
/Users/boris/yandex-cloud/bin/yc compute instance get-serial-port-output medhistory-server | tail -100
```

---

## 📝 Регулярные задачи

### Ежедневно
- ✅ Проверка логов на ошибки
- ✅ Мониторинг использования диска
- ✅ Проверка работы всех контейнеров

### Еженедельно
- ✅ Обновление системных пакетов
- ✅ Проверка бэкапов
- ✅ Анализ логов безопасности

### Ежемесячно
- ✅ Обновление Docker
- ✅ Очистка старых образов и логов
- ✅ Проверка использования ресурсов
- ✅ Аудит безопасности

---

## 🔗 Полезные ссылки

- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [MongoDB Documentation](https://docs.mongodb.com/)

---

**Последнее обновление:** 28 октября 2025


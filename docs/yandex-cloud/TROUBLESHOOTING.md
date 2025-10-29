# 🔧 Решение проблем

Руководство по диагностике и устранению типичных проблем с сервером MedHistory.

---

## 🔍 Диагностика

### Быстрая проверка

```bash
# Комплексная диагностика
ssh -l yc-user 46.21.244.23 << 'EOF'
echo "=== System Status ==="
systemctl is-system-running
echo ""
echo "=== Docker Status ==="
sudo systemctl status docker --no-pager | head -5
echo ""
echo "=== Containers ==="
docker ps -a
echo ""
echo "=== Disk Space ==="
df -h / | tail -1
echo ""
echo "=== Memory ==="
free -h | grep Mem
echo ""
echo "=== Network ==="
ping -c 3 8.8.8.8
EOF
```

---

## 🚫 Проблемы с SSH

### Не могу подключиться по SSH

#### Проблема: Connection timeout

**Причина:** Порт 22 закрыт или ВМ недоступна

**Решение:**
```bash
# 1. Проверить, что ВМ запущена
/Users/boris/yandex-cloud/bin/yc compute instance get medhistory-server | grep status

# 2. Если остановлена - запустить
/Users/boris/yandex-cloud/bin/yc compute instance start medhistory-server

# 3. Проверить Security Group
/Users/boris/yandex-cloud/bin/yc vpc security-group get enpo36phcf9ck74h6igk | grep "port: \"22\""

# 4. Проверить доступность порта
nc -zv 46.21.244.23 22
```

#### Проблема: Permission denied (publickey)

**Причина:** SSH ключ не распознан

**Решение:**
```bash
# 1. Проверить права на ключ
ls -la ~/.ssh/id_rsa
chmod 600 ~/.ssh/id_rsa

# 2. Проверить, что используете правильного пользователя
# ✅ Правильно: yc-user
# ❌ Неправильно: ubuntu

# 3. Добавить ключ в метаданные ВМ
/Users/boris/yandex-cloud/bin/yc compute instance add-metadata medhistory-server \
  --metadata ssh-keys="yc-user:$(cat ~/.ssh/id_rsa.pub)"

# 4. Подождать 10-15 секунд
sleep 15

# 5. Попробовать снова
ssh -l yc-user 46.21.244.23
```

#### Проблема: Connection closed by remote host

**Причина:** SSH сервис неправильно настроен или перегружен

**Решение:**
```bash
# 1. Перезагрузить ВМ
/Users/boris/yandex-cloud/bin/yc compute instance restart medhistory-server

# 2. Подождать 1-2 минуты
sleep 120

# 3. Проверить serial console
/Users/boris/yandex-cloud/bin/yc compute instance get-serial-port-output medhistory-server | tail -50

# 4. Попробовать подключиться
ssh -l yc-user 46.21.244.23
```

#### Проблема: Host key verification failed

**Причина:** SSH ключ хоста изменился

**Решение:**
```bash
# Удалить старый ключ
ssh-keygen -R 46.21.244.23

# Подключиться заново
ssh -o StrictHostKeyChecking=no -l yc-user 46.21.244.23
```

---

## 🐳 Проблемы с Docker

### Контейнер не запускается

#### Диагностика
```bash
# 1. Проверить статус
ssh -l yc-user 46.21.244.23 'docker ps -a | grep medhistory'

# 2. Посмотреть логи
ssh -l yc-user 46.21.244.23 'docker logs medhistory_backend --tail=100'

# 3. Проверить конфигурацию
ssh -l yc-user 46.21.244.23 'cd ~/medhistory && docker compose -f docker-compose.prod.yml config'
```

#### Решения

**1. Пересоздать контейнер**
```bash
ssh -l yc-user 46.21.244.23 'cd ~/medhistory && docker compose -f docker-compose.prod.yml up -d --force-recreate backend'
```

**2. Полная пересборка**
```bash
ssh -l yc-user 46.21.244.23 'cd ~/medhistory && \
  docker compose -f docker-compose.prod.yml down && \
  docker compose -f docker-compose.prod.yml build --no-cache && \
  docker compose -f docker-compose.prod.yml --env-file .env.production up -d'
```

**3. Проверить .env.production**
```bash
ssh -l yc-user 46.21.244.23 'cat ~/medhistory/.env.production'
```

### Docker daemon не работает

```bash
# Проверить статус
ssh -l yc-user 46.21.244.23 'sudo systemctl status docker'

# Запустить Docker
ssh -l yc-user 46.21.244.23 'sudo systemctl start docker'

# Включить автозапуск
ssh -l yc-user 46.21.244.23 'sudo systemctl enable docker'

# Перезапустить Docker
ssh -l yc-user 46.21.244.23 'sudo systemctl restart docker'

# Посмотреть логи
ssh -l yc-user 46.21.244.23 'sudo journalctl -u docker --no-pager | tail -50'
```

### Ошибка "no space left on device"

```bash
# 1. Проверить использование диска
ssh -l yc-user 46.21.244.23 'df -h'

# 2. Очистить Docker
ssh -l yc-user 46.21.244.23 'docker system prune -a --volumes'

# 3. Очистить логи
ssh -l yc-user 46.21.244.23 'sudo journalctl --vacuum-time=7d'

# 4. Удалить старые образы
ssh -l yc-user 46.21.244.23 'docker images --format "{{.Repository}}:{{.Tag}} {{.Size}}" | sort -k 2 -h'
ssh -l yc-user 46.21.244.23 'docker rmi $(docker images -q)'
```

### Контейнер постоянно перезапускается

```bash
# 1. Проверить логи
ssh -l yc-user 46.21.244.23 'docker logs medhistory_backend --tail=200'

# 2. Проверить health check
ssh -l yc-user 46.21.244.23 'docker inspect medhistory_backend | jq ".[0].State.Health"'

# 3. Остановить автоматический перезапуск
ssh -l yc-user 46.21.244.23 'docker update --restart=no medhistory_backend'

# 4. Запустить контейнер вручную для диагностики
ssh -l yc-user 46.21.244.23 'docker start medhistory_backend && docker logs -f medhistory_backend'
```

---

## 🗄️ Проблемы с базами данных

### PostgreSQL не доступна

```bash
# 1. Проверить статус контейнера
ssh -l yc-user 46.21.244.23 'docker ps | grep postgres'

# 2. Проверить логи
ssh -l yc-user 46.21.244.23 'docker logs medhistory_postgres --tail=50'

# 3. Перезапустить
ssh -l yc-user 46.21.244.23 'cd ~/medhistory && docker compose -f docker-compose.prod.yml restart postgres'

# 4. Проверить подключение
ssh -l yc-user 46.21.244.23 'docker exec medhistory_postgres pg_isready -U medhistory_user'
```

### MongoDB не доступна

```bash
# 1. Проверить статус
ssh -l yc-user 46.21.244.23 'docker ps | grep mongodb'

# 2. Логи
ssh -l yc-user 46.21.244.23 'docker logs medhistory_mongodb --tail=50'

# 3. Проверить подключение
ssh -l yc-user 46.21.244.23 'docker exec medhistory_mongodb mongosh --eval "db.adminCommand({ ping: 1 })"'

# 4. Перезапустить
ssh -l yc-user 46.21.244.23 'cd ~/medhistory && docker compose -f docker-compose.prod.yml restart mongodb'
```

### Ошибки миграций БД

```bash
# 1. Проверить текущую версию схемы
ssh -l yc-user 46.21.244.23 'docker exec medhistory_postgres psql -U medhistory_user -d medhistory -c "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1;"'

# 2. Запустить миграции вручную
ssh -l yc-user 46.21.244.23 'docker exec -i medhistory_postgres psql -U medhistory_user -d medhistory' < backend/migrations/XXX_migration.sql

# 3. Откатить последнюю миграцию (если есть rollback скрипт)
ssh -l yc-user 46.21.244.23 'docker exec -i medhistory_postgres psql -U medhistory_user -d medhistory' < backend/migrations/XXX_rollback.sql
```

---

## 🌐 Проблемы с сетью

### Приложение недоступно извне

```bash
# 1. Проверить, что nginx работает
ssh -l yc-user 46.21.244.23 'docker ps | grep nginx'

# 2. Проверить порты
ssh -l yc-user 46.21.244.23 'sudo ss -tulpn | grep -E ":(80|443)"'

# 3. Проверить Security Group
/Users/boris/yandex-cloud/bin/yc vpc security-group get enpo36phcf9ck74h6igk

# 4. Проверить health endpoint
curl -v http://46.21.244.23/health

# 5. Проверить логи nginx
ssh -l yc-user 46.21.244.23 'docker logs medhistory_nginx --tail=50'
```

### Slow response / Timeouts

```bash
# 1. Проверить нагрузку
ssh -l yc-user 46.21.244.23 'top -bn1 | head -20'

# 2. Проверить Docker stats
ssh -l yc-user 46.21.244.23 'docker stats --no-stream'

# 3. Проверить сетевую задержку
ping -c 10 46.21.244.23

# 4. Проверить логи backend
ssh -l yc-user 46.21.244.23 'cd ~/medhistory && docker compose -f docker-compose.prod.yml logs --tail=100 backend | grep -i error'
```

### DNS не резолвится

```bash
# 1. Проверить DNS на сервере
ssh -l yc-user 46.21.244.23 'nslookup google.com'

# 2. Проверить /etc/resolv.conf
ssh -l yc-user 46.21.244.23 'cat /etc/resolv.conf'

# 3. Перезапустить сеть
ssh -l yc-user 46.21.244.23 'sudo systemctl restart systemd-resolved'
```

---

## 💾 Проблемы с диском

### Диск заполнен

```bash
# 1. Определить что занимает место
ssh -l yc-user 46.21.244.23 'sudo du -sh /* | sort -rh | head -10'
ssh -l yc-user 46.21.244.23 'sudo du -sh /var/lib/docker/* | sort -rh'

# 2. Очистить Docker
ssh -l yc-user 46.21.244.23 'docker system df'  # Посмотреть что занимает место
ssh -l yc-user 46.21.244.23 'docker system prune -a --volumes'

# 3. Очистить логи
ssh -l yc-user 46.21.244.23 'sudo journalctl --disk-usage'
ssh -l yc-user 46.21.244.23 'sudo journalctl --vacuum-time=7d'

# 4. Очистить apt кэш
ssh -l yc-user 46.21.244.23 'sudo apt clean && sudo apt autoremove -y'

# 5. Увеличить размер диска (если нужно)
/Users/boris/yandex-cloud/bin/yc compute disk update fhm7lhk4a8ruibjj7l4e --size 100
ssh -l yc-user 46.21.244.23 'sudo resize2fs /dev/vda1'
```

### Высокий I/O на диске

```bash
# 1. Проверить активность диска
ssh -l yc-user 46.21.244.23 'iostat -x 1 5'

# 2. Найти процессы с высоким I/O
ssh -l yc-user 46.21.244.23 'sudo iotop -o'

# 3. Проверить Docker volumes
ssh -l yc-user 46.21.244.23 'docker ps -q | xargs docker inspect -f '\''{{ .Name }}{{ range .Mounts }} {{ .Source }}{{ end }}'\'''
```

---

## 🧠 Проблемы с памятью

### Out of Memory (OOM)

```bash
# 1. Проверить использование памяти
ssh -l yc-user 46.21.244.23 'free -h'

# 2. Найти процессы-"пожиратели" памяти
ssh -l yc-user 46.21.244.23 'ps aux --sort=-%mem | head -10'

# 3. Проверить Docker контейнеры
ssh -l yc-user 46.21.244.23 'docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}"'

# 4. Проверить OOM логи
ssh -l yc-user 46.21.244.23 'sudo dmesg | grep -i "out of memory"'
ssh -l yc-user 46.21.244.23 'sudo journalctl -k | grep -i "killed process"'

# 5. Добавить swap (временное решение)
ssh -l yc-user 46.21.244.23 << 'EOF'
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
EOF
```

### Memory leak

```bash
# 1. Мониторить память контейнера
ssh -l yc-user 46.21.244.23 'while true; do docker stats --no-stream medhistory_backend | tail -1; sleep 60; done'

# 2. Перезапустить проблемный контейнер
ssh -l yc-user 46.21.244.23 'cd ~/medhistory && docker compose -f docker-compose.prod.yml restart backend'

# 3. Ограничить память контейнера (в docker-compose.yml)
# deploy:
#   resources:
#     limits:
#       memory: 2G
```

---

## 🔥 Критические ситуации

### Сервер полностью недоступен

```bash
# 1. Проверить ping
ping 46.21.244.23

# 2. Проверить статус ВМ через YC
/Users/boris/yandex-cloud/bin/yc compute instance get medhistory-server

# 3. Перезагрузить ВМ
/Users/boris/yandex-cloud/bin/yc compute instance restart medhistory-server

# 4. Ждем 2-3 минуты
sleep 180

# 5. Проверить serial console
/Users/boris/yandex-cloud/bin/yc compute instance get-serial-port-output medhistory-server | tail -100

# 6. Если не помогло - пересоздать ВМ из снимка
```

### Все контейнеры упали

```bash
# 1. Подключиться к серверу
ssh -l yc-user 46.21.244.23

# 2. Проверить Docker daemon
sudo systemctl status docker

# 3. Перезапустить Docker
sudo systemctl restart docker

# 4. Запустить приложение
cd ~/medhistory
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# 5. Мониторить логи
docker compose -f docker-compose.prod.yml logs -f
```

### Данные повреждены

```bash
# 1. Остановить приложение
ssh -l yc-user 46.21.244.23 'cd ~/medhistory && docker compose -f docker-compose.prod.yml down'

# 2. Восстановить из бэкапа
ssh -l yc-user 46.21.244.23 'cd ~/medhistory && ./scripts/restore.sh ~/backups/medhistory_backup_LATEST.tar.gz'

# 3. Или восстановить из снимка диска
/Users/boris/yandex-cloud/bin/yc compute disk create \
  --name medhistory-disk-restored \
  --source-snapshot-name medhistory-snapshot-LATEST
# Затем создать новую ВМ с этим диском
```

---

## 🔄 Проблемы с обновлением

### Обновление не применяется

```bash
# 1. Проверить что файлы загружены
ssh -l yc-user 46.21.244.23 'ls -lah ~/medhistory/backend/app/main.py'

# 2. Пересобрать без кэша
ssh -l yc-user 46.21.244.23 'cd ~/medhistory && docker compose -f docker-compose.prod.yml build --no-cache backend'

# 3. Принудительно пересоздать контейнер
ssh -l yc-user 46.21.244.23 'cd ~/medhistory && docker compose -f docker-compose.prod.yml up -d --force-recreate backend'

# 4. Проверить, что новый образ используется
ssh -l yc-user 46.21.244.23 'docker images | grep medhistory'
```

### Rsync ошибки

```bash
# 1. Проверить SSH подключение
ssh -l yc-user 46.21.244.23 'echo "OK"'

# 2. Использовать verbose mode
rsync -avzP ./backend/ yc-user@46.21.244.23:~/medhistory/backend/

# 3. Проверить права доступа
ssh -l yc-user 46.21.244.23 'ls -la ~/medhistory/'
```

---

## 📋 Чеклист диагностики

Когда что-то идет не так, проверьте по порядку:

### Уровень 1: Базовые проверки
- [ ] ВМ запущена (`yc compute instance get medhistory-server`)
- [ ] SSH доступен (`ssh -l yc-user 46.21.244.23 'echo OK'`)
- [ ] Docker работает (`ssh -l yc-user 46.21.244.23 'docker ps'`)
- [ ] Контейнеры запущены
- [ ] Есть свободное место на диске
- [ ] Есть свободная память

### Уровень 2: Детальная диагностика
- [ ] Логи контейнеров без ошибок
- [ ] Базы данных доступны
- [ ] Health endpoint отвечает
- [ ] Сеть работает корректно
- [ ] .env.production правильно настроен

### Уровень 3: Глубокая диагностика
- [ ] Системные логи (`journalctl`)
- [ ] Логи Docker daemon
- [ ] Serial console вывод
- [ ] Метрики производительности
- [ ] Security Group правила

---

## 🆘 Контакты для поддержки

- **Yandex Cloud Support:** https://cloud.yandex.ru/support
- **Документация:** https://cloud.yandex.ru/docs/
- **Форум:** https://cloud.yandex.ru/forum/

---

## 📝 Логирование проблем

При обращении в поддержку всегда предоставляйте:

1. **Описание проблемы**
2. **Точное время возникновения**
3. **Логи:**
   ```bash
   ssh -l yc-user 46.21.244.23 'docker compose -f ~/medhistory/docker-compose.prod.yml logs' > problem_logs.txt
   ```
4. **Статус системы:**
   ```bash
   ssh -l yc-user 46.21.244.23 'docker ps -a; df -h; free -h' > system_status.txt
   ```
5. **Serial console вывод:**
   ```bash
   yc compute instance get-serial-port-output medhistory-server > serial_console.txt
   ```

---

**Последнее обновление:** 28 октября 2025


# 🔐 Безопасность сервера

Руководство по настройке безопасности и best practices для сервера MedHistory.

---

## 🎯 Основные принципы безопасности

1. **Минимум привилегий** - давать только необходимые права
2. **Глубокая защита** - несколько уровней защиты
3. **Регулярные обновления** - всегда актуальное ПО
4. **Мониторинг** - отслеживание подозрительной активности
5. **Бэкапы** - регулярное резервное копирование

---

## 🔑 SSH Security

### Базовая настройка SSH

```bash
ssh -l yc-user 46.21.244.23

# Редактировать конфигурацию SSH
sudo nano /etc/ssh/sshd_config
```

**Рекомендуемые настройки:**
```
# Отключить вход по паролю
PasswordAuthentication no
PubkeyAuthentication yes

# Отключить root login
PermitRootLogin no

# Разрешить только конкретных пользователей
AllowUsers yc-user

# Изменить порт (опционально)
# Port 2222

# Ограничить попытки входа
MaxAuthTries 3
MaxSessions 5

# Таймауты
LoginGraceTime 30
ClientAliveInterval 300
ClientAliveCountMax 2

# Отключить пустые пароли
PermitEmptyPasswords no

# Отключить X11 forwarding (если не нужен)
X11Forwarding no

# Отключить SSH Agent Forwarding (если не нужен)
AllowAgentForwarding no

# Использовать только безопасные алгоритмы
Protocol 2
Ciphers aes256-gcm@openssh.com,aes128-gcm@openssh.com
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com
KexAlgorithms curve25519-sha256,diffie-hellman-group-exchange-sha256
```

**Применить изменения:**
```bash
# Проверить конфигурацию
sudo sshd -t

# Перезапустить SSH
sudo systemctl restart sshd
```

### SSH ключи

#### Создание надежного SSH ключа

```bash
# На локальной машине
# Используйте ED25519 (современный, быстрый, безопасный)
ssh-keygen -t ed25519 -a 100 -f ~/.ssh/medhistory_ed25519 -C "medhistory-server"

# Или RSA 4096 бит
ssh-keygen -t rsa -b 4096 -o -a 100 -f ~/.ssh/medhistory_rsa -C "medhistory-server"
```

#### Защита ключей

```bash
# Правильные права доступа
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub
chmod 600 ~/.ssh/config

# Использовать парольную фразу для ключа
# (будет запрошена при создании ключа)
```

#### Ротация ключей

```bash
# Рекомендуется менять ключи раз в год

# 1. Создать новый ключ
ssh-keygen -t ed25519 -f ~/.ssh/medhistory_new

# 2. Добавить на сервер
/Users/boris/yandex-cloud/bin/yc compute instance add-metadata medhistory-server \
  --metadata ssh-keys="yc-user:$(cat ~/.ssh/medhistory_new.pub)"

# 3. Проверить доступ с новым ключом
ssh -i ~/.ssh/medhistory_new -l yc-user 46.21.244.23

# 4. Удалить старый ключ (после проверки)
/Users/boris/yandex-cloud/bin/yc compute instance remove-metadata medhistory-server \
  --keys ssh-keys
```

---

## 🛡️ Firewall и Security Groups

### Настройка Security Group

```bash
# Просмотр текущих правил
/Users/boris/yandex-cloud/bin/yc vpc security-group get enpo36phcf9ck74h6igk
```

**Минимально необходимые правила:**

**Входящие (Ingress):**
- SSH (22) - только с вашего IP
- HTTP (80) - для пользователей
- HTTPS (443) - для пользователей

**Исходящие (Egress):**
- Разрешить все (для обновлений и внешних API)

```bash
# Ограничить SSH только с вашего IP
MY_IP=$(curl -s ifconfig.me)

/Users/boris/yandex-cloud/bin/yc vpc security-group update-rules medhistory-sg \
  --add-rule "direction=ingress,port=22,protocol=tcp,v4-cidrs=[$MY_IP/32],description=SSH-from-my-IP"
```

### UFW Firewall на сервере

```bash
ssh -l yc-user 46.21.244.23

# Установить UFW
sudo apt install -y ufw

# По умолчанию запретить все входящие
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Разрешить SSH (ВАЖНО! Сделать до включения UFW)
sudo ufw allow 22/tcp

# Разрешить HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Включить UFW
sudo ufw --force enable

# Проверить статус
sudo ufw status verbose
```

---

## 🚨 Fail2Ban

Защита от брутфорс атак.

### Установка и настройка

```bash
ssh -l yc-user 46.21.244.23

# Установка
sudo apt update
sudo apt install -y fail2ban

# Создать конфигурацию
sudo nano /etc/fail2ban/jail.local
```

**Базовая конфигурация:**
```ini
[DEFAULT]
# Время бана (в секундах)
bantime = 3600
# Интервал для подсчета попыток
findtime = 600
# Максимум попыток
maxretry = 3
# Email для уведомлений (опционально)
# destemail = your@email.com
# action = %(action_mwl)s

[sshd]
enabled = true
port = 22
logpath = /var/log/auth.log
maxretry = 3
bantime = 7200
```

**Запуск:**
```bash
# Запустить Fail2Ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Проверить статус
sudo fail2ban-client status
sudo fail2ban-client status sshd

# Разбанить IP (если нужно)
sudo fail2ban-client set sshd unbanip <IP>
```

---

## 🔒 SSL/TLS сертификаты

### Let's Encrypt (бесплатные сертификаты)

```bash
ssh -l yc-user 46.21.244.23

# Установить Certbot
sudo apt update
sudo apt install -y certbot

# Получить сертификат (standalone)
# ВАЖНО: Остановите nginx перед этим
sudo docker compose -f ~/medhistory/docker-compose.prod.yml stop nginx

sudo certbot certonly --standalone \
  -d your-domain.com \
  -d www.your-domain.com \
  --agree-tos \
  --email your@email.com \
  --no-eff-email

# Скопировать сертификаты в проект
sudo mkdir -p ~/medhistory/nginx/ssl
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ~/medhistory/nginx/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ~/medhistory/nginx/ssl/
sudo chown -R yc-user:yc-user ~/medhistory/nginx/ssl/

# Запустить nginx
sudo docker compose -f ~/medhistory/docker-compose.prod.yml start nginx
```

### Автоматическое обновление сертификатов

```bash
# Создать скрипт обновления
sudo nano /usr/local/bin/renew-cert.sh
```

```bash
#!/bin/bash
# Скрипт обновления SSL сертификата

docker compose -f /home/yc-user/medhistory/docker-compose.prod.yml stop nginx
certbot renew --quiet
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem /home/yc-user/medhistory/nginx/ssl/
cp /etc/letsencrypt/live/your-domain.com/privkey.pem /home/yc-user/medhistory/nginx/ssl/
chown -R yc-user:yc-user /home/yc-user/medhistory/nginx/ssl/
docker compose -f /home/yc-user/medhistory/docker-compose.prod.yml start nginx
```

```bash
# Сделать исполняемым
sudo chmod +x /usr/local/bin/renew-cert.sh

# Добавить в cron (обновление каждый месяц)
sudo crontab -e
# Добавить: 0 0 1 * * /usr/local/bin/renew-cert.sh
```

---

## 🔐 Секреты и переменные окружения

### Безопасное хранение .env.production

```bash
# Правильные права доступа
ssh -l yc-user 46.21.244.23 'chmod 600 ~/medhistory/.env.production'

# НЕ коммитить .env в git
# Убедитесь что .env* добавлен в .gitignore
```

### Генерация безопасных паролей

```bash
# Для PostgreSQL, MongoDB, MinIO, JWT
openssl rand -base64 32

# Или
head -c 32 /dev/urandom | base64
```

### Ротация секретов

**Регулярно меняйте:**
- Пароли БД (раз в 3-6 месяцев)
- JWT секрет (при подозрении на утечку)
- API ключи (раз в год)

```bash
# 1. Обновить .env.production
nano ~/medhistory/.env.production

# 2. Пересоздать контейнеры
cd ~/medhistory
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

---

## 🐳 Docker Security

### Best Practices

1. **Не запускать контейнеры от root**
2. **Ограничить ресурсы**
3. **Read-only файловая система где возможно**
4. **Не хранить секреты в образах**

### Пример безопасной конфигурации Docker Compose

```yaml
services:
  backend:
    # Не запускать от root
    user: "1000:1000"
    
    # Ограничить ресурсы
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
    
    # Read-only где возможно
    read_only: true
    tmpfs:
      - /tmp
    
    # Запретить повышение привилегий
    security_opt:
      - no-new-privileges:true
    
    # Ограничить capabilities
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
```

### Сканирование образов на уязвимости

```bash
# Установить Trivy
ssh -l yc-user 46.21.244.23 << 'EOF'
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/trivy.list
sudo apt update
sudo apt install trivy
EOF

# Сканировать образ
ssh -l yc-user 46.21.244.23 'trivy image medhistory_backend:latest'
```

---

## 🗄️ Безопасность баз данных

### PostgreSQL

```bash
# Изменить пароль
ssh -l yc-user 46.21.244.23 'docker exec -it medhistory_postgres psql -U postgres'
```

```sql
ALTER USER medhistory_user WITH PASSWORD 'new-strong-password';
```

### MongoDB

```bash
ssh -l yc-user 46.21.244.23 'docker exec -it medhistory_mongodb mongosh admin'
```

```javascript
db.changeUserPassword("medhistory_user", "new-strong-password");
```

### Бэкапы БД

```bash
# Шифрование бэкапов
ssh -l yc-user 46.21.244.23 << 'EOF'
# Создать бэкап
docker exec medhistory_postgres pg_dump -U medhistory_user medhistory > /tmp/backup.sql

# Зашифровать
gpg --symmetric --cipher-algo AES256 /tmp/backup.sql

# Загрузить зашифрованный бэкап
mv /tmp/backup.sql.gpg ~/backups/
rm /tmp/backup.sql
EOF
```

---

## 📊 Мониторинг безопасности

### Аудит доступа

```bash
# История входов
ssh -l yc-user 46.21.244.23 'last | head -20'

# Неудачные попытки входа
ssh -l yc-user 46.21.244.23 'sudo lastb | head -20'

# Активные пользователи
ssh -l yc-user 46.21.244.23 'w'

# История команд sudo
ssh -l yc-user 46.21.244.23 'sudo cat /var/log/auth.log | grep sudo | tail -50'
```

### Мониторинг открытых портов

```bash
# Все слушающие порты
ssh -l yc-user 46.21.244.23 'sudo ss -tulpn'

# Активные соединения
ssh -l yc-user 46.21.244.23 'sudo netstat -an | grep ESTABLISHED'
```

### Проверка на руткиты и вредоносное ПО

```bash
# Установить rkhunter
ssh -l yc-user 46.21.244.23 'sudo apt install -y rkhunter'

# Обновить базу
ssh -l yc-user 46.21.244.23 'sudo rkhunter --update'

# Сканировать
ssh -l yc-user 46.21.244.23 'sudo rkhunter --check --skip-keypress'

# Установить ClamAV (антивирус)
ssh -l yc-user 46.21.244.23 'sudo apt install -y clamav clamav-daemon'

# Обновить базу вирусов
ssh -l yc-user 46.21.244.23 'sudo freshclam'

# Сканировать
ssh -l yc-user 46.21.244.23 'sudo clamscan -r /home'
```

---

## 📝 Логирование

### Централизованное логирование

```bash
# Настроить rsyslog для отправки логов
ssh -l yc-user 46.21.244.23 'sudo nano /etc/rsyslog.d/50-default.conf'

# Добавить:
# *.* @@your-log-server.com:514  # UDP
# *.* @@your-log-server.com:514  # TCP
```

### Ротация логов

```bash
# Настроить logrotate
ssh -l yc-user 46.21.244.23 'sudo nano /etc/logrotate.d/docker'
```

```
/var/lib/docker/containers/*/*.log {
  rotate 7
  daily
  compress
  missingok
  delaycompress
  copytruncate
}
```

---

## 🔄 Обновления безопасности

### Автоматические обновления безопасности

```bash
ssh -l yc-user 46.21.244.23

# Установить unattended-upgrades
sudo apt install -y unattended-upgrades apt-listchanges

# Настроить
sudo dpkg-reconfigure -plow unattended-upgrades

# Проверить конфигурацию
sudo nano /etc/apt/apt.conf.d/50unattended-upgrades
```

**Рекомендуемые настройки:**
```
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
```

---

## 📋 Чеклист безопасности

### Обязательно

- [ ] SSH только по ключам (пароли отключены)
- [ ] Fail2Ban настроен и работает
- [ ] UFW firewall включен
- [ ] Security Group ограничивает доступ
- [ ] Автоматические обновления безопасности включены
- [ ] Регулярные бэкапы настроены
- [ ] .env.production защищен (chmod 600)
- [ ] Сильные пароли для всех БД

### Рекомендуется

- [ ] SSL/TLS сертификаты установлены
- [ ] Docker контейнеры не запускаются от root
- [ ] Мониторинг логов настроен
- [ ] Ротация секретов запланирована
- [ ] Сканирование на уязвимости настроено
- [ ] SSH на нестандартном порту
- [ ] Ограничение ресурсов для контейнеров

### Периодически (раз в месяц)

- [ ] Проверить логи на подозрительную активность
- [ ] Обновить все пакеты
- [ ] Проверить бэкапы
- [ ] Сканировать на руткиты
- [ ] Проверить открытые порты
- [ ] Проверить активных пользователей

---

## 🆘 В случае взлома

### Если подозреваете компрометацию

1. **Немедленно:**
   ```bash
   # Остановить все сервисы
   ssh -l yc-user 46.21.244.23 'cd ~/medhistory && docker compose -f docker-compose.prod.yml down'
   
   # Создать снимок для анализа
   /Users/boris/yandex-cloud/bin/yc compute snapshot create \
     --name medhistory-compromised-$(date +%Y%m%d) \
     --disk-id fhm7lhk4a8ruibjj7l4e
   ```

2. **Изолировать сервер:**
   ```bash
   # Изменить Security Group (закрыть все порты)
   /Users/boris/yandex-cloud/bin/yc vpc security-group update-rules medhistory-sg --delete-all
   ```

3. **Проанализировать:**
   - Проверить логи доступа
   - Найти точку входа
   - Определить что было скомпрометировано

4. **Восстановить:**
   - Создать новую ВМ из чистого образа
   - Восстановить данные из бэкапа (проверенного)
   - Сменить ВСЕ пароли и ключи

---

## 🔗 Дополнительные ресурсы

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks/)
- [Docker Security](https://docs.docker.com/engine/security/)
- [Ubuntu Security](https://ubuntu.com/security)

---

**Последнее обновление:** 28 октября 2025

**Помните:** Безопасность - это процесс, а не состояние. Регулярно пересматривайте и обновляйте настройки безопасности.


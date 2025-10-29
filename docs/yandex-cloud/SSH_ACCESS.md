# 🔐 SSH подключение к серверу

Все способы подключения к серверу MedHistory по SSH.

---

## 🎯 Основная информация

| Параметр | Значение |
|----------|----------|
| **IP адрес** | `46.21.244.23` |
| **Пользователь** | `yc-user` ⚠️ (НЕ ubuntu!) |
| **Порт** | `22` (стандартный) |
| **SSH ключ** | `~/.ssh/id_rsa` |
| **Тип аутентификации** | Public Key (Yandex Cloud OS Login) |

---

## 🔑 Способы подключения

### 1. Простое подключение (рекомендуется)

```bash
ssh -l yc-user 46.21.244.23
```

Или альтернативный синтаксис:
```bash
ssh yc-user@46.21.244.23
```

### 2. С явным указанием SSH ключа

```bash
ssh -i ~/.ssh/id_rsa -l yc-user 46.21.244.23
```

### 3. Через Yandex Cloud CLI

```bash
/Users/boris/yandex-cloud/bin/yc compute ssh \
  --id fhmsq7s4569qgl1oga4p \
  --identity-file ~/.ssh/id_rsa \
  --login yc-user
```

Или по имени ВМ:
```bash
/Users/boris/yandex-cloud/bin/yc compute ssh \
  --name medhistory-server \
  --identity-file ~/.ssh/id_rsa \
  --login yc-user
```

### 4. С SSH config файлом

Создайте или отредактируйте `~/.ssh/config`:

```bash
# MedHistory Server
Host medhistory
    HostName 46.21.244.23
    User yc-user
    IdentityFile ~/.ssh/id_rsa
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

Теперь можно подключаться просто:
```bash
ssh medhistory
```

---

## ⚡ Выполнение команд

### Одиночная команда (без входа на сервер)

```bash
# Проверка времени работы
ssh -l yc-user 46.21.244.23 'uptime'

# Проверка Docker контейнеров
ssh -l yc-user 46.21.244.23 'docker ps'

# Просмотр использования диска
ssh -l yc-user 46.21.244.23 'df -h'

# Просмотр логов
ssh -l yc-user 46.21.244.23 'cd ~/medhistory && docker compose -f docker-compose.prod.yml logs --tail=50 backend'
```

### Множество команд (heredoc)

```bash
ssh -l yc-user 46.21.244.23 << 'EOF'
echo "=== Статус сервера ==="
hostname
uptime
df -h /
free -h
docker ps
EOF
```

### Интерактивная команда

```bash
# Открыть интерактивный shell внутри контейнера
ssh -t -l yc-user 46.21.244.23 'docker exec -it medhistory_backend bash'
```

Флаг `-t` выделяет псевдо-терминал для интерактивных команд.

---

## 📁 Передача файлов

### SCP (Secure Copy)

#### Загрузка на сервер
```bash
# Один файл
scp file.txt yc-user@46.21.244.23:~/medhistory/

# Папка
scp -r ./backend yc-user@46.21.244.23:~/medhistory/

# С явным указанием ключа
scp -i ~/.ssh/id_rsa file.txt yc-user@46.21.244.23:~/medhistory/
```

#### Скачивание с сервера
```bash
# Один файл
scp yc-user@46.21.244.23:~/medhistory/backup.tar.gz ~/Downloads/

# Папка
scp -r yc-user@46.21.244.23:~/medhistory/logs ~/Downloads/

# Все бэкапы
scp yc-user@46.21.244.23:~/backups/*.tar.gz ~/Downloads/
```

### Rsync (рекомендуется для больших файлов)

```bash
# Синхронизация с сервером
rsync -avz --progress \
  --exclude 'node_modules' \
  --exclude '__pycache__' \
  ./backend/ yc-user@46.21.244.23:~/medhistory/backend/

# Синхронизация с сервера
rsync -avz --progress \
  yc-user@46.21.244.23:~/backups/ ~/local-backups/

# С удалением лишних файлов на сервере
rsync -avz --progress --delete \
  ./frontend/ yc-user@46.21.244.23:~/medhistory/frontend/

# Dry-run (проверка без изменений)
rsync -avz --progress --dry-run \
  ./backend/ yc-user@46.21.244.23:~/medhistory/backend/
```

---

## 🚀 Полезные алиасы

### Добавьте в ~/.zshrc или ~/.bashrc

```bash
# SSH подключение
alias ssh-med='ssh -l yc-user 46.21.244.23'

# Просмотр логов
alias med-logs='ssh -l yc-user 46.21.244.23 "cd ~/medhistory && docker compose -f docker-compose.prod.yml logs -f"'
alias med-logs-backend='ssh -l yc-user 46.21.244.23 "cd ~/medhistory && docker compose -f docker-compose.prod.yml logs -f backend"'
alias med-logs-frontend='ssh -l yc-user 46.21.244.23 "cd ~/medhistory && docker compose -f docker-compose.prod.yml logs -f frontend"'

# Статус
alias med-status='ssh -l yc-user 46.21.244.23 "docker ps"'
alias med-stats='ssh -l yc-user 46.21.244.23 "docker stats --no-stream"'

# Управление
alias med-restart='ssh -l yc-user 46.21.244.23 "cd ~/medhistory && docker compose -f docker-compose.prod.yml restart"'
alias med-stop='ssh -l yc-user 46.21.244.23 "cd ~/medhistory && docker compose -f docker-compose.prod.yml down"'
alias med-start='ssh -l yc-user 46.21.244.23 "cd ~/medhistory && docker compose -f docker-compose.prod.yml --env-file .env.production up -d"'

# Информация о сервере
alias med-info='ssh -l yc-user 46.21.244.23 "echo \"=== Server Info ===\" && hostname && uptime && df -h / && free -h"'

# Загрузка файлов
alias med-upload='rsync -avz --progress --exclude \"node_modules\" --exclude \"__pycache__\" --exclude \".git\"'
```

Применить изменения:
```bash
source ~/.zshrc  # или source ~/.bashrc
```

### Использование алиасов

```bash
# Подключиться
ssh-med

# Посмотреть логи
med-logs

# Проверить статус
med-status

# Загрузить проект
med-upload ./backend/ yc-user@46.21.244.23:~/medhistory/backend/
```

---

## 🔧 Настройка SSH

### Проверка SSH ключа

```bash
# Убедитесь, что ключ существует
ls -la ~/.ssh/id_rsa
ls -la ~/.ssh/id_rsa.pub

# Проверьте права доступа (должны быть строгие)
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub

# Посмотрите содержимое публичного ключа
cat ~/.ssh/id_rsa.pub
```

### Создание нового SSH ключа (если нужно)

```bash
# RSA ключ
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -C "your_email@example.com"

# ED25519 ключ (современный, более безопасный)
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -C "your_email@example.com"
```

### Добавление SSH ключа в ВМ

```bash
# Через YC CLI
/Users/boris/yandex-cloud/bin/yc compute instance add-metadata medhistory-server \
  --metadata ssh-keys="yc-user:$(cat ~/.ssh/id_rsa.pub)"
```

---

## 🛡️ Безопасность

### SSH Hardening на сервере

После первого подключения к серверу:

```bash
ssh -l yc-user 46.21.244.23

# Отредактируйте конфиг SSH
sudo nano /etc/ssh/sshd_config
```

Рекомендуемые настройки:
```
# Отключить аутентификацию по паролю
PasswordAuthentication no

# Отключить root login
PermitRootLogin no

# Разрешить только определенным пользователям
AllowUsers yc-user

# Изменить порт (опционально, не забудьте открыть в Security Group)
# Port 2222

# Ограничить количество попыток
MaxAuthTries 3

# Таймаут неактивной сессии
ClientAliveInterval 300
ClientAliveCountMax 2
```

Перезапустите SSH:
```bash
sudo systemctl restart sshd
```

### Настройка fail2ban (защита от брутфорса)

```bash
ssh -l yc-user 46.21.244.23

# Установка
sudo apt update
sudo apt install -y fail2ban

# Создание конфигурации
sudo nano /etc/fail2ban/jail.local
```

Содержимое:
```ini
[sshd]
enabled = true
port = 22
maxretry = 3
bantime = 3600
findtime = 600
```

Запуск:
```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Проверка статуса
sudo fail2ban-client status sshd
```

---

## 🔍 Диагностика проблем

### Проблема: Connection refused

```bash
# Проверьте, что ВМ запущена
/Users/boris/yandex-cloud/bin/yc compute instance get medhistory-server | grep status

# Проверьте доступность порта 22
nc -zv 46.21.244.23 22
telnet 46.21.244.23 22
```

### Проблема: Permission denied (publickey)

```bash
# 1. Проверьте права на ключ
chmod 600 ~/.ssh/id_rsa

# 2. Очистите known_hosts
ssh-keygen -R 46.21.244.23

# 3. Добавьте ключ в метаданные ВМ
/Users/boris/yandex-cloud/bin/yc compute instance add-metadata medhistory-server \
  --metadata ssh-keys="yc-user:$(cat ~/.ssh/id_rsa.pub)"

# 4. Подождите 10-15 секунд и попробуйте снова
sleep 15
ssh -l yc-user 46.21.244.23
```

### Проблема: Connection timeout

```bash
# Проверьте Security Group
/Users/boris/yandex-cloud/bin/yc vpc security-group get enpo36phcf9ck74h6igk

# Проверьте, что порт 22 открыт
# Должно быть правило: port=22, protocol=tcp, source=0.0.0.0/0
```

### Проблема: Медленное подключение

```bash
# Отключите DNS lookup на сервере
ssh -l yc-user 46.21.244.23
sudo nano /etc/ssh/sshd_config
# Добавьте: UseDNS no
sudo systemctl restart sshd
```

### Подробная диагностика

```bash
# SSH с максимальной детализацией
ssh -vvv -l yc-user 46.21.244.23

# Проверка SSH сервиса на сервере
ssh -l yc-user 46.21.244.23 'sudo systemctl status sshd'

# Проверка логов SSH на сервере
ssh -l yc-user 46.21.244.23 'sudo tail -100 /var/log/auth.log'
```

---

## 📊 Мониторинг SSH подключений

### На локальной машине

```bash
# Активные SSH сессии
ps aux | grep ssh

# История подключений
cat ~/.ssh/known_hosts
```

### На сервере

```bash
ssh -l yc-user 46.21.244.23

# Текущие SSH сессии
who
w

# История входов
last | head -20

# Неудачные попытки входа
sudo lastb | head -20

# Логи SSH
sudo tail -100 /var/log/auth.log | grep sshd
```

---

## 🎓 Best Practices

1. **Всегда используйте SSH ключи**, не пароли
2. **Используйте разные ключи** для разных серверов
3. **Регулярно обновляйте** ключи (раз в год)
4. **Не делитесь** приватными ключами
5. **Используйте парольную фразу** для ключей
6. **Храните бэкап** ключей в безопасном месте
7. **Используйте SSH config** для удобства
8. **Мониторьте** неудачные попытки входа
9. **Настройте fail2ban** для защиты от брутфорса
10. **Отключите аутентификацию по паролю** на сервере

---

## 🔗 Полезные ссылки

- [SSH Manual](https://man.openbsd.org/ssh)
- [SSH Config Documentation](https://man.openbsd.org/ssh_config)
- [Yandex Cloud OS Login](https://cloud.yandex.ru/docs/compute/operations/vm-connect/os-login)

---

**Последнее обновление:** 28 октября 2025


# ⚙️ Yandex Cloud CLI команды

Полный справочник команд YC CLI для управления виртуальной машиной MedHistory.

---

## 📍 Путь к YC CLI

```bash
/Users/boris/yandex-cloud/bin/yc
```

Для удобства можно создать alias:
```bash
alias yc='/Users/boris/yandex-cloud/bin/yc'
```

---

## 🖥️ Управление виртуальными машинами

### Просмотр информации

```bash
# Список всех ВМ
yc compute instance list

# Детальная информация о ВМ (по имени)
yc compute instance get medhistory-server

# Детальная информация о ВМ (по ID)
yc compute instance get fhmsq7s4569qgl1oga4p

# В формате YAML
yc compute instance get medhistory-server --format yaml

# В формате JSON
yc compute instance get fhmsq7s4569qgl1oga4p --format json | jq '.'
```

### Управление питанием

```bash
# Запуск ВМ
yc compute instance start medhistory-server
yc compute instance start fhmsq7s4569qgl1oga4p

# Остановка ВМ (данные сохраняются)
yc compute instance stop medhistory-server
yc compute instance stop fhmsq7s4569qgl1oga4p

# Перезагрузка ВМ
yc compute instance restart medhistory-server
yc compute instance restart fhmsq7s4569qgl1oga4p
```

### Создание ВМ

```bash
# Базовое создание
yc compute instance create \
  --name medhistory-server \
  --zone ru-central1-a \
  --cores 4 \
  --memory 8 \
  --core-fraction 100 \
  --network-interface subnet-name=medhistory-subnet-a,nat-ip-version=ipv4,security-group-ids=enpo36phcf9ck74h6igk \
  --create-boot-disk image-folder-id=standard-images,image-family=ubuntu-2204-lts,size=50,type=network-ssd \
  --ssh-key ~/.ssh/id_rsa.pub \
  --metadata serial-port-enable=1

# С дополнительными опциями
yc compute instance create \
  --name medhistory-server-2 \
  --zone ru-central1-b \
  --cores 8 \
  --memory 16 \
  --core-fraction 100 \
  --platform standard-v3 \
  --network-interface subnet-name=medhistory-subnet-a,nat-ip-version=ipv4,ipv4-address=auto \
  --create-boot-disk image-family=ubuntu-2204-lts,size=100,type=network-ssd \
  --ssh-key ~/.ssh/id_rsa.pub \
  --preemptible \
  --service-account-name medhistory-sa \
  --labels env=production,app=medhistory
```

### Изменение конфигурации

```bash
# Изменить vCPU и RAM (требуется остановка ВМ)
yc compute instance stop medhistory-server
yc compute instance update fhmsq7s4569qgl1oga4p \
  --cores 8 \
  --memory 16
yc compute instance start medhistory-server

# Изменить core-fraction
yc compute instance update fhmsq7s4569qgl1oga4p --core-fraction 50

# Добавить/изменить метаданные
yc compute instance add-metadata medhistory-server \
  --metadata ssh-keys="yc-user:$(cat ~/.ssh/id_rsa.pub)"

# Удалить метаданные
yc compute instance remove-metadata medhistory-server \
  --keys ssh-keys

# Добавить labels
yc compute instance add-labels medhistory-server \
  --labels environment=production,version=1.0

# Изменить имя
yc compute instance update fhmsq7s4569qgl1oga4p \
  --name medhistory-prod-server
```

### Удаление ВМ

```bash
# Удалить ВМ (с подтверждением)
yc compute instance delete medhistory-server

# Удалить без подтверждения
yc compute instance delete fhmsq7s4569qgl1oga4p --async
```

---

## 💾 Управление дисками

### Просмотр дисков

```bash
# Список всех дисков
yc compute disk list

# Информация о конкретном диске
yc compute disk get fhm7lhk4a8ruibjj7l4e

# Диски, подключенные к ВМ
yc compute instance get medhistory-server | grep disk
```

### Изменение размера диска

```bash
# Увеличить размер (можно без остановки ВМ)
yc compute disk update fhm7lhk4a8ruibjj7l4e --size 100

# После увеличения нужно расширить файловую систему на сервере
ssh -l yc-user 46.21.244.23 'sudo resize2fs /dev/vda1'
```

### Создание снимков (snapshots)

```bash
# Создать снимок диска
yc compute snapshot create \
  --name medhistory-snapshot-$(date +%Y%m%d-%H%M%S) \
  --disk-id fhm7lhk4a8ruibjj7l4e \
  --description "Backup before update"

# Список снимков
yc compute snapshot list

# Информация о снимке
yc compute snapshot get medhistory-snapshot-20251028-185000

# Удалить снимок
yc compute snapshot delete medhistory-snapshot-20251028-185000
```

### Создание диска из снимка

```bash
# Создать новый диск из снимка
yc compute disk create \
  --name medhistory-disk-restored \
  --source-snapshot-name medhistory-snapshot-20251028-185000 \
  --size 50
```

### Расписание снимков

```bash
# Создать расписание автоматических снимков
yc compute snapshot-schedule create daily-backup \
  --disk-id fhm7lhk4a8ruibjj7l4e \
  --schedule-policy start-at=02:00,expression="0 2 * * *" \
  --snapshot-count 7 \
  --retention-period 168h

# Список расписаний
yc compute snapshot-schedule list

# Удалить расписание
yc compute snapshot-schedule delete daily-backup
```

---

## 🌐 Управление сетью

### VPC - Virtual Private Cloud

```bash
# Список сетей
yc vpc network list

# Создать сеть
yc vpc network create --name medhistory-network

# Удалить сеть
yc vpc network delete medhistory-network
```

### Подсети (Subnets)

```bash
# Список подсетей
yc vpc subnet list

# Создать подсеть
yc vpc subnet create \
  --name medhistory-subnet-b \
  --network-name medhistory-network \
  --zone ru-central1-b \
  --range 10.129.0.0/24

# Информация о подсети
yc vpc subnet get medhistory-subnet-a

# Удалить подсеть
yc vpc subnet delete medhistory-subnet-b
```

### IP адреса

```bash
# Список всех внешних IP адресов
yc vpc address list

# Зарезервировать статический IP
yc vpc address create \
  --name medhistory-static-ip \
  --zone ru-central1-a \
  --external-ipv4 zone=ru-central1-a

# Привязать IP к ВМ
yc compute instance add-one-to-one-nat \
  --id fhmsq7s4569qgl1oga4p \
  --network-interface-index 0 \
  --nat-address <STATIC_IP>

# Удалить NAT
yc compute instance remove-one-to-one-nat \
  --id fhmsq7s4569qgl1oga4p \
  --network-interface-index 0
```

### Security Groups (Группы безопасности)

```bash
# Список групп безопасности
yc vpc security-group list

# Подробная информация
yc vpc security-group get medhistory-sg
yc vpc security-group get enpo36phcf9ck74h6igk

# Создать группу безопасности
yc vpc security-group create \
  --name medhistory-sg-new \
  --network-name medhistory-network \
  --rule "direction=ingress,port=22,protocol=tcp,v4-cidrs=[0.0.0.0/0]" \
  --rule "direction=ingress,port=80,protocol=tcp,v4-cidrs=[0.0.0.0/0]" \
  --rule "direction=ingress,port=443,protocol=tcp,v4-cidrs=[0.0.0.0/0]" \
  --rule "direction=egress,port=any,protocol=any,v4-cidrs=[0.0.0.0/0]"

# Добавить правило
yc vpc security-group update-rules medhistory-sg \
  --add-rule "direction=ingress,port=8080,protocol=tcp,v4-cidrs=[0.0.0.0/0]"

# Удалить правило
yc vpc security-group update-rules medhistory-sg \
  --delete-rule-id <RULE_ID>

# Применить группу безопасности к ВМ
yc compute instance update-network-interface medhistory-server \
  --network-interface-index 0 \
  --security-group-ids enpo36phcf9ck74h6igk
```

---

## 🔐 SSH и подключение

### SSH через YC CLI

```bash
# Подключение по имени ВМ
yc compute ssh \
  --name medhistory-server \
  --login yc-user \
  --identity-file ~/.ssh/id_rsa

# Подключение по ID ВМ
yc compute ssh \
  --id fhmsq7s4569qgl1oga4p \
  --login yc-user \
  --identity-file ~/.ssh/id_rsa

# Выполнить команду
yc compute ssh \
  --name medhistory-server \
  --login yc-user \
  -- 'docker ps'
```

### Serial Console

```bash
# Получить вывод serial console
yc compute instance get-serial-port-output medhistory-server

# Последние 100 строк
yc compute instance get-serial-port-output fhmsq7s4569qgl1oga4p | tail -100

# Сохранить в файл
yc compute instance get-serial-port-output medhistory-server > serial-console.log
```

---

## 📊 Мониторинг и логи

### Операции с ВМ

```bash
# История операций
yc compute instance list-operations medhistory-server

# Подробности операции
yc compute instance list-operations fhmsq7s4569qgl1oga4p --limit 10 --format yaml
```

### Метрики (требует настройки Monitoring)

```bash
# Экспорт метрик
yc monitoring metric list \
  --folder-id b1gudpmb327g7hf8rc5i \
  --service compute
```

---

## 🔧 Конфигурация YC CLI

### Профили

```bash
# Список профилей
yc config profile list

# Активный профиль
yc config profile get

# Создать новый профиль
yc config profile create prod

# Переключиться на профиль
yc config profile activate prod

# Удалить профиль
yc config profile delete prod
```

### Настройки

```bash
# Показать текущие настройки
yc config list

# Установить параметры
yc config set folder-id b1gudpmb327g7hf8rc5i
yc config set compute-default-zone ru-central1-a
yc config set format yaml

# Сбросить настройки
yc config unset folder-id
```

### Аутентификация

```bash
# Получить IAM токен
yc iam create-token

# Информация о текущем пользователе
yc iam user-account get
```

---

## 💰 Биллинг и квоты

### Информация об аккаунте

```bash
# ID облака и каталога
yc config list

# Информация об облаке
yc resource-manager cloud list

# Информация о каталоге
yc resource-manager folder get b1gudpmb327g7hf8rc5i
```

### Квоты

```bash
# Просмотр квот (через веб-консоль)
# https://console.cloud.yandex.ru/folders/b1gudpmb327g7hf8rc5i/quotas
```

---

## 🚀 Полезные скрипты

### Создание ВМ одной командой

```bash
#!/bin/bash
# create-vm-quick.sh

VM_NAME="medhistory-server"
ZONE="ru-central1-a"
SUBNET="medhistory-subnet-a"
SG="enpo36phcf9ck74h6igk"

yc compute instance create \
  --name $VM_NAME \
  --zone $ZONE \
  --cores 4 \
  --memory 8 \
  --core-fraction 100 \
  --network-interface subnet-name=$SUBNET,nat-ip-version=ipv4,security-group-ids=$SG \
  --create-boot-disk image-family=ubuntu-2204-lts,size=50,type=network-ssd \
  --ssh-key ~/.ssh/id_rsa.pub \
  --metadata serial-port-enable=1

IP=$(yc compute instance get $VM_NAME --format json | jq -r '.network_interfaces[0].primary_v4_address.one_to_one_nat.address')
echo "VM created! IP: $IP"
echo "Connect: ssh -l yc-user $IP"
```

### Мониторинг статуса

```bash
#!/bin/bash
# check-vm-status.sh

VM_ID="fhmsq7s4569qgl1oga4p"

echo "=== VM Status ==="
yc compute instance get $VM_ID --format json | jq -r '
  "Status: " + .status,
  "IP: " + .network_interfaces[0].primary_v4_address.one_to_one_nat.address,
  "Created: " + .created_at
'

echo -e "\n=== Disk Usage ==="
yc compute disk list --format json | jq -r '.[] | 
  select(.id == "fhm7lhk4a8ruibjj7l4e") |
  "Size: \(.size/1024/1024/1024)GB, Type: \(.type_id)"
'
```

### Автоматический бэкап

```bash
#!/bin/bash
# auto-backup.sh

DISK_ID="fhm7lhk4a8ruibjj7l4e"
SNAPSHOT_NAME="auto-backup-$(date +%Y%m%d-%H%M%S)"

echo "Creating snapshot: $SNAPSHOT_NAME"
yc compute snapshot create \
  --name $SNAPSHOT_NAME \
  --disk-id $DISK_ID \
  --description "Automatic backup"

# Удалить старые снимки (оставить последние 7)
yc compute snapshot list --format json | \
  jq -r '.[] | select(.name | startswith("auto-backup")) | .name' | \
  sort -r | tail -n +8 | \
  while read name; do
    echo "Deleting old snapshot: $name"
    yc compute snapshot delete $name
  done
```

---

## 📖 Справка и документация

```bash
# Общая справка
yc --help

# Справка по compute
yc compute --help

# Справка по instance
yc compute instance --help

# Справка по конкретной команде
yc compute instance create --help

# Версия CLI
yc version

# Обновление CLI
curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
```

---

## 🔗 Полезные ссылки

- [YC CLI Documentation](https://cloud.yandex.ru/docs/cli/)
- [Compute Cloud API](https://cloud.yandex.ru/docs/compute/api-ref/)
- [Консоль Yandex Cloud](https://console.cloud.yandex.ru/)

---

**Последнее обновление:** 28 октября 2025


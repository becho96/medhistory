#!/bin/bash

# ==================================================
# Скрипт для создания виртуальной машины в Яндекс.Облаке
# ==================================================
# Использование:
#   ./scripts/create-vm.sh
# ==================================================

set -e

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Создание виртуальной машины MedHistory в Яндекс.Облаке${NC}"
echo ""

# Проверка что YC CLI установлен
if ! command -v yc &> /dev/null; then
    echo -e "${RED}✗ YC CLI не установлен${NC}"
    echo "  Установите: curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash"
    exit 1
fi

# Проверка что YC CLI инициализирован
if ! yc config list &> /dev/null; then
    echo -e "${RED}✗ YC CLI не инициализирован${NC}"
    echo "  Запустите: yc init"
    exit 1
fi

echo -e "${YELLOW}📋 Текущая конфигурация YC CLI:${NC}"
yc config list
echo ""

# Параметры ВМ
VM_NAME="medhistory-server"
ZONE="ru-central1-a"
CORES=4
MEMORY=8
DISK_SIZE=50
IMAGE_FAMILY="ubuntu-2204-lts"
IMAGE_FOLDER="standard-images"

# Проверка наличия SSH ключа
SSH_KEY="$HOME/.ssh/id_rsa.pub"
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${YELLOW}⚠️  SSH ключ не найден в $SSH_KEY${NC}"
    echo -e "${YELLOW}Создаем новый SSH ключ...${NC}"
    ssh-keygen -t rsa -b 4096 -f "$HOME/.ssh/id_rsa" -N ""
    echo -e "${GREEN}✓${NC} SSH ключ создан"
    echo ""
fi

# Получение списка подсетей
echo -e "${YELLOW}🔍 Поиск доступных подсетей...${NC}"
SUBNETS=$(yc vpc subnet list --format json)

if [ "$(echo "$SUBNETS" | jq length)" -eq 0 ]; then
    echo -e "${RED}✗ Нет доступных подсетей${NC}"
    echo -e "${YELLOW}Создание сети и подсети...${NC}"
    
    # Создание сети
    yc vpc network create --name medhistory-network --description "MedHistory application network"
    
    # Создание подсети
    yc vpc subnet create \
        --name medhistory-subnet-a \
        --network-name medhistory-network \
        --zone ru-central1-a \
        --range 10.128.0.0/24
    
    SUBNET_NAME="medhistory-subnet-a"
    echo -e "${GREEN}✓${NC} Сеть и подсеть созданы"
else
    # Использование существующей подсети
    SUBNET_NAME=$(echo "$SUBNETS" | jq -r '.[0].name')
    echo -e "${GREEN}✓${NC} Используется существующая подсеть: $SUBNET_NAME"
fi
echo ""

# Создание группы безопасности
echo -e "${YELLOW}🔒 Создание группы безопасности...${NC}"
NETWORK_NAME=$(yc vpc subnet get "$SUBNET_NAME" --format json | jq -r '.network_id')

# Проверка существования группы безопасности
SG_EXISTS=$(yc vpc security-group list --format json | jq -r '.[] | select(.name=="medhistory-sg") | .id')

if [ -z "$SG_EXISTS" ]; then
    SG_ID=$(yc vpc security-group create \
        --name medhistory-sg \
        --network-id "$NETWORK_NAME" \
        --rule "direction=ingress,port=22,protocol=tcp,v4-cidrs=[0.0.0.0/0],description=SSH" \
        --rule "direction=ingress,port=80,protocol=tcp,v4-cidrs=[0.0.0.0/0],description=HTTP" \
        --rule "direction=ingress,port=443,protocol=tcp,v4-cidrs=[0.0.0.0/0],description=HTTPS" \
        --rule "direction=egress,port=any,protocol=any,v4-cidrs=[0.0.0.0/0],description=Allow-all-outgoing" \
        --format json | jq -r '.id')
    echo -e "${GREEN}✓${NC} Группа безопасности создана: $SG_ID"
else
    SG_ID=$SG_EXISTS
    echo -e "${GREEN}✓${NC} Используется существующая группа безопасности: $SG_ID"
fi
echo ""

# Создание виртуальной машины
echo -e "${YELLOW}🖥️  Создание виртуальной машины...${NC}"
echo -e "${BLUE}Параметры:${NC}"
echo "  - Имя: $VM_NAME"
echo "  - Зона: $ZONE"
echo "  - CPU: $CORES vCPU"
echo "  - RAM: $MEMORY GB"
echo "  - Диск: $DISK_SIZE GB SSD"
echo "  - ОС: Ubuntu 22.04 LTS"
echo ""

# Проверка существования ВМ с таким именем
VM_EXISTS=$(yc compute instance list --format json | jq -r '.[] | select(.name=="'$VM_NAME'") | .id')

if [ -n "$VM_EXISTS" ]; then
    echo -e "${YELLOW}⚠️  ВМ с именем $VM_NAME уже существует${NC}"
    read -p "Удалить существующую ВМ и создать новую? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Удаление существующей ВМ...${NC}"
        yc compute instance delete "$VM_EXISTS"
        echo -e "${GREEN}✓${NC} ВМ удалена"
    else
        echo -e "${YELLOW}Отменено${NC}"
        exit 0
    fi
fi

# Создание ВМ
VM_DATA=$(yc compute instance create \
    --name "$VM_NAME" \
    --zone "$ZONE" \
    --cores "$CORES" \
    --memory "$MEMORY" \
    --core-fraction 100 \
    --network-interface subnet-name="$SUBNET_NAME",nat-ip-version=ipv4,security-group-ids="$SG_ID" \
    --create-boot-disk image-folder-id="$IMAGE_FOLDER",image-family="$IMAGE_FAMILY",size="$DISK_SIZE",type=network-ssd \
    --ssh-key "$SSH_KEY" \
    --format json)

VM_ID=$(echo "$VM_DATA" | jq -r '.id')
VM_IP=$(echo "$VM_DATA" | jq -r '.network_interfaces[0].primary_v4_address.one_to_one_nat.address')

echo ""
echo -e "${GREEN}✅ Виртуальная машина создана успешно!${NC}"
echo ""
echo -e "${BLUE}📋 Информация о ВМ:${NC}"
echo "  - ID: $VM_ID"
echo "  - Имя: $VM_NAME"
echo "  - Внешний IP: $VM_IP"
echo "  - Зона: $ZONE"
echo "  - Конфигурация: $CORES vCPU, $MEMORY GB RAM"
echo ""
echo -e "${YELLOW}⏳ ВМ запускается... Подождите 1-2 минуты${NC}"
echo ""

# Ожидание запуска ВМ
sleep 30

echo -e "${GREEN}🔗 Следующие шаги:${NC}"
echo ""
echo "1. Подключитесь к серверу:"
echo -e "   ${BLUE}ssh ubuntu@$VM_IP${NC}"
echo ""
echo "2. Запустите скрипт настройки сервера:"
echo -e "   ${BLUE}curl -sSL https://raw.githubusercontent.com/your-repo/main/scripts/setup-server.sh | bash${NC}"
echo "   Или скопируйте проект на сервер и запустите:"
echo -e "   ${BLUE}./scripts/setup-server.sh${NC}"
echo ""
echo "3. Перезагрузите сервер:"
echo -e "   ${BLUE}sudo reboot${NC}"
echo ""
echo "4. Обновите .env.production с IP адресом:"
echo -e "   ${BLUE}VITE_API_URL=http://$VM_IP${NC}"
echo ""

# Сохранение информации о ВМ
cat > vm-info.txt << EOF
Виртуальная машина MedHistory
================================
ID: $VM_ID
Имя: $VM_NAME
IP: $VM_IP
Зона: $ZONE
Конфигурация: $CORES vCPU, $MEMORY GB RAM
Дата создания: $(date)

SSH подключение:
ssh ubuntu@$VM_IP

Удаление ВМ:
yc compute instance delete $VM_ID
EOF

echo -e "${GREEN}✓${NC} Информация сохранена в vm-info.txt"
echo ""
echo -e "${YELLOW}💰 Примерная стоимость: ~3,500₽/месяц${NC}"
echo ""
echo -e "${GREEN}Удачи! 🚀${NC}"


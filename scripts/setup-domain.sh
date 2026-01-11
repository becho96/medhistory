#!/bin/bash

# ========================================
# Скрипт настройки домена для MedHistory
# ========================================

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Конфигурация (ИЗМЕНИТЕ ЭТИ ЗНАЧЕНИЯ)
DOMAIN=""
EMAIL=""
SERVER_IP="158.160.99.232"
SERVER_USER="yc-user"
REMOTE_PATH="~/medhistory"

# Функция вывода
log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Проверка аргументов
usage() {
    echo "Использование: $0 -d <домен> -e <email>"
    echo ""
    echo "Опции:"
    echo "  -d    Доменное имя (например: medhistory.ru)"
    echo "  -e    Email для Let's Encrypt сертификата"
    echo ""
    echo "Пример:"
    echo "  $0 -d medhistory.ru -e admin@medhistory.ru"
    exit 1
}

while getopts "d:e:h" opt; do
    case $opt in
        d) DOMAIN="$OPTARG" ;;
        e) EMAIL="$OPTARG" ;;
        h) usage ;;
        *) usage ;;
    esac
done

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    error "Необходимо указать домен (-d) и email (-e)"
    usage
fi

echo ""
echo "========================================="
echo "  🌐 Настройка домена для MedHistory"
echo "========================================="
echo ""
echo "Домен:  ${DOMAIN}"
echo "Email:  ${EMAIL}"
echo "Сервер: ${SERVER_IP}"
echo ""

# Проверка DNS
log "Проверка DNS записей..."
DNS_IP=$(dig +short "$DOMAIN" A 2>/dev/null | head -1)

if [ -z "$DNS_IP" ]; then
    error "DNS запись для $DOMAIN не найдена. Убедитесь, что A-запись настроена и подождите распространения DNS."
fi

if [ "$DNS_IP" != "$SERVER_IP" ]; then
    warn "DNS указывает на $DNS_IP, а не на $SERVER_IP"
    read -p "Продолжить? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

success "DNS проверен: $DOMAIN → $DNS_IP"

# Создание nginx конфигурации
log "Создание nginx конфигурации для $DOMAIN..."

NGINX_CONFIG="user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '\$remote_addr - \$remote_user [\$time_local] \"\$request\" '
                    '\$status \$body_bytes_sent \"\$http_referer\" '
                    '\"\$http_user_agent\" \"\$http_x_forwarded_for\"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 25M;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript 
               application/json application/javascript application/xml+rss 
               application/rss+xml font/truetype font/opentype 
               application/vnd.ms-fontobject image/svg+xml;
    gzip_disable \"msie6\";

    # Rate limiting
    limit_req_zone \$binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone \$binary_remote_addr zone=upload_limit:10m rate=2r/s;

    # Upstream servers
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:80;
    }

    upstream grafana {
        server grafana:3000;
    }

    # HTTP server - redirect to HTTPS
    server {
        listen 80;
        server_name ${DOMAIN} www.${DOMAIN};

        # For Let's Encrypt challenges
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        # Redirect all HTTP to HTTPS
        location / {
            return 301 https://\$host\$request_uri;
        }
    }

    # HTTPS server
    server {
        listen 443 ssl http2;
        server_name ${DOMAIN} www.${DOMAIN};

        # SSL configuration (Let's Encrypt)
        ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;

        # Security headers
        add_header Strict-Transport-Security \"max-age=31536000; includeSubDomains\" always;
        add_header X-Frame-Options \"SAMEORIGIN\" always;
        add_header X-Content-Type-Options \"nosniff\" always;
        add_header X-XSS-Protection \"1; mode=block\" always;
        add_header Referrer-Policy \"no-referrer-when-downgrade\" always;

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        # API proxy
        location /api/ {
            limit_req zone=api_limit burst=20 nodelay;
            
            proxy_pass http://backend;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            
            # CORS headers
            add_header 'Access-Control-Allow-Origin' '*' always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
            add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type' always;
            
            if (\$request_method = 'OPTIONS') {
                return 204;
            }
        }

        # File upload with rate limiting
        location /api/v1/documents/upload {
            limit_req zone=upload_limit burst=5 nodelay;
            
            proxy_pass http://backend;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            
            # Increased timeouts for file upload
            proxy_connect_timeout 300s;
            proxy_send_timeout 300s;
            proxy_read_timeout 300s;
        }

        # API documentation
        location /docs {
            proxy_pass http://backend/docs;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        location /openapi.json {
            proxy_pass http://backend/openapi.json;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        # Grafana monitoring dashboard
        location /grafana/ {
            proxy_pass http://grafana/;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            
            proxy_redirect off;
            
            # WebSocket support for live updates
            proxy_http_version 1.1;
            proxy_set_header Upgrade \$http_upgrade;
            proxy_set_header Connection \"upgrade\";
        }

        # Health check
        location /health {
            access_log off;
            return 200 \"healthy\\n\";
            add_header Content-Type text/plain;
        }
    }
}"

# Сохранение конфигурации локально
TEMP_NGINX_CONF="/tmp/nginx-${DOMAIN}.conf"
echo "$NGINX_CONFIG" > "$TEMP_NGINX_CONF"
success "Nginx конфигурация создана"

# Подключение к серверу и настройка
log "Подключение к серверу ${SERVER_IP}..."

# 1. Установка certbot если не установлен
log "Проверка и установка certbot..."
ssh ${SERVER_USER}@${SERVER_IP} << 'REMOTE_SCRIPT'
if ! command -v certbot &> /dev/null; then
    echo "Установка certbot..."
    sudo apt update
    sudo apt install -y certbot
fi
echo "Certbot готов"
REMOTE_SCRIPT

# 2. Остановка nginx для получения сертификата
log "Подготовка к получению SSL сертификата..."
ssh ${SERVER_USER}@${SERVER_IP} << REMOTE_SCRIPT
cd ${REMOTE_PATH}
docker compose stop nginx 2>/dev/null || true
REMOTE_SCRIPT

# 3. Получение SSL сертификата
log "Получение SSL сертификата от Let's Encrypt..."
ssh ${SERVER_USER}@${SERVER_IP} << REMOTE_SCRIPT
sudo certbot certonly --standalone \
    -d ${DOMAIN} \
    -d www.${DOMAIN} \
    --email ${EMAIL} \
    --agree-tos \
    --non-interactive
REMOTE_SCRIPT

if [ $? -ne 0 ]; then
    error "Не удалось получить SSL сертификат"
fi

success "SSL сертификат получен"

# 4. Копирование nginx конфигурации на сервер
log "Копирование nginx конфигурации на сервер..."
scp "$TEMP_NGINX_CONF" ${SERVER_USER}@${SERVER_IP}:${REMOTE_PATH}/nginx/nginx.conf

# 5. Обновление docker-compose для монтирования сертификатов
log "Обновление docker-compose конфигурации..."
ssh ${SERVER_USER}@${SERVER_IP} << 'REMOTE_SCRIPT'
cd ~/medhistory

# Проверяем, есть ли уже монтирование сертификатов
if ! grep -q "letsencrypt" docker-compose.yml 2>/dev/null; then
    echo "Добавление монтирования сертификатов в docker-compose.yml..."
    
    # Создаем backup
    cp docker-compose.yml docker-compose.yml.backup
    
    # Добавляем volume для сертификатов в nginx сервис
    # Это делается через sed
    sed -i '/nginx:/,/volumes:/{
        /volumes:/a\      - /etc/letsencrypt:/etc/letsencrypt:ro
    }' docker-compose.yml
fi
REMOTE_SCRIPT

# 6. Перезапуск сервисов
log "Перезапуск сервисов..."
ssh ${SERVER_USER}@${SERVER_IP} << REMOTE_SCRIPT
cd ${REMOTE_PATH}
docker compose up -d nginx
REMOTE_SCRIPT

# 7. Настройка автоматического обновления сертификата
log "Настройка автоматического обновления сертификата..."
ssh ${SERVER_USER}@${SERVER_IP} << 'REMOTE_SCRIPT'
# Добавляем cron задачу для обновления сертификата
(crontab -l 2>/dev/null | grep -v certbot; echo "0 3 * * * certbot renew --quiet --post-hook 'docker restart medhistory_nginx'") | crontab -
REMOTE_SCRIPT

success "Автоматическое обновление сертификата настроено"

# 8. Проверка
log "Проверка работы сервиса..."
sleep 5

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://${DOMAIN}" 2>/dev/null || echo "000")

if [ "$HTTP_STATUS" = "200" ]; then
    success "Сервис работает!"
else
    warn "Получен HTTP статус: $HTTP_STATUS"
fi

# Очистка
rm -f "$TEMP_NGINX_CONF"

echo ""
echo "========================================="
echo "  ✅ Настройка домена завершена!"
echo "========================================="
echo ""
echo "🔗 Ваш сервис доступен по адресам:"
echo "   https://${DOMAIN}"
echo "   https://www.${DOMAIN}"
echo ""
echo "📝 API документация:"
echo "   https://${DOMAIN}/docs"
echo ""
echo "📊 Мониторинг (Grafana):"
echo "   https://${DOMAIN}/grafana/"
echo ""
echo "🔐 SSL сертификат будет автоматически"
echo "   обновляться каждые 60-90 дней"
echo ""

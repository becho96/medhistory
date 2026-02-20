1) приложение работает в двух конфигурациях
- local: в локальном докере. для развертывания нужно всегда использовать deploy.local
- prod: развертывание происходит через .github/workflows/deploy.yml после того как мы запушим обновление через git

2) На текущий момент я использую ресурсы Яндекс облака для развертывания prod конфигурации. Инструкция для управления этим сервером находится в docs/yandex-cloud/SERVER_MANAGEMENT.md

Проверка prod (05.02.2026 16:20):
- IP: 93.77.182.26 ✅ 
- VM статус: RUNNING ✅
- Production конфигурация: docker-compose.prod.yml ✅
- Все контейнеры: RUNNING ✅
  • postgres: Up 1 min (healthy)
  • mongodb: Up 1 min (healthy)
  • minio: Up 1 min (healthy)
  • backend: Up 1 min (healthy) - production build
  • frontend: Up 1 min (healthy) - production build с nginx
  • nginx: Up 21 sec (reverse proxy)

Доступность через nginx reverse proxy:
- Frontend: http://93.77.182.26/ ✅ (HTTP 200)
- API через proxy: http://93.77.182.26/api/v1/* ✅ (HTTP 200/401)
- API docs: http://93.77.182.26/docs ✅ (HTTP 200)
- Health check: http://93.77.182.26/health ✅ (HTTP 200)

⚠️ ВАЖНО:
- IP адрес динамический и меняется после остановки/запуска VM
- Рекомендуется зарезервировать статический IP
- SERVER_IP в GitHub Secrets: 93.77.182.26 ✅

3) также есть ТГ бот, через который пользователи могут взаимодействовать с сервисом. Логика бота реализована в n8n. Подробнее в n8n/workflows/medhistory_telegram_bot.json.

4) n8n развернут как в локальной конфигурации в отдельном докере. Подробнее в docker-compose.yml. Так и в продакшн конфигурации, подробнее в docker-compose.prod.yml


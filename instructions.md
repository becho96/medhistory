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

✅ ИСПРАВЛЕНО (05.02.2026):
- Добавлен docker-compose.prod.yml для production развертывания
- Настроен nginx как reverse proxy (порт 80)
- Frontend теперь использует production build (Vite + nginx)
- Backend использует production build (без --reload, 4 workers)
- API доступен через /api/* (проксирование через nginx)
- Исправлены TypeScript ошибки в frontend коде
- GitHub Actions обновлен для использования production конфигурации


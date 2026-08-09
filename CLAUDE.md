# CLAUDE.md — MedHistory

Поведенческие принципы + специфика проекта. Файл должен оставаться коротким — прежде чем добавить строку, подумай, не убрать ли другую.

## 1. Принципы работы

**Думай до кода.** Явно проговаривай допущения. Если возможны разные интерпретации — назови их, не выбирай молча. Непонятно — остановись и спроси.

**Простота прежде всего.** Минимум кода, который решает задачу. Никаких фич, абстракций и обработки ошибок сверх того, что просили. Если задача решается в 50 строк, а ты написал 200 — перепиши.

**Хирургические изменения.** Трогай только то, что требует задача. Не "улучшай" соседний код, не переформатируй. Следуй существующему стилю. Удаляй только то, что стало лишним из-за ТВОИХ правок.

**Цели, а не шаги.** Превращай задачи в проверяемые цели ("добавить валидацию" → "написать падающий тест, потом сделать, чтобы он прошёл"). Для многошаговой работы перед кодом озвучь короткий план с проверками.

## 2. О проекте

Управление медицинской историей (medhistory.ru). FastAPI + React 18 + PostgreSQL + MongoDB + MinIO. UI, медицинская терминология и промпты к LLM — на **русском**; код и коммиты — на английском.

## 3. Точки входа и подводные камни

- Backend entry: [backend/main.py](backend/main.py) — НЕ `backend/app/main.py`.
- API router: [backend/app/api/v1/router.py](backend/app/api/v1/router.py)
- Auth deps: [backend/app/api/deps.py](backend/app/api/deps.py) — `get_current_user`, `get_db`
- Frontend entry: [frontend/src/App.tsx](frontend/src/App.tsx)
- JWT хранится в `localStorage` под ключом `auth_token`.
- Telegram-бот: отдельный сервис [bot/](bot/) — aiogram, long-polling, свой контейнер; backend-роутер `/api/v1/bot/*`.

## 4. Сборка и запуск

```bash
./deploy.local              # стандартный локальный запуск (Docker)
./deploy.local --rebuild    # пересобрать образы
./deploy.local --update     # быстрое обновление без пересборки

cd frontend && npm run dev         # Vite dev на :5173
cd frontend && npm run build       # tsc + vite build
cd frontend && npm run lint        # ESLint, max-warnings 0
```

Перед тем как объявить фронтенд-работу готовой — проверь, что TypeScript собирается (`npm run build` или `npx tsc --noEmit`).

## 4.1 Тестирование UI

- Для тестирования UI — **MCP Playwright** (инструменты `mcp__playwright__browser_*`), не ручные инструкции пользователю.
- Тестируй на **dev-сборке локально** (`cd frontend && npm run dev` → http://localhost:5173), не на проде.
- Тестовая учётка: `becho15rus@gmail.com` / `1234567890`.

## 5. Базы данных

- **PostgreSQL** — реляционные данные (users, documents, interpretations, chat_*).
- **MongoDB** — `document_metadata`. Значения анализов: `extracted_data.lab_results`. Summary: `extracted_data.summary`. Классификация: `classification.specialties` (массив).
- **MinIO** — сырые файлы.

**Миграции:** сырой SQL в [backend/migrations/](backend/migrations/) как `00N_*.sql` (на текущий момент последняя — `022`). Применять через:
```bash
psql -U medhistory_user medhistory -f backend/migrations/XXX_*.sql
```
НЕ вводи Alembic для новых миграций — продолжай нумерованный SQL-паттерн.

## 6. AI / LLM

- **Анализ документов** (prod, существующий): OpenRouter → Gemini 2.5 Flash.
- **Ассистент** (LangGraph multi-agent, новый): Anthropic Claude через `langchain-anthropic`.
- LLM factory: [backend/app/services/assistant/llm_factory.py](backend/app/services/assistant/llm_factory.py)
- Graph: [backend/app/services/assistant/graph.py](backend/app/services/assistant/graph.py)
- WebSocket: `WS /api/v1/assistant/ws?token=<jwt>`
- MCP-сервер (отдельно): `python -m mcp_server.server`

Нужны `ANTHROPIC_API_KEY` и `OPENROUTER_API_KEY` в `.env.local`.

## 7. Деплой — две конфигурации, не смешивать

- **local**: `./deploy.local` → [docker-compose.yml](docker-compose.yml) + `.env.local`
- **prod**: **Timeweb Cloud** (`194.87.140.190`, статический IP) → GitHub Actions (ручной `workflow_dispatch`) → [docker-compose.prod.yml](docker-compose.prod.yml) + `.env.production` в `/root/medhistory/` на сервере.

Полная документация по проду — [docs/timeweb/DEPLOYMENT.md](docs/timeweb/DEPLOYMENT.md) (инфраструктура, GitHub Secrets, flow деплоя, список контейнеров, известные фиксы).

SSH: `ssh -i ~/.ssh/medhistory_deploy root@194.87.140.190`. Паролевая авторизация отключена.

Миграция с Yandex Cloud завершена: DNS указывает на Timeweb, Let's Encrypt сертификат выпущен (auto-renew через certbot контейнер), nginx работает по HTTPS. Поддомен `www.medhistory.ru` пока не настроен (нужна A-запись + перевыпуск сертификата с двумя `-d`).

Никогда не редактируй `.env.production` без явной просьбы — там prod-секреты.

## 8. Конвенции (то, чего нет в глобальных правилах)

- Новые backend-эндпоинты: кладутся в `backend/app/api/v1/endpoints/`, регистрируются в `router.py`.
- Запросы с фронта: TanStack Query хуки через [frontend/src/services/](frontend/src/services/), а не разбросанные `fetch`/`axios` в компонентах.
- Состояние: Zustand-сторы в [frontend/src/stores/](frontend/src/stores/).
- Не логируй значения PII (содержимое документов, числовые значения анализов) — только ID.
- Регистрация требует двух согласий 152-ФЗ — `terms_and_privacy` и `special_category` — хранятся в таблице `user_consents` с sha256 текста. Юр. документы лежат в [frontend/public/legal/](frontend/public/legal/).

## 9. При работе с этим репозиторием

- Пользователь — соло-разработчик, русскоязычный. Объяснения на русском, код и коммиты — на английском.
- Перед рискованными/неоднозначными изменениями (миграции, prod-конфиг, auth-флоу) — покажи план и дождись подтверждения.
- Если правка затрагивает `.env.production`, `deploy.local`, `nginx/` или GitHub Actions workflows — сначала уточни границы задачи.

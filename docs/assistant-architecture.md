# Архитектура ИИ-ассистента MedHistory

## Обзор

ИИ-ассистент — это многоагентная система на базе **LangGraph**, встроенная в FastAPI-бэкенд. Она отвечает на медицинские вопросы пользователя, опираясь на его реальные данные из PostgreSQL и MongoDB.

Связь с клиентом — через **WebSocket** с потоковой передачей токенов.

---

## Схема графа

```
Входящее сообщение
        │
        ▼
 load_profile          ← загружает имя, пол, возраст из PostgreSQL
        │
        ▼
   supervisor          ← классифицирует intent, извлекает параметры (LLM-вызов)
        │
   ┌────┴────────────────────────┐
   │ intent == general_qa        │ intent != general_qa
   ▼                             ▼
general_qa                data_retrieval     ← выбирает источники по intent
   │                             │
   ▼                     ┌───────┼───────────────┐
  END              lab_analysis  health_history  recommendation
                         │             │              │
                         └─────────────┴──────────────┘
                                       │
                                      END
```

---

## Компоненты

### 1. Транспортный слой — `assistant.py`

**Файл:** `backend/app/api/v1/endpoints/assistant.py`

WebSocket-эндпоинт `WS /api/v1/assistant/ws?token=<jwt>`.

**Протокол клиент → сервер:**
```json
{
  "message": "какие анализы я сдавал?",
  "session_id": "uuid или null",
  "model": { "provider": "openrouter", "model_id": "google/gemini-2.5-flash" }
}
```

**Протокол сервер → клиент (стриминг):**

| Тип события      | Когда                                        |
|------------------|----------------------------------------------|
| `session_created`| При создании новой сессии                    |
| `thinking`       | При старте каждого агента                    |
| `token`          | Потоковый токен ответа (стриминг)            |
| `done`           | Ответ завершён, содержит `intent`, `message_id` |
| `error`          | Ошибка обработки                             |

**REST-эндпоинты:**

| Метод    | Путь                                     | Описание                    |
|----------|------------------------------------------|-----------------------------|
| `GET`    | `/sessions`                              | Список сессий пользователя  |
| `DELETE` | `/sessions/{id}`                         | Удалить сессию              |
| `GET`    | `/sessions/{id}/messages`               | История сообщений           |
| `GET`    | `/models`                                | Доступные провайдеры/модели |

**Жизненный цикл сообщения:**
1. Аутентификация по JWT из query-параметра `?token=`
2. Получение или создание `ChatSession` в PostgreSQL
3. Загрузка истории последних `CHAT_HISTORY_LIMIT` (20) сообщений
4. Построение и запуск LangGraph-графа (`build_graph`)
5. Стриминг токенов клиенту через `astream_events`
6. Сохранение сообщений и коммит транзакции
7. Автоматическая генерация заголовка сессии (при первом сообщении)

---

### 2. Состояние графа — `state.py`

**Файл:** `backend/app/services/assistant/state.py`

```python
class MedicalAssistantState(TypedDict):
    messages:        list[BaseMessage]   # история диалога (add_messages reducer)
    user_id:         str
    session_id:      str
    model_config:    dict                # {"provider": ..., "model_id": ...}
    patient_profile: dict                # {full_name, gender, age}
    intent:          str                 # результат supervisor
    tool_params:     dict                # параметры запроса (даты, аналит и др.)
    retrieved_data:  dict                # данные из БД для агентов
```

---

### 3. Узлы графа

#### `load_profile`

Загружает демографию пациента из PostgreSQL (`users`): имя, пол, возраст.
Передаётся всем агентам как `patient_profile`.

---

#### `supervisor` — `agents/supervisor.py`

Единственный узел, который **классифицирует намерение** пользователя.

**Вход:** последнее сообщение пользователя  
**Выход:** `intent` + `tool_params` (JSON)

Возможные intent-ы:

| Intent                 | Когда используется                                           |
|------------------------|--------------------------------------------------------------|
| `lab_analysis`         | Вопросы про анализы, результаты, лабораторные показатели    |
| `health_trends`        | Динамика показателя во времени («как менялся гемоглобин»)   |
| `health_history`       | Болезни, диагнозы, посещения врача                          |
| `doctor_recommendation`| Рекомендация специалиста                                    |
| `general_qa`           | Общий медицинский вопрос, вопросы о дате/времени, приветствия|

Извлекаемые `tool_params`:
- `analyte_name` — название аналита (например, «гемоглобин»)
- `date_from` / `date_to` — период в формате ISO `YYYY-MM-DD`
- `specialty` — специальность врача

**Маршрутизация после supervisor:**
- `general_qa` → напрямую в агент `general_qa` (без обращения к БД)
- всё остальное → `data_retrieval`

---

#### `data_retrieval` — `graph.py`

Выбирает источники данных в зависимости от intent и загружает их из БД.

| Intent                  | Источники данных                                                      |
|-------------------------|-----------------------------------------------------------------------|
| `lab_analysis`          | lab_results + analyte_standards (референсные значения)               |
| `health_trends`         | lab_results + analyte_standards                                       |
| `health_history`        | doctor_visits + lab_results + studies + interpretations              |
| `doctor_recommendation` | lab_results + doctor_visits + interpretations + health_events + studies|

**Функции извлечения данных:**

| Функция                    | Источник                          | Фильтры                        |
|----------------------------|-----------------------------------|--------------------------------|
| `_fetch_lab_results`       | PostgreSQL `documents` + MongoDB  | user_id, date_from/to, analyte |
| `_fetch_doctor_visits`     | PostgreSQL `documents` + MongoDB  | user_id, date_from/to          |
| `_fetch_studies`           | PostgreSQL `documents` + MongoDB  | user_id, date_from/to          |
| `_fetch_interpretations`   | PostgreSQL `interpretations`      | user_id                        |
| `_fetch_health_events`     | PostgreSQL `health_events` + MongoDB | user_id, date_from/to       |
| `_fetch_analyte_standard`  | PostgreSQL `analyte_standards`    | canonical_name / синонимы, пол |

> Запросы к PostgreSQL возвращают ID документов, по которым из MongoDB подтягиваются
> извлечённые данные (`extracted_data`, `classification` и т.д.).

---

#### `lab_analysis` — `agents/lab_analysis.py`

Интерпретирует лабораторные анализы пациента.

- Опирается на `retrieved_data.lab_results` и `retrieved_data.analyte_standards`
- Для `health_trends` акцент на динамику показателей во времени
- Всегда добавляет дисклеймер: *«Это не медицинский диагноз»*

---

#### `health_history` — `agents/health_history.py`

Составляет обзор истории болезни.

- Использует посещения врачей, анализы, исследования, интерпретации
- Структурирует хронологически или по системам организма
- Выделяет хронические состояния и повторяющиеся проблемы

---

#### `recommendation` — `agents/recommendation.py`

Рекомендует специалистов на основе данных пациента.

- Объясняет, почему рекомендован конкретный специалист
- Ранжирует по приоритету, указывает срочность
- Использует полный набор данных: анализы, визиты, исследования, health_events

---

#### `general_qa` — `agents/general_qa.py`

Отвечает на общие вопросы без обращения к данным пациента.

- Текущая дата подставляется динамически в system prompt
- Передаёт последние 10 сообщений диалога как контекст
- Обрабатывает: медицинские термины, общие вопросы, дату/время, приветствия

---

### 4. LLM-фабрика — `llm_factory.py`

**Файл:** `backend/app/services/assistant/llm_factory.py`

Поддерживаемые провайдеры:

| Провайдер    | Модели                                                    | Настройка               |
|--------------|-----------------------------------------------------------|-------------------------|
| `anthropic`  | claude-sonnet-4-6, claude-opus-4-6, claude-haiku-4-5      | `ANTHROPIC_API_KEY`     |
| `openrouter` | google/gemini-2.5-flash (и любые другие через OpenRouter) | `OPENROUTER_API_KEY`    |

Провайдер и модель по умолчанию задаются в `.env.local`:
```
ASSISTANT_PROVIDER=openrouter
ASSISTANT_MODEL=google/gemini-2.5-flash
```

Клиент может переопределить модель в каждом сообщении через поле `model` в WebSocket-пакете.

---

## База данных

### PostgreSQL — структурированные данные

| Таблица              | Назначение                                             |
|----------------------|--------------------------------------------------------|
| `users`              | Профиль пользователя (имя, пол, дата рождения)        |
| `documents`          | Метаданные документов (тип, дата, статус, mongodb_id) |
| `interpretations`    | AI-интерпретации анализов                              |
| `analyte_standards`  | Референсные значения аналитов                          |
| `analyte_synonyms`   | Синонимы названий аналитов                             |
| `health_events`      | Дневник самочувствия пользователя                      |
| `chat_sessions`      | Сессии диалога с ассистентом                           |
| `chat_messages`      | Сообщения диалога (role, content, metadata)            |

### MongoDB — неструктурированные данные

| Коллекция             | Назначение                                                  |
|-----------------------|-------------------------------------------------------------|
| `document_metadata`   | Полные извлечённые данные документов (`extracted_data`, `classification`) |

---

## Хранение диалогов

Каждый диалог привязан к `ChatSession`. При каждом обращении:
1. Загружаются последние 20 сообщений из `chat_messages`
2. Они передаются в граф как начальное состояние `messages`
3. После получения ответа оба сообщения (user + assistant) сохраняются в БД
4. В метаданных сообщения ассистента фиксируются `intent`, `model_provider`, `model_id`

---

## Конфигурация

Ключевые настройки в `backend/app/core/config.py` (задаются через `.env.local`):

| Переменная                      | По умолчанию          | Описание                                  |
|---------------------------------|-----------------------|-------------------------------------------|
| `ASSISTANT_PROVIDER`            | `anthropic`           | Провайдер LLM                             |
| `ASSISTANT_MODEL`               | `claude-sonnet-4-6`   | Модель по умолчанию                       |
| `CHAT_HISTORY_LIMIT`            | `20`                  | Кол-во сообщений из истории в контексте   |
| `ASSISTANT_LAB_RESULTS_LIMIT`   | `200`                 | Макс. документов результатов анализов     |
| `ASSISTANT_DOCTOR_VISITS_LIMIT` | `100`                 | Макс. документов посещений врача          |
| `ASSISTANT_STUDIES_LIMIT`       | `100`                 | Макс. инструментальных исследований       |
| `ASSISTANT_INTERPRETATIONS_LIMIT` | `20`               | Макс. прошлых интерпретаций               |
| `ASSISTANT_HEALTH_EVENTS_LIMIT` | `100`                 | Макс. событий самочувствия                |

---

## Известные ограничения

1. **Маршрутизация чувствительна к контексту** — supervisor смотрит только на последнее сообщение, но LLM видит историю диалога, что иногда приводит к неверной классификации intent.
2. **health_history возвращает весь объём данных** — вопрос «сколько раз я делал ЭКГ?» вызывает полный обзор истории болезни вместо конкретного ответа.
3. **asyncpg не принимает строки как даты** — даты из supervisor должны быть конвертированы в `datetime.date` перед передачей в SQL-запросы (решено через `_parse_date`).
4. **Стриминг зависит от провайдера** — если LLM не генерирует `on_chat_model_stream` события, используется fallback через `on_chain_end`.

# MedHistory API Documentation

**Версия:** 1.0.0  
**Базовый URL:** `/api/v1`

## Содержание

- [Обзор](#обзор)
- [Аутентификация](#аутентификация)
- [Эндпоинты](#эндпоинты)
  - [Authentication](#authentication)
  - [Documents](#documents)
  - [Interpretations](#interpretations)
  - [Reports](#reports)
  - [Timeline](#timeline)
- [Модели данных](#модели-данных)
- [Коды ошибок](#коды-ошибок)
- [Технологический стек](#технологический-стек)

---

## Обзор

MedHistory API — это RESTful API для управления персональной медицинской историей. Система позволяет:

- 📤 Загружать медицинские документы (PDF, изображения, DOCX)
- 🤖 Автоматически классифицировать и извлекать данные с помощью AI
- 📊 Анализировать лабораторные показатели в динамике
- 📝 Генерировать AI-интерпретации медицинских данных
- 📑 Создавать PDF отчёты
- 📅 Просматривать медицинскую историю в формате timeline

### Архитектура хранения данных

- **PostgreSQL**: Основные метаданные документов, пользователи, отчёты
- **MongoDB**: Расширенные метаданные, результаты AI-анализа, лабораторные данные
- **MinIO**: Хранение файлов документов

---

## Аутентификация

API использует JWT (JSON Web Tokens) для аутентификации.

### Получение токена

```http
POST /api/v1/auth/login
```

После успешной аутентификации токен необходимо включать в заголовок всех защищённых запросов:

```http
Authorization: Bearer <access_token>
```

### Время жизни токена

Токен действителен в течение 24 часов (1440 минут).

---

## Эндпоинты

## Authentication

### POST /auth/register

Регистрация нового пользователя.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "Иван Иванов"
}
```

**Response:** `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "full_name": "Иван Иванов",
  "is_active": true,
  "created_at": "2025-10-28T10:30:00Z"
}
```

**Ошибки:**
- `400` - Email уже зарегистрирован

---

### POST /auth/login

Вход в систему и получение access token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Ошибки:**
- `401` - Неверный email или пароль
- `403` - Учётная запись неактивна

---

### GET /auth/me

Получить информацию о текущем пользователе.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "full_name": "Иван Иванов",
  "is_active": true,
  "created_at": "2025-10-28T10:30:00Z"
}
```

---

## Documents

### POST /documents/upload

Загрузить новый медицинский документ.

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**Request Body:**
```
file: <binary> (PDF, JPG, JPEG, PNG, DOCX)
```

**Ограничения:**
- Максимальный размер файла: 20 МБ
- Поддерживаемые форматы: `.pdf`, `.jpg`, `.jpeg`, `.png`, `.docx`

**Response:** `201 Created`
```json
{
  "document_id": "750e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Документ успешно загружен и обрабатывается"
}
```

**Процесс обработки:**
1. Файл загружается в MinIO
2. AI анализирует документ и извлекает метаданные
3. Данные сохраняются в PostgreSQL и MongoDB
4. Статус обработки обновляется: `pending` → `processing` → `completed`/`failed`

**Ошибки:**
- `400` - Неподдерживаемый формат файла или превышен размер
- `500` - Ошибка при загрузке

---

### GET /documents/

Получить список документов пользователя с фильтрацией.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `skip` | int | Количество записей для пропуска (default: 0) |
| `limit` | int | Максимум записей (default: 100, max: 10000) |
| `document_type` | string[] | Фильтр по типу документа |
| `patient_name` | string[] | Фильтр по имени пациента |
| `medical_facility` | string[] | Фильтр по медицинскому учреждению |
| `date_from` | string | Фильтр по дате документа (от) ISO format |
| `date_to` | string | Фильтр по дате документа (до) ISO format |
| `created_from` | string | Фильтр по дате загрузки (от) ISO format |
| `created_to` | string | Фильтр по дате загрузки (до) ISO format |
| `sort_by` | string | Сортировка: `document_date` или `created_at` |
| `specialties` | string[] | Фильтр по специальности (MongoDB) |
| `document_subtype` | string[] | Фильтр по подтипу документа (MongoDB) |
| `research_area` | string[] | Фильтр по области исследования (MongoDB) |

**Типы документов:**
- `Прием врача`
- `Результаты анализа`
- `Инструментальное исследование`
- `Функциональная диагностика`
- `Другое`

**Response:** `200 OK`
```json
[
  {
    "id": "750e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "original_filename": "Анализ_крови_2024.pdf",
    "file_size": 1024567,
    "file_type": "pdf",
    "file_url": "documents/550e8400.../750e8400...pdf",
    "document_type": "Результаты анализа",
    "document_date": "2024-10-15",
    "patient_name": "Иван Иванов",
    "medical_facility": "Городская поликлиника №1",
    "processing_status": "completed",
    "mongodb_metadata_id": "671234567890abcdef123456",
    "created_at": "2024-10-20T14:30:00Z",
    "updated_at": "2024-10-20T14:35:00Z",
    "specialty": "Терапия",
    "document_subtype": "Общий анализ крови",
    "research_area": null,
    "summary": "Общий анализ крови в пределах нормы"
  }
]
```

---

### GET /documents/count/total

Получить общее количество документов с фильтрацией.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:** (те же, что и в `/documents/`)

**Response:** `200 OK`
```json
{
  "total": 42
}
```

---

### GET /documents/{document_id}

Получить документ по ID с метаданными из MongoDB.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK` (`DocumentWithMetadata`)
```json
{
  "id": "750e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "original_filename": "Анализ_крови_2024.pdf",
  "file_size": 1024567,
  "file_type": "pdf",
  "file_url": "documents/550e8400.../750e8400...pdf",
  "document_type": "Результаты анализа",
  "document_date": "2024-10-15",
  "patient_name": "Иван Иванов",
  "medical_facility": "Городская поликлиника №1",
  "processing_status": "completed",
  "mongodb_metadata_id": "671234567890abcdef123456",
  "created_at": "2024-10-20T14:30:00Z",
  "updated_at": "2024-10-20T14:35:00Z",
  "specialty": "Терапия",
  "document_subtype": "Общий анализ крови",
  "research_area": null,
  "summary": "Общий анализ крови от 15.10.2024. Все показатели в пределах референсных значений. Гемоглобин 145 г/л, эритроциты 4.8×10¹²/л, лейкоциты 6.2×10⁹/л."
}
```

**Дополнительные поля из MongoDB:**
- `specialty` - специальность врача (для "Прием врача")
- `document_subtype` - подтип документа
- `research_area` - область исследования (для "Инструментальное исследование")
- `summary` - краткое содержание документа, сгенерированное AI

**Ошибки:**
- `404` - Документ не найден

---

### GET /documents/{document_id}/file

Скачать файл документа.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```
Content-Type: application/pdf (или image/jpeg, image/png, etc.)
Content-Disposition: attachment; filename*=UTF-8''<filename>

<binary file content>
```

**Ошибки:**
- `404` - Документ не найден
- `500` - Ошибка при скачивании файла

---

### DELETE /documents/{document_id}

Удалить документ.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `204 No Content`

**Ошибки:**
- `404` - Документ не найден

---

### GET /documents/{document_id}/labs

Получить извлечённые лабораторные результаты из документа.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "document_id": "750e8400-e29b-41d4-a716-446655440000",
  "lab_results": [
    {
      "test_name": "Гемоглобин",
      "value": "145",
      "unit": "г/л",
      "reference_range": "130-160",
      "flag": "normal"
    },
    {
      "test_name": "Лейкоциты",
      "value": "6.5",
      "unit": "×10⁹/л",
      "reference_range": "4.0-9.0",
      "flag": "normal"
    }
  ]
}
```

**Ошибки:**
- `404` - Документ не найден

---

### GET /documents/{document_id}/labs/summary

Получить краткую информацию о наличии лабораторных данных.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "document_id": "750e8400-e29b-41d4-a716-446655440000",
  "has_labs": true,
  "count": 12
}
```

---

### GET /documents/labs/analytes

Получить список всех уникальных названий анализов в документах пользователя.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "analytes": [
    {
      "name": "Гемоглобин",
      "count": 15
    },
    {
      "name": "Лейкоциты",
      "count": 14
    },
    {
      "name": "Глюкоза",
      "count": 10
    }
  ]
}
```

---

### GET /documents/labs/timeseries

Получить временной ряд для конкретного анализа.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `analyte` | string | Да | Название анализа (например, "Гемоглобин") |

**Response:** `200 OK`
```json
{
  "analyte": "Гемоглобин",
  "points": [
    {
      "document_id": "750e8400-e29b-41d4-a716-446655440000",
      "date": "2024-01-15",
      "value": "145",
      "value_num": 145.0,
      "unit": "г/л",
      "reference_range": "130-160",
      "flag": "normal"
    },
    {
      "document_id": "850e8400-e29b-41d4-a716-446655440001",
      "date": "2024-06-20",
      "value": "142",
      "value_num": 142.0,
      "unit": "г/л",
      "reference_range": "130-160",
      "flag": "normal"
    }
  ]
}
```

---

### GET /documents/filters/values

Получить уникальные значения для фильтров с автодополнением.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `field` | string | Да | Поле для фильтрации |
| `q` | string | Нет | Поисковый запрос для фильтрации значений |
| `limit` | int | Нет | Максимум значений (default: 50, max: 100) |

**Поддерживаемые поля:**
- `document_type` (PostgreSQL)
- `patient_name` (PostgreSQL)
- `medical_facility` (PostgreSQL)
- `specialties` (MongoDB)
- `document_subtype` (MongoDB)
- `research_area` (MongoDB)

**Response:** `200 OK`
```json
{
  "field": "medical_facility",
  "values": [
    "Городская поликлиника №1",
    "Областная больница",
    "Частная клиника 'Здоровье'"
  ]
}
```

**Ошибки:**
- `400` - Неверное название поля

---

## Interpretations

AI-интерпретации медицинских документов.

### POST /interpretations/

Создать новую AI-интерпретацию для выбранных документов.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "document_ids": [
    "750e8400-e29b-41d4-a716-446655440000",
    "850e8400-e29b-41d4-a716-446655440001"
  ]
}
```

**Требования:**
- Минимум 1 документ

**Response:** `201 Created`
```json
{
  "id": "950e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "interpretation_text": null,
  "error_message": null,
  "created_at": "2024-10-28T15:30:00Z",
  "updated_at": "2024-10-28T15:30:00Z",
  "completed_at": null,
  "documents": [
    {
      "id": "750e8400-e29b-41d4-a716-446655440000",
      "original_filename": "Анализ_крови_2024.pdf",
      "document_date": "2024-10-15T00:00:00Z",
      "document_type": "Результаты анализа",
      "document_subtype": null
    }
  ]
}
```

**Статусы обработки:**
- `pending` - Ожидает обработки
- `processing` - Обрабатывается
- `completed` - Успешно завершено
- `failed` - Ошибка обработки

**Ошибки:**
- `400` - Неверные данные запроса
- `500` - Ошибка при создании интерпретации

---

### GET /interpretations/

Получить список всех интерпретаций пользователя.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `skip` | int | Количество записей для пропуска (default: 0) |
| `limit` | int | Максимум записей (default: 100) |

**Response:** `200 OK`
```json
{
  "total": 5,
  "items": [
    {
      "id": "950e8400-e29b-41d4-a716-446655440000",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "interpretation_text": "На основе анализа представленных документов можно сделать следующие выводы:\n\n1. Показатели крови в норме...",
      "error_message": null,
      "created_at": "2024-10-28T15:30:00Z",
      "updated_at": "2024-10-28T15:32:00Z",
      "completed_at": "2024-10-28T15:32:00Z",
      "documents": [
        {
          "id": "750e8400-e29b-41d4-a716-446655440000",
          "original_filename": "Анализ_крови_2024.pdf",
          "document_date": "2024-10-15T00:00:00Z",
          "document_type": "Результаты анализа",
          "document_subtype": null
        }
      ]
    }
  ]
}
```

---

### GET /interpretations/{interpretation_id}

Получить конкретную интерпретацию по ID.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "id": "950e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "interpretation_text": "Подробная медицинская интерпретация...",
  "error_message": null,
  "created_at": "2024-10-28T15:30:00Z",
  "updated_at": "2024-10-28T15:32:00Z",
  "completed_at": "2024-10-28T15:32:00Z",
  "documents": [...]
}
```

**Ошибки:**
- `404` - Интерпретация не найдена

---

### DELETE /interpretations/{interpretation_id}

Удалить интерпретацию.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `204 No Content`

**Ошибки:**
- `404` - Интерпретация не найдена

---

## Reports

Генерация PDF отчётов.

### POST /reports/generate

Сгенерировать PDF отчёт на основе фильтров.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "filters": {
    "document_type": "Результаты анализа",
    "patient_name": "Иван Иванов",
    "date_from": "2024-01-01",
    "date_to": "2024-12-31",
    "medical_facility": "Городская поликлиника №1"
  }
}
```

**Response:** `200 OK`
```json
{
  "report_id": "a50e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "message": "Отчёт успешно сгенерирован"
}
```

**Ошибки:**
- `400` - Неверные параметры фильтрации
- `500` - Ошибка при генерации отчёта

---

### GET /reports/

Получить список отчётов пользователя.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `skip` | int | Количество записей для пропуска (default: 0) |
| `limit` | int | Максимум записей (default: 50) |

**Response:** `200 OK`
```json
[
  {
    "id": "a50e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "file_url": "reports/550e8400.../a50e8400...pdf",
    "filters": {
      "document_type": "Результаты анализа",
      "date_from": "2024-01-01",
      "date_to": "2024-12-31"
    },
    "created_at": "2024-10-28T16:00:00Z"
  }
]
```

---

### GET /reports/{report_id}

Получить метаданные отчёта.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "id": "a50e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_url": "reports/550e8400.../a50e8400...pdf",
  "filters": {...},
  "created_at": "2024-10-28T16:00:00Z"
}
```

**Ошибки:**
- `404` - Отчёт не найден

---

### GET /reports/{report_id}/download

Скачать PDF отчёт.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```
Content-Type: application/pdf
Content-Disposition: attachment; filename=medical_report_<report_id>.pdf

<binary PDF content>
```

**Ошибки:**
- `404` - Отчёт не найден
- `500` - Ошибка при скачивании

---

## Timeline

Временная шкала медицинских событий.

### GET /timeline/

Получить события timeline с фильтрацией.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `document_type` | string | Фильтр по типу документа |
| `specialty` | string | Фильтр по специальности |
| `patient_name` | string | Фильтр по имени пациента |
| `medical_facility` | string | Фильтр по медицинскому учреждению |
| `date_from` | string | Фильтр по дате (от) ISO format |
| `date_to` | string | Фильтр по дате (до) ISO format |

**Response:** `200 OK`
```json
{
  "total_count": 15,
  "date_range": {
    "start": "2024-01-15",
    "end": "2024-10-28"
  },
  "events": [
    {
      "document_id": "750e8400-e29b-41d4-a716-446655440000",
      "date": "2024-10-28",
      "document_type": "Результаты анализа",
      "document_subtype": "Общий анализ крови",
      "specialty": "Терапия",
      "title": "Результаты анализа - Терапия",
      "medical_facility": "Городская поликлиника №1",
      "icon": "test-tube",
      "color": "#EF4444",
      "file_url": "documents/550e8400.../750e8400...pdf",
      "original_filename": "Анализ_крови_2024.pdf",
      "summary": "Общий анализ крови в пределах нормы"
    }
  ]
}
```

**Иконки событий:**
- `doctor` - Прием врача
- `test-tube` - Результаты анализа
- `scan` - Инструментальное исследование
- `activity` - Функциональная диагностика
- `document` - Другое

---

### GET /timeline/stats

Получить статистику по timeline.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "total_documents": 42,
  "by_type": {
    "Результаты анализа": 15,
    "Прием врача": 12,
    "Инструментальное исследование": 8,
    "Функциональная диагностика": 5,
    "Другое": 2
  },
  "by_specialty": {
    "Терапия": 10,
    "Кардиология": 5,
    "Неврология": 3
  },
  "by_facility": {
    "Городская поликлиника №1": 20,
    "Областная больница": 15,
    "Частная клиника 'Здоровье'": 7
  }
}
```

---

### GET /timeline/suggestions

Получить предложения для автодополнения фильтров.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `field` | string | Да | Поле: `document_type`, `patient_name`, `medical_facility` |
| `q` | string | Нет | Поисковая подстрока |
| `limit` | int | Нет | Максимум значений (default: 20, max: 100) |

**Response:** `200 OK`
```json
{
  "values": [
    "Городская поликлиника №1",
    "Городская больница №2"
  ]
}
```

---

## Модели данных

### User

```typescript
{
  id: UUID
  email: string
  full_name?: string
  is_active: boolean
  created_at: datetime
}
```

### Document

```typescript
{
  id: UUID
  user_id: UUID
  original_filename: string
  file_size: number
  file_type: string
  file_url: string
  document_type?: string
  document_date?: date
  patient_name?: string
  medical_facility?: string
  processing_status: string  // pending, processing, completed, failed
  mongodb_metadata_id?: string
  created_at: datetime
  updated_at: datetime
}
```

### DocumentWithMetadata

Расширяет `Document` дополнительными полями из MongoDB:

```typescript
{
  ...Document,
  specialty?: string
  document_subtype?: string
  research_area?: string
  summary?: string
}
```

### MongoDB Document Metadata

```json
{
  "_id": "ObjectId",
  "document_id": "UUID",
  "user_id": "UUID",
  "classification": {
    "document_type": "string",
    "document_subtype": "string",
    "specialties": ["string"],
    "research_area": "string",
    "document_language": "string",
    "confidence": 0.95
  },
  "extracted_data": {
    "summary": "string",
    "lab_results": [
      {
        "test_name": "string",
        "value": "string",
        "unit": "string",
        "reference_range": "string",
        "flag": "normal | high | low"
      }
    ]
  },
  "raw_text": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Interpretation

```typescript
{
  id: UUID
  user_id: UUID
  status: string  // pending, processing, completed, failed
  interpretation_text?: string
  error_message?: string
  created_at: datetime
  updated_at: datetime
  completed_at?: datetime
  documents: InterpretationDocumentInfo[]
}
```

### Report

```typescript
{
  id: UUID
  user_id: UUID
  file_url: string
  filters: {
    document_type?: string
    patient_name?: string
    date_from?: date
    date_to?: date
    medical_facility?: string
  }
  created_at: datetime
}
```

### TimelineEvent

```typescript
{
  document_id: UUID
  date?: date
  document_type?: string
  document_subtype?: string
  specialty?: string
  title: string
  medical_facility?: string
  icon: string
  color: string
  file_url?: string
  original_filename?: string
  summary?: string
}
```

---

## Коды ошибок

| Код | Описание |
|-----|----------|
| `200` | OK - Запрос успешно выполнен |
| `201` | Created - Ресурс успешно создан |
| `204` | No Content - Успешное выполнение без возврата данных |
| `400` | Bad Request - Неверные параметры запроса |
| `401` | Unauthorized - Требуется аутентификация |
| `403` | Forbidden - Доступ запрещён |
| `404` | Not Found - Ресурс не найден |
| `500` | Internal Server Error - Внутренняя ошибка сервера |

### Формат ошибки

```json
{
  "detail": "Описание ошибки"
}
```

---

## Технологический стек

### Backend Framework
- **FastAPI** - Современный веб-фреймворк для Python
- **Python 3.11+**

### Базы данных
- **PostgreSQL** - Реляционная БД для основных данных
- **MongoDB** - NoSQL БД для расширенных метаданных и AI-результатов
- **MinIO** - S3-совместимое хранилище файлов

### AI/ML
- **OpenRouter API** - Интеграция с Claude 3.5 Sonnet для:
  - Классификации документов
  - Извлечения метаданных
  - Извлечения лабораторных данных
  - Генерации интерпретаций

### Безопасность
- **JWT** - Аутентификация с токенами
- **bcrypt** - Хеширование паролей

### Дополнительные библиотеки
- **SQLAlchemy** - ORM для PostgreSQL
- **Motor** - Асинхронный драйвер для MongoDB
- **Pydantic** - Валидация данных
- **Pillow** - Обработка изображений
- **python-multipart** - Загрузка файлов

---

## Примеры использования

### Базовый workflow

1. **Регистрация и аутентификация**
```bash
# Регистрация
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123", "full_name": "Иван Иванов"}'

# Вход
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'
```

2. **Загрузка документа**
```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@analysis.pdf"
```

3. **Получение списка документов**
```bash
curl -X GET "http://localhost:8000/api/v1/documents/?limit=10&document_type=Результаты%20анализа" \
  -H "Authorization: Bearer <token>"
```

4. **Создание интерпретации**
```bash
curl -X POST http://localhost:8000/api/v1/interpretations/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"document_ids": ["750e8400-e29b-41d4-a716-446655440000"]}'
```

---

## Контакты и поддержка

Для вопросов и предложений по API обращайтесь к команде разработки проекта MedHistory.

**Версия документации:** 1.2.0  
**Дата обновления:** 28 октября 2025  
**Изменения:**
- Endpoint `GET /documents/{document_id}` теперь возвращает `DocumentWithMetadata` с полями из MongoDB (`specialty`, `document_subtype`, `research_area`, `summary`)
- Добавлено описание поля `summary` - AI-генерированное краткое содержание документа


# Структура лендинг страницы — Landing.tsx

## Обзор

Единый файл [`frontend/src/pages/Landing.tsx`](../frontend/src/pages/Landing.tsx) (~345 строк).  
Внешние компоненты: только `GraphVisualization` из [`frontend/src/components/Landing/`](../frontend/src/components/Landing/).

---

## Иерархия разделов

```
<div> — корневой контейнер (min-h-screen, bg-white)
│
├── 1. Hero — секция заголовка
├── 2. Bento Grid — блок возможностей
├── 4. Testimonials — отзывы
├── 5. How it Works — как работает
├── 6. CTA — финальный призыв к действию
└── 7. Footer — подвал
```

---

## 1. Hero

**Позиция:** строки 19–49  
**Фон:** белый  
**Структура:**

```
<section>
├── Badge — метка "Новое" + текст про AI-ассистент
├── <h1> — главный заголовок с акцентом (emerald-500)
├── <p> — подзаголовок-подпись
└── CTA Button — кнопка "Попробовать" → /register
```

**Ключевые детали:**
- Бейдж: pill с зелёным тегом «Новое» + иконка ChevronRight
- H1: «Умное управление **медицинской историей**» (акцент — emerald)
- Кнопка: emerald, округлённая (rounded-full), ссылка на `/register`

---

## 2. Bento Grid — Возможности

**Позиция:** строки 52–190  
**Фон:** bg-gray-50  
**Раскладка:** `grid cols-1 / sm:cols-2 / lg:cols-3`, gap-4/5

**Порядок отображения на lg (3-col grid):**
```
Row 1: [Умная обработка: 1/3] [Динамика показателей: 2/3]
Row 2: [Семейные профили: 1/3] [Отчёт для врача: 1/3] [Данные под защитой: 1/3]
```
Реализовано через CSS `order` утилиты Tailwind + `lg:col-span-2` на карточке Динамики.

```
<section> (bg-gray-50)
└── Grid (5 карточек)
    ├── [1] Card "Умная обработка медицинских документов" (col-1, lg:order-1)
    ├── [2] Card "Динамика показателей" (sm:col-span-2 lg:col-span-2, lg:order-2)
    ├── [3] Card "Семейные профили" (col-1, lg:order-3)
    ├── [4] Card "Отчёт для врача" (sm:col-span-2 lg:col-span-1, lg:order-4)
    └── [5] Card "Данные под защитой" (col-1, lg:order-5)
```

### 2.1 Карточка — «Умная обработка медицинских документов»

Иконка: `FileSearch` (emerald)

```
Header: иконка + заголовок
Body: описание текстом
Footer (mt-auto):
├── Input formats row
│   ├── PDF pill (red-50)
│   ├── Фото pill (blue-50)
│   ├── Скан pill (purple-50)
│   ├── ChevronRight
│   └── AI-иконка Zap (emerald bg)
└── Extracted result block (gray-50)
    ├── Статус строка (CheckCircle2 + "Анализ крови.pdf — распознан")
    └── 2×2 grid с полями: Тип / Дата / Гемоглобин / Показателей
```

### 2.2 Карточка — «Семейные профили»

```
Header: заголовок + описание
Footer (mt-auto):
└── list (familyMembers[])
    ├── Row "Мама" (rose, UserRound icon, 23 docs)
    ├── Row "Папа" (blue, User2 icon, 15 docs)
    └── Row "Ребёнок" (amber, Baby icon, 8 docs)
```

Данные вынесены в константу `familyMembers[]` (строки 9–13).

### 2.3 Карточка — «Динамика показателей» (2/3 ширины на lg)

Иконка: `BarChart3` (emerald)

```
Header: иконка + заголовок
Body: описание
Footer (mt-auto):
└── <GraphVisualization />
```

### 2.4 Карточка — «Отчёт для врача»

`sm:col-span-2`, flex-row на sm+

```
Left block (flex-1):
├── Заголовок
├── Описание
└── Кнопки: "Попробовать" → /register | "Подробнее" → /login

Right block (w-[300px], серый фон):
└── list документов (3 элемента с иконками FileCheck)
    ├── Анализ крови — 12.03.2024
    ├── ЭКГ — 15.01.2024
    └── УЗИ — 08.11.2023
```

### 2.5 Карточка — «Данные под защитой»

```
Центрированный layout:
├── Иконка Shield (emerald-50 bg)
├── Заголовок
└── Текст описания
```

---

## 4. Testimonials — Отзывы

**Позиция:** строки 218–246  
**Фон:** белый  
**Раскладка:** `grid cols-1 / sm:cols-2 / lg:cols-3`

```
<section>
├── Заголовок секции
├── Подзаголовок
└── Grid (3 карточки, данные inline в .map())
    ├── Review Card (Анна М.)
    ├── Review Card (Дмитрий К.)
    └── Review Card (Елена С.)

    Структура каждой карточки:
    ├── Текст цитаты
    └── Автор (avatar placeholder (div) + имя + роль)
```

---

## 5. How it Works — Как это работает

**Позиция:** строки 249–274  
**Фон:** bg-gray-50  
**Раскладка:** `grid cols-1 / sm:cols-3`

```
<section> (bg-gray-50)
├── Заголовок секции
├── Подзаголовок
└── Grid (3 шага, данные inline в .map())
    ├── Step "01 — Загрузите документы"
    ├── Step "02 — Автоматическая обработка"
    └── Step "03 — AI-рекомендации"

    Структура каждого шага:
    ├── Номер (круглый emerald badge)
    ├── Заголовок
    └── Описание
```

---

## 6. CTA — Финальный призыв

**Позиция:** строки 277–304  
**Фон:** белый (внешний), `bg-gray-900` (блок)  
**Раскладка:** flex col → lg:flex-row

```
<section>
└── CTA Block (bg-gray-900, rounded-3xl)
    ├── Left (flex-1):
    │   ├── Заголовок (белый текст)
    │   ├── "Создать аккаунт" → /register (emerald)
    │   └── "Войти" → /login (border gray)
    └── Right (hidden → lg:flex):
        └── Placeholder (bg-gray-800) с иконкой Bot
```

---

## 7. Footer — Подвал

**Позиция:** строки 307–340  
**Раскладка:** `grid cols-2 / sm:cols-4`

```
<footer>
└── Grid (4 колонки)
    ├── Brand col (col-span-2 / sm:col-span-1)
    │   ├── Logo (HeartPulse + "MedHistory")
    │   └── Описание
    ├── "Продукт" — Возможности / Тарифы / Обновления
    ├── "Ресурсы" — Документация / Блог / FAQ
    └── "Компания" — О нас / Контакты / Конфиденциальность
└── Bottom bar
    └── Copyright "© 2024 MedHistory"
```

Данные колонок вынесены в inline `.map()` (строки 319–334).

---

## Дочерние компоненты

| Компонент | Файл | Используется |
|---|---|---|
| `GraphVisualization` | `components/Landing/GraphVisualization.tsx` | Dashboard Mockup (§2), Карточка §3.3 |
| `TimelineVisualization` | `components/Landing/TimelineVisualization.tsx` | **Не используется** в текущей версии |

### GraphVisualization

Recharts-график динамики гемоглобина (янв–июн).

```
<div>
├── Header row
│   ├── Заголовок "Динамика гемоглобина"
│   └── Легенда (зелёный кружок + пунктир)
├── <ResponsiveContainer height=220>
│   └── <LineChart data=hemoglobinData>
│       ├── CartesianGrid (горизонтальные линии, gray-100)
│       ├── XAxis (даты)
│       ├── YAxis (100–170)
│       ├── ReferenceLine y=120 (норма мин, пунктир)
│       ├── ReferenceLine y=160 (норма макс, пунктир)
│       ├── Tooltip (белый, rounded)
│       └── Line (emerald, monotone)
└── Footer note (emerald-50 bg) — текстовый вывод тренда
```

Данные хардкодены в константе `hemoglobinData[]` (строки 3–10).

---

## Цветовая система

| Роль | Цвет |
|---|---|
| Акцент / CTA | `emerald-500` (#10b981) |
| Hover CTA | `emerald-600` |
| Фон секций (чётные) | `bg-gray-50` |
| Фон секций (нечётные) | `bg-white` |
| Финальный CTA-блок | `bg-gray-900` |
| Текст основной | `text-gray-900` |
| Текст вторичный | `text-gray-500` |
| Границы карточек | `border-gray-200` / `border-gray-100` |

## Адаптивность

Брейкпоинты Tailwind:
- **base** (mobile): одна колонка, уменьшенные отступы и шрифты
- **sm** (≥640px): две колонки в гридах, полные отступы
- **lg** (≥1024px): три колонки, горизонтальный CTA-блок

Максимальная ширина контейнеров: `max-w-[1400px]`.

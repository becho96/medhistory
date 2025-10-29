# Дизайн-система медицинского сервиса
## UI/UX паттерны и рекомендации

> **Версия:** 1.0  
> **Дата:** Октябрь 2025  
> **Цель:** Создание эмоциональной привязанности пользователей через современный, приятный и функциональный дизайн

---

## 📋 Содержание

1. [Философия дизайна](#философия-дизайна)
2. [Цветовая система](#цветовая-система)
3. [Типографика](#типографика)
4. [Компонентная архитектура](#компонентная-архитектура)
5. [Паттерны визуализации данных](#паттерны-визуализации-данных)
6. [Микроинтерактивность](#микроинтерактивность)
7. [Адаптивность и респонсив](#адаптивность-и-респонсив)
8. [Специфика медицинского контекста](#специфика-медицинского-контекста)

---

## 🎨 Философия дизайна

### Ключевые принципы

**Человечность превыше технологий**
- Дизайн должен снижать стресс, связанный с медицинскими вопросами
- Использование мягких форм, успокаивающих цветов
- Эмпатичные микротексты и поддерживающие сообщения

**Clarity through Simplicity**
- Медицинская информация должна быть понятной без упрощения
- Визуальная иерархия помогает быстро находить критичную информацию
- Прогрессивное раскрытие сложности (progressive disclosure)

**Доверие через прозрачность**
- Четкая визуализация статусов и процессов
- Понятная обратная связь на каждое действие
- Объяснение, почему запрашиваются те или иные данные

---

## 🌈 Цветовая система

### Основная палитра

```
Primary Colors (Основные)
├─ Medical Blue #4A90E2      // Основной акцент, доверие
├─ Soft Lavender #E8E4F3     // Фоны карточек, нейтральность
└─ Clean White #FFFFFF        // Базовый фон, чистота

Secondary Colors (Вспомогательные)
├─ Healing Green #7ED957     // Успех, положительная динамика
├─ Warm Peach #FFB4A2        // Важные уведомления, мягкие предупреждения
├─ Calm Mint #B8E6E0         // Дополнительные акценты
└─ Gentle Pink #FFE5F0       // Поддерживающие блоки

Data Visualization
├─ Graph Blue #6BA4FF        // Основные метрики
├─ Graph Purple #B794F6      // Дополнительные данные
├─ Graph Green #7ED957       // Позитивные тренды
└─ Graph Coral #FF9B9B       // Показатели, требующие внимания

Semantic Colors
├─ Success #34C759           // Успешные операции
├─ Warning #FFCC00           // Предупреждения
├─ Error #FF3B30             // Ошибки, критичные состояния
└─ Info #5AC8FA              // Информационные сообщения
```

### Принципы использования цвета

1. **Фон и контраст**
   - Минимальный контраст 4.5:1 для текста
   - Использование мягких градиентов для создания глубины
   - Белый фон для основного контента, цветные акценты для зонирования

2. **Эмоциональное кодирование**
   - Зеленый: выздоровление, положительная динамика
   - Синий: стабильность, профессионализм
   - Персиковый/розовый: эмпатия, забота
   - Избегать агрессивного красного для обычных состояний

3. **Градиенты**
   ```css
   /* Пример мягкого градиента для карточек */
   background: linear-gradient(135deg, #E8E4F3 0%, #F5F3FF 100%);
   
   /* Пример градиента для графиков */
   background: linear-gradient(180deg, #6BA4FF 0%, rgba(107, 164, 255, 0.1) 100%);
   ```

---

## ✍️ Типографика

### Шрифтовая система

**Основной шрифт:** Inter / SF Pro Display  
**Альтернатива:** Nunito Sans / Manrope

```
Иерархия размеров:

H1 - Hero Numbers
├─ Size: 48-64px
├─ Weight: 600-700
├─ Use: Основные метрики, ключевые показатели
└─ Example: "24,780.00" (месячный доход)

H2 - Section Headers
├─ Size: 32-40px
├─ Weight: 600
├─ Use: Заголовки секций, названия страниц
└─ Example: "Результаты анализов"

H3 - Card Titles
├─ Size: 20-24px
├─ Weight: 600
├─ Use: Заголовки карточек, подсекций
└─ Example: "AI Satisfaction Scan"

H4 - Subsection Titles
├─ Size: 16-18px
├─ Weight: 500-600
├─ Use: Подзаголовки, категории
└─ Example: "Tenant Acquisition Cost"

Body Large
├─ Size: 16px
├─ Weight: 400
├─ Line Height: 1.5
└─ Use: Основной текст, описания

Body Regular
├─ Size: 14px
├─ Weight: 400
├─ Line Height: 1.5
└─ Use: Вспомогательный текст, метаданные

Caption / Labels
├─ Size: 12-13px
├─ Weight: 400-500
├─ Color: #6B7280
└─ Use: Подписи, дополнительная информация
```

### Правила типографики

1. **Цифры и метрики**
   - Использовать tabular numbers для выравнивания
   - Крупный размер для ключевых показателей (48px+)
   - Добавлять символы валюты/единиц измерения меньшим размером

2. **Читабельность**
   - Максимальная ширина текстового блока: 65-75 символов
   - Межстрочный интервал: 1.5 для body текста
   - Достаточные отступы между параграфами (16px)

3. **Иерархия через вес**
   - Regular (400) - основной текст
   - Medium (500) - акценты, метки
   - Semibold (600) - заголовки, важная информация
   - Bold (700) - крупные метрики, критичные данные

---

## 🧩 Компонентная архитектура

### 1. Card-Based Layout (Карточная структура)

**Принцип:** Вся информация организована в модульные карточки с четким разделением контента

```
Анатомия карточки:
┌─────────────────────────────────────┐
│ Icon  Title              Actions    │  ← Header
├─────────────────────────────────────┤
│                                     │
│     Main Content Area               │  ← Content
│     (Charts, Stats, Lists)          │
│                                     │
├─────────────────────────────────────┤
│ Metadata / Secondary Info           │  ← Footer
└─────────────────────────────────────┘
```

**Спецификация карточки:**

```css
.medical-card {
  background: #FFFFFF;
  border-radius: 16-24px;
  padding: 20-32px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04), 
              0 1px 2px rgba(0, 0, 0, 0.06);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.medical-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08),
              0 2px 4px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.medical-card--colored-bg {
  background: linear-gradient(135deg, #E8E4F3 0%, #F5F3FF 100%);
}
```

**Типы карточек:**

1. **Metric Card (Карточка метрики)**
   - Крупное числовое значение
   - Иконка или индикатор
   - Микрографик тренда
   - Процентное изменение

2. **Status Card (Статусная карточка)**
   - Индикатор состояния (круговая диаграмма, процент)
   - Пояснительный текст
   - Разбивка по категориям

3. **Action Card (Активная карточка)**
   - Призыв к действию
   - Кнопка или ссылка
   - Поддерживающая графика

4. **List Card (Список)**
   - Вертикальный/горизонтальный список элементов
   - С возможностью скролла
   - С быстрыми действиями

### 2. Dashboard Layout Patterns

**Принцип сетки:**

```
Desktop (1440px+)
┌──────────────────────────────────────────┐
│ Header (Navigation)                      │
├──────────┬───────────────────────────────┤
│          │  Main Content Area            │
│ Sidebar  │  ┌─────────┬─────────────┐   │
│ (240px)  │  │ Card 1  │  Card 2     │   │
│          │  ├─────────┴─────────────┤   │
│ Nav      │  │ Large Card / Chart    │   │
│ Links    │  ├──────────┬────────────┤   │
│          │  │ Card 3   │  Card 4    │   │
│          │  └──────────┴────────────┘   │
└──────────┴───────────────────────────────┘

Tablet (768-1440px)
┌────────────────────────────┐
│ Header + Navigation        │
├────────────────────────────┤
│  Main Content Area         │
│  ┌────────┬────────┐       │
│  │ Card 1 │ Card 2 │       │
│  ├────────┴────────┤       │
│  │  Large Card     │       │
│  └─────────────────┘       │
└────────────────────────────┘

Mobile (< 768px)
┌──────────────┐
│ Header       │
├──────────────┤
│ Card 1       │
├──────────────┤
│ Card 2       │
├──────────────┤
│ Card 3       │
└──────────────┘
```

**Grid System:**

```css
.dashboard-grid {
  display: grid;
  gap: 24px;
  grid-template-columns: repeat(12, 1fr);
}

/* Примеры размеров карточек */
.card-small { grid-column: span 3; }   /* 1/4 ширины */
.card-medium { grid-column: span 6; }  /* 1/2 ширины */
.card-large { grid-column: span 9; }   /* 3/4 ширины */
.card-full { grid-column: span 12; }   /* Full width */
```

### 3. Navigation Patterns

**Табы (Tabs)**
```
Применение: Переключение между разделами на одной странице

┌─────────┬─────────┬─────────┬─────────┐
│  Sales  │ Finance │Customer │Marketing│  ← Active: Sales
└─────────┴─────────┴─────────┴─────────┘

Стиль:
- Active: жирный текст, подчеркивание или фоновая подсветка
- Inactive: серый текст, hover-эффект
- Мобильная версия: горизонтальный скролл
```

**Боковая навигация (Sidebar)**
```
Применение: Основная навигация в desktop версии

┌─────────────────┐
│ 🏠 Dashboard    │
│ 📊 Analytics    │  ← Active
│ 📅 Appointments │
│ 👤 Patients     │
│ ⚙️ Settings     │
└─────────────────┘

Стиль:
- Иконка + текст
- Active: цветной фон, акцентный цвет иконки
- Группировка по категориям
- Коллапсируемые секции
```

**Breadcrumbs**
```
Home > Пациенты > Иванов Иван > Карта пациента

Стиль:
- Серый цвет для неактивных крошек
- Синий цвет + ссылка для кликабельных элементов
- Текущая страница: жирный шрифт, не кликабельна
```

### 4. Form Components (Формы)

**Input Fields**

```css
.medical-input {
  width: 100%;
  padding: 12px 16px;
  border: 1.5px solid #E5E7EB;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.2s ease;
}

.medical-input:focus {
  outline: none;
  border-color: #4A90E2;
  box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.1);
}

.medical-input--error {
  border-color: #FF3B30;
}

.medical-input--success {
  border-color: #34C759;
}
```

**Принципы форм:**

1. **Floating Labels**
   - Label перемещается вверх при фокусе/заполнении
   - Экономит пространство
   - Улучшает визуальный поток

2. **Inline Validation**
   - Проверка по мере ввода (с debounce)
   - Зеленая галочка для корректных полей
   - Понятные сообщения об ошибках
   - Помощь/подсказки под полем

3. **Multi-Step Forms**
   - Прогресс-бар наверху
   - Возможность вернуться назад
   - Сохранение промежуточных данных
   - Четкая CTA на каждом шаге

### 5. Buttons & CTAs

**Кнопки:**

```css
/* Primary Button */
.btn-primary {
  background: #4A90E2;
  color: white;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 14px;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-primary:hover {
  background: #3A7BC8;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(74, 144, 226, 0.3);
}

.btn-primary:active {
  transform: translateY(0);
}

/* Secondary Button */
.btn-secondary {
  background: white;
  color: #4A90E2;
  border: 1.5px solid #4A90E2;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 14px;
}

/* Ghost Button */
.btn-ghost {
  background: transparent;
  color: #6B7280;
  padding: 12px 24px;
  border: none;
  font-weight: 500;
}

/* Icon Button */
.btn-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #F3F4F6;
  transition: all 0.2s ease;
}

.btn-icon:hover {
  background: #E5E7EB;
}
```

**Иерархия кнопок:**
1. Primary - основное действие (1 на экране)
2. Secondary - альтернативные действия
3. Ghost - третичные действия, отмена

### 6. Модальные окна и оверлеи

**Modal Design:**

```
Анатомия модального окна:
┌─────────────────────────────────────┐
│  [×]                                │  ← Close button
│                                     │
│  Modal Title                        │  ← Header
│                                     │
├─────────────────────────────────────┤
│                                     │
│  Content Area                       │  ← Body
│  Lorem ipsum dolor sit amet...      │
│                                     │
├─────────────────────────────────────┤
│           [Cancel]  [Action] ───────┤  ← Footer
└─────────────────────────────────────┘
```

**Принципы:**
- Затемненный backdrop (rgba(0,0,0,0.4))
- Центрирование по экрану
- Анимация появления (fade in + scale)
- Закрытие по ESC, клику вне окна
- Блокировка скролла основной страницы
- Максимальная ширина 600px

---

## 📊 Паттерны визуализации данных

### 1. Metrics Display (Отображение метрик)

**Крупные числовые показатели:**

```html
<div class="metric-card">
  <div class="metric-header">
    <span class="metric-icon">💊</span>
    <span class="metric-label">Принято медикаментов</span>
  </div>
  <div class="metric-value">
    <span class="metric-number">124</span>
    <span class="metric-unit">шт</span>
  </div>
  <div class="metric-change positive">
    <span class="change-indicator">↑</span>
    <span class="change-value">+12%</span>
    <span class="change-period">за неделю</span>
  </div>
  <div class="metric-chart">
    <!-- Mini sparkline chart -->
  </div>
</div>
```

**Стилистика:**
- Крупные числа (48-64px) для основной метрики
- Иконка или эмодзи для быстрой идентификации
- Цветовые индикаторы изменений (зеленый вверх, красный вниз)
- Микрографик для визуализации тренда

### 2. Charts & Graphs

**Line Charts (Линейные графики)**
- Для отображения трендов во времени
- Smooth curves вместо острых углов
- Gradient fill под линией для визуальной привлекательности
- Tooltips при hover с точными значениями

```javascript
// Пример конфигурации (Chart.js)
{
  type: 'line',
  options: {
    tension: 0.4, // Smooth curves
    fill: true,
    backgroundColor: 'rgba(107, 164, 255, 0.1)',
    borderColor: '#6BA4FF',
    borderWidth: 3,
    pointRadius: 0, // Скрыть точки на линии
    pointHoverRadius: 6, // Показать при hover
  }
}
```

**Bar Charts (Столбчатые диаграммы)**
- Для сравнения категорий
- Rounded corners на столбцах
- Горизонтальная ориентация для длинных лейблов
- Пастельные цвета для каждой категории

**Donut/Pie Charts (Круговые диаграммы)**
- Для отображения процентного соотношения
- Центральное число - общий показатель
- Сегменты с различными цветами
- Легенда рядом с графиком

```html
<div class="donut-chart">
  <svg viewBox="0 0 100 100">
    <!-- SVG paths for segments -->
  </svg>
  <div class="donut-center">
    <div class="donut-value">86%</div>
    <div class="donut-label">Satisfaction</div>
  </div>
</div>
```

**Heatmap Calendar (Календарная тепловая карта)**
- Отображение активности по дням
- GitHub-style календарь
- Цветовая интенсивность для значений
- Tooltip с датой и значением

```css
.calendar-heatmap {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}

.calendar-day {
  width: 16px;
  height: 16px;
  border-radius: 3px;
  background: #E5E7EB;
  transition: all 0.2s;
}

.calendar-day--filled-1 { background: #C7D2FE; }
.calendar-day--filled-2 { background: #A5B4FC; }
.calendar-day--filled-3 { background: #818CF8; }
.calendar-day--filled-4 { background: #6366F1; }
```

### 3. Progress Indicators

**Linear Progress Bar**
```html
<div class="progress-bar">
  <div class="progress-fill" style="width: 65%"></div>
</div>

<style>
.progress-bar {
  height: 8px;
  background: #E5E7EB;
  border-radius: 999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #7ED957, #6BC946);
  border-radius: 999px;
  transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}
</style>
```

**Circular Progress**
```html
<svg class="circular-progress" viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="45" 
          stroke="#E5E7EB" 
          stroke-width="10" 
          fill="none"/>
  <circle cx="50" cy="50" r="45"
          stroke="#4A90E2"
          stroke-width="10"
          fill="none"
          stroke-dasharray="282.6"
          stroke-dashoffset="70.65"
          stroke-linecap="round"/>
</svg>
```

**Step Progress**
```
[●]─────[●]─────[○]─────[○]
 1       2       3       4
Done   Current  Todo    Todo
```

### 4. Data Tables

**Принципы дизайна таблиц:**

1. **Минималистичные линии**
   - Отказ от тяжелых borders
   - Разделение через background color
   - Hover-эффект на строках

```css
.medical-table {
  width: 100%;
  border-collapse: collapse;
}

.medical-table thead {
  background: #F9FAFB;
  border-bottom: 2px solid #E5E7EB;
}

.medical-table th {
  padding: 12px 16px;
  text-align: left;
  font-weight: 600;
  font-size: 12px;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.medical-table td {
  padding: 16px;
  border-bottom: 1px solid #F3F4F6;
}

.medical-table tbody tr:hover {
  background: #F9FAFB;
}
```

2. **Сортировка и фильтрация**
   - Иконки сортировки в заголовках
   - Визуальный индикатор активной сортировки
   - Фильтры над таблицей или в выпадающем меню

3. **Pagination**
   - Номера страниц + стрелки навигации
   - Информация о количестве элементов
   - Выбор количества строк на странице

---

## 🎭 Микроинтерактивность

### 1. Hover Effects

**Карточки:**
```css
.card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
}
```

**Кнопки:**
```css
.button {
  transition: all 0.2s ease;
}

.button:hover {
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgba(74, 144, 226, 0.3);
}

.button:active {
  transform: scale(0.98);
}
```

### 2. Loading States

**Skeleton Screens**
```html
<div class="skeleton-card">
  <div class="skeleton-header">
    <div class="skeleton-circle"></div>
    <div class="skeleton-line short"></div>
  </div>
  <div class="skeleton-body">
    <div class="skeleton-line"></div>
    <div class="skeleton-line medium"></div>
    <div class="skeleton-line long"></div>
  </div>
</div>

<style>
.skeleton-line {
  height: 12px;
  background: linear-gradient(
    90deg,
    #F0F0F0 0%,
    #E0E0E0 50%,
    #F0F0F0 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
  margin-bottom: 8px;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
```

**Spinner**
```css
.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #E5E7EB;
  border-top-color: #4A90E2;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

### 3. Transitions

**Page Transitions**
```css
.page-enter {
  opacity: 0;
  transform: translateY(20px);
}

.page-enter-active {
  opacity: 1;
  transform: translateY(0);
  transition: all 0.3s ease-out;
}

.page-exit {
  opacity: 1;
}

.page-exit-active {
  opacity: 0;
  transition: all 0.2s ease-in;
}
```

**Modal Animation**
```css
.modal-backdrop {
  animation: fadeIn 0.2s ease-out;
}

.modal-content {
  animation: slideUp 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
```

### 4. Feedback Механизмы

**Toast Notifications**
```html
<div class="toast toast--success">
  <div class="toast-icon">✓</div>
  <div class="toast-content">
    <div class="toast-title">Успешно сохранено</div>
    <div class="toast-message">Данные пациента обновлены</div>
  </div>
  <button class="toast-close">×</button>
</div>

<style>
.toast {
  min-width: 300px;
  padding: 16px;
  border-radius: 12px;
  background: white;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  display: flex;
  align-items: start;
  gap: 12px;
  animation: slideInRight 0.3s ease-out;
}

.toast--success { border-left: 4px solid #34C759; }
.toast--error { border-left: 4px solid #FF3B30; }
.toast--info { border-left: 4px solid #5AC8FA; }

@keyframes slideInRight {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
</style>
```

**Tooltips**
```css
.tooltip {
  position: relative;
}

.tooltip::after {
  content: attr(data-tooltip);
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%) translateY(-8px);
  padding: 8px 12px;
  background: #1F2937;
  color: white;
  font-size: 12px;
  border-radius: 6px;
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s, transform 0.2s;
}

.tooltip:hover::after {
  opacity: 1;
  transform: translateX(-50%) translateY(-4px);
}
```

### 5. Empty States

```html
<div class="empty-state">
  <div class="empty-state-icon">
    <svg><!-- Illustration --></svg>
  </div>
  <h3 class="empty-state-title">Нет данных для отображения</h3>
  <p class="empty-state-message">
    Пока здесь ничего нет. Начните с добавления первого пациента.
  </p>
  <button class="btn-primary">Добавить пациента</button>
</div>

<style>
.empty-state {
  padding: 64px 32px;
  text-align: center;
  color: #6B7280;
}

.empty-state-icon {
  width: 120px;
  height: 120px;
  margin: 0 auto 24px;
  opacity: 0.6;
}

.empty-state-title {
  font-size: 20px;
  font-weight: 600;
  color: #1F2937;
  margin-bottom: 8px;
}

.empty-state-message {
  font-size: 14px;
  margin-bottom: 24px;
}
</style>
```

---

## 📱 Адаптивность и респонсив

### Breakpoints

```css
/* Mobile First Approach */

/* Extra Small - Mobile */
@media (min-width: 320px) { }

/* Small - Large Mobile */
@media (min-width: 640px) { }

/* Medium - Tablet */
@media (min-width: 768px) { }

/* Large - Desktop */
@media (min-width: 1024px) { }

/* Extra Large - Large Desktop */
@media (min-width: 1440px) { }

/* 2XL - Ultra Wide */
@media (min-width: 1920px) { }
```

### Адаптивные паттерны

**1. Stack → Grid**
```css
.responsive-grid {
  display: grid;
  gap: 24px;
  grid-template-columns: 1fr; /* Mobile: single column */
}

@media (min-width: 768px) {
  .responsive-grid {
    grid-template-columns: repeat(2, 1fr); /* Tablet: 2 columns */
  }
}

@media (min-width: 1024px) {
  .responsive-grid {
    grid-template-columns: repeat(3, 1fr); /* Desktop: 3 columns */
  }
}
```

**2. Hamburger Menu**
```html
<!-- Mobile -->
<nav class="mobile-nav">
  <button class="hamburger-menu">☰</button>
  <div class="mobile-menu">
    <!-- Menu items -->
  </div>
</nav>

<!-- Desktop -->
<nav class="desktop-nav">
  <ul class="nav-links">
    <li>Дашборд</li>
    <li>Пациенты</li>
    <li>Аналитика</li>
  </ul>
</nav>
```

**3. Touch-Friendly Targets**
```css
/* Минимальный размер тач-таргета: 44x44px (iOS HIG) */
.touch-target {
  min-width: 44px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Увеличенные отступы на мобильных */
@media (max-width: 768px) {
  .card {
    padding: 20px;
  }
  
  button {
    padding: 14px 24px;
  }
}
```

**4. Responsive Typography**
```css
:root {
  /* Mobile */
  --font-size-hero: 32px;
  --font-size-h1: 24px;
  --font-size-h2: 20px;
  --font-size-body: 14px;
}

@media (min-width: 768px) {
  :root {
    /* Tablet */
    --font-size-hero: 48px;
    --font-size-h1: 32px;
    --font-size-h2: 24px;
    --font-size-body: 16px;
  }
}

@media (min-width: 1024px) {
  :root {
    /* Desktop */
    --font-size-hero: 64px;
    --font-size-h1: 40px;
    --font-size-h2: 32px;
    --font-size-body: 16px;
  }
}
```

---

## 🏥 Специфика медицинского контекста

### 1. Обработка чувствительных данных

**Визуальные индикаторы конфиденциальности:**

```html
<div class="sensitive-data">
  <span class="lock-icon">🔒</span>
  <span class="label">Конфиденциальная информация</span>
</div>
```

**Принципы:**
- Явное указание на защищенность данных
- Возможность скрыть/показать чувствительную информацию
- Логи доступа к критичным данным
- Автоматический logout при неактивности

### 2. Критичные уведомления

**Иерархия важности:**

```css
/* Routine - обычная информация */
.notification--routine {
  background: #F0F9FF;
  border-left: 4px solid #5AC8FA;
}

/* Important - требует внимания */
.notification--important {
  background: #FFF7ED;
  border-left: 4px solid #FFCC00;
}

/* Urgent - критично */
.notification--urgent {
  background: #FEE2E2;
  border-left: 4px solid #FF3B30;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.9; }
}
```

**Принципы:**
- Звуковые уведомления для критичных событий
- Persistent notifications для важных задач
- Группировка уведомлений по типу
- Возможность отложить или выполнить действие сразу

### 3. Медицинская терминология

**Упрощение и глоссарий:**

```html
<div class="medical-term">
  <span class="term">Гипертензия</span>
  <span class="info-icon" data-tooltip="Повышенное артериальное давление">ⓘ</span>
</div>
```

**Принципы:**
- Tooltips с простыми объяснениями
- Ссылки на подробную информацию
- Визуальные референсы (нормы, диапазоны)
- Двойное отображение: медицинский + понятный термин

### 4. Временные метки и история

```html
<div class="timeline">
  <div class="timeline-item">
    <div class="timeline-marker"></div>
    <div class="timeline-content">
      <div class="timeline-time">14:30, 23 октября 2025</div>
      <div class="timeline-title">Прием препарата "Лизиноприл"</div>
      <div class="timeline-meta">Назначено: Доктор Иванова</div>
    </div>
  </div>
  <!-- More items -->
</div>

<style>
.timeline {
  position: relative;
  padding-left: 40px;
}

.timeline::before {
  content: '';
  position: absolute;
  left: 12px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #E5E7EB;
}

.timeline-item {
  position: relative;
  margin-bottom: 24px;
}

.timeline-marker {
  position: absolute;
  left: -34px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #4A90E2;
  border: 3px solid white;
  box-shadow: 0 0 0 2px #E5E7EB;
}

.timeline-time {
  font-size: 12px;
  color: #6B7280;
  margin-bottom: 4px;
}

.timeline-title {
  font-weight: 600;
  margin-bottom: 4px;
}

.timeline-meta {
  font-size: 14px;
  color: #9CA3AF;
}
</style>
```

### 5. Визуализация состояния здоровья

**Health Score Indicator:**

```html
<div class="health-score">
  <svg viewBox="0 0 200 120">
    <path class="gauge-bg" d="..."/>
    <path class="gauge-fill" d="..." 
          style="stroke-dasharray: 251; stroke-dashoffset: 62.75;"/>
  </svg>
  <div class="health-score-value">
    <span class="score">85</span>
    <span class="label">Отличное</span>
  </div>
</div>

<style>
.health-score {
  position: relative;
  width: 200px;
}

.gauge-bg {
  stroke: #E5E7EB;
  stroke-width: 20;
  fill: none;
}

.gauge-fill {
  stroke: #7ED957;
  stroke-width: 20;
  fill: none;
  stroke-linecap: round;
  transition: stroke-dashoffset 1s ease-out;
}

.health-score-value {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -20%);
  text-align: center;
}

.score {
  font-size: 48px;
  font-weight: 700;
  color: #1F2937;
}

.label {
  display: block;
  font-size: 14px;
  color: #6B7280;
}
</style>
```

**Vital Signs Display:**

```html
<div class="vitals-grid">
  <div class="vital-card">
    <div class="vital-icon">❤️</div>
    <div class="vital-value">72</div>
    <div class="vital-unit">уд/мин</div>
    <div class="vital-label">Пульс</div>
    <div class="vital-status normal">Норма</div>
  </div>
  
  <div class="vital-card">
    <div class="vital-icon">🌡️</div>
    <div class="vital-value">36.6</div>
    <div class="vital-unit">°C</div>
    <div class="vital-label">Температура</div>
    <div class="vital-status normal">Норма</div>
  </div>
  
  <div class="vital-card alert">
    <div class="vital-icon">💉</div>
    <div class="vital-value">145/92</div>
    <div class="vital-unit">мм рт.ст.</div>
    <div class="vital-label">Давление</div>
    <div class="vital-status elevated">Повышено</div>
  </div>
</div>

<style>
.vitals-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
}

.vital-card {
  background: white;
  padding: 20px;
  border-radius: 12px;
  text-align: center;
  border: 2px solid #E5E7EB;
  transition: all 0.3s ease;
}

.vital-card.alert {
  border-color: #FF9B9B;
  background: #FFF5F5;
}

.vital-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.vital-value {
  font-size: 32px;
  font-weight: 700;
  color: #1F2937;
}

.vital-unit {
  font-size: 12px;
  color: #6B7280;
  margin-bottom: 4px;
}

.vital-label {
  font-size: 14px;
  color: #6B7280;
  margin-bottom: 8px;
}

.vital-status {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.vital-status.normal {
  background: #D1FAE5;
  color: #065F46;
}

.vital-status.elevated {
  background: #FEE2E2;
  color: #991B1B;
}
</style>
```

### 6. Accessibility для медицинских приложений

**Критичные требования:**

1. **Цветовая слепота**
   - Не полагаться только на цвет для передачи информации
   - Использовать иконки, паттерны, текстовые метки

2. **Screen Readers**
   - ARIA-labels для всех интерактивных элементов
   - Семантический HTML (section, article, nav)
   - Описания для графиков и визуализаций

3. **Keyboard Navigation**
   - Tab-индексы для логического порядка навигации
   - Focus states для всех интерактивных элементов
   - Shortcuts для критичных действий

```css
/* Focus States */
*:focus-visible {
  outline: 2px solid #4A90E2;
  outline-offset: 2px;
  border-radius: 4px;
}

button:focus-visible,
input:focus-visible {
  box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.2);
}
```

4. **Крупный шрифт и контраст**
   - Минимальный размер шрифта 14px
   - Контраст 4.5:1 для обычного текста
   - Контраст 3:1 для крупного текста (18px+)
   - Возможность увеличить шрифт в настройках

---

## 🎯 Чек-лист внедрения

### Phase 1: Фундамент (Неделя 1-2)

- [ ] Настроить дизайн-токены (цвета, шрифты, отступы)
- [ ] Создать базовые компоненты (Button, Input, Card)
- [ ] Внедрить типографическую систему
- [ ] Настроить grid system и breakpoints

### Phase 2: Компоненты (Неделя 3-4)

- [ ] Разработать карточки разных типов
- [ ] Создать навигационные элементы
- [ ] Реализовать формы с валидацией
- [ ] Добавить модальные окна и оверлеи

### Phase 3: Визуализация (Неделя 5-6)

- [ ] Интегрировать библиотеку графиков
- [ ] Создать компоненты для метрик
- [ ] Реализовать прогресс-индикаторы
- [ ] Настроить таблицы с сортировкой

### Phase 4: Интерактивность (Неделя 7-8)

- [ ] Добавить hover-эффекты и transitions
- [ ] Реализовать loading states (skeleton, spinner)
- [ ] Создать систему уведомлений (toast)
- [ ] Настроить empty states

### Phase 5: Полировка (Неделя 9-10)

- [ ] Адаптировать все компоненты под mobile
- [ ] Провести accessibility audit
- [ ] Оптимизировать производительность
- [ ] Создать UI Kit / Storybook

---

## 📚 Рекомендуемые инструменты

### Design
- **Figma** - основной инструмент дизайна
- **Figma Plugins**: Stark (accessibility), Iconify, Unsplash

### Development
- **CSS Framework**: Tailwind CSS (utility-first)
- **Component Library**: shadcn/ui или Chakra UI (как база)
- **Icons**: Lucide Icons, Heroicons
- **Charts**: Chart.js, Recharts, или D3.js
- **Animations**: Framer Motion

### Testing
- **Lighthouse** - производительность и accessibility
- **WAVE** - accessibility тестирование
- **BrowserStack** - кроссбраузерность

---

## 🔄 Итерации и обновления

Эта дизайн-система - живой документ. Рекомендуется:

1. **Ежемесячно** проводить UX-аудит с реальными пользователями
2. **Ежеквартально** обновлять компоненты на основе feedback
3. **Ежегодно** пересматривать визуальный стиль

### Сбор обратной связи

- Встроенные формы feedback на каждой странице
- A/B тестирование ключевых экранов
- Отслеживание метрик: время на задачу, количество ошибок, успешность выполнения действий
- Пользовательские интервью (минимум 5 в квартал)

---

## ✨ Заключение

Эта дизайн-система основана на референсах из современных dashboard-приложений и адаптирована под специфику медицинского контекста. Ключевые принципы:

1. **Эмпатия** - дизайн снижает стресс, а не добавляет его
2. **Ясность** - информация структурирована и понятна
3. **Доверие** - визуальная надежность и профессионализм
4. **Эффективность** - быстрый доступ к критичным данным
5. **Привлекательность** - приятный глазу интерфейс, к которому хочется возвращаться

Следуя этим паттернам, ваш медицинский сервис станет не просто функциональным инструментом, но и приятным пространством для работы, к которому пользователи будут эмоционально привязаны.

---

**Документ подготовлен:** Октябрь 2025  
**Следующее обновление:** Январь 2026

# MedHistory Telegram Bot — n8n Workflows

## Предварительные требования

1. Работающее приложение MedHistory (backend + postgres + mongodb + minio)
2. Docker Compose с сервисом n8n (уже добавлен в `docker-compose.yml`)

---

## Шаг 1: Создать Telegram-бота

1. Откройте Telegram и найдите [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot`
3. Введите имя бота (например: `MedHistory Bot`)
4. Введите username бота (например: `medhistory_local_bot`)
5. Скопируйте полученный **Bot Token** (формат: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

## Шаг 2: Настроить переменные окружения

Добавьте в файл `.env` (или `.env.local`):

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=<ваш токен от BotFather>
BOT_SECRET=<случайная строка для защиты API бота>

# n8n
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=<пароль для доступа к n8n UI>
N8N_ENCRYPTION_KEY=<случайная строка для шифрования credentials в n8n>
N8N_WEBHOOK_URL=http://localhost:5678
```

Для production замените `N8N_WEBHOOK_URL` на внешний URL сервера:
```env
N8N_WEBHOOK_URL=https://n8n.yourdomain.com
```

Сгенерировать случайные строки можно командой:
```bash
openssl rand -hex 32
```

## Шаг 3: Запустить инфраструктуру

```bash
# Применить миграции (если ещё не применены)
docker compose exec postgres psql -U medhistory_user -d medhistory -f /app/migrations/007_add_telegram_id.sql
docker compose exec postgres psql -U medhistory_user -d medhistory -f /app/migrations/008_add_bot_state.sql

# Перезапустить сервисы
docker compose up -d
```

n8n будет доступен по адресу: **http://localhost:5678**

## Шаг 4: Настроить Telegram Credentials в n8n

1. Откройте n8n UI: http://localhost:5678
2. Войдите с логином/паролем из `.env`
3. Перейдите в **Settings → Credentials → Add Credential**
4. Выберите тип: **Telegram API**
5. Введите:
   - **Name:** `MedHistory Bot`
   - **Access Token:** `<ваш TELEGRAM_BOT_TOKEN>`
6. Сохраните credential

## Шаг 5: Импортировать workflow

1. В n8n UI нажмите **Add Workflow** (или **Import from File**)
2. Выберите файл: `n8n/workflows/medhistory_telegram_bot.json`
3. После импорта workflow появится в списке

## Шаг 6: Привязать credentials к нодам

После импорта нужно переназначить Telegram credential на все ноды:

1. Откройте импортированный workflow
2. Для каждой ноды типа "Telegram" и "Telegram Trigger":
   - Кликните на ноду
   - В поле **Credential** выберите `MedHistory Bot`
   - Сохраните
3. Сохраните workflow

## Шаг 7: Активировать workflow

1. В правом верхнем углу workflow нажмите **Toggle Active**
2. n8n автоматически установит Webhook для Telegram Bot API
3. Проверьте бота — отправьте `/start` в Telegram

---

## Структура workflow

### Основной поток:

```
Telegram Trigger → Parse Update → Get Bot State → Determine Route → Main Router
```

### Ветки (branches):

| Команда/Событие | Описание |
|---|---|
| `/start` | Приветственное сообщение |
| `/login` | Начало авторизации (ввод email → пароль) |
| `/documents` | Список последних документов с inline-кнопками |
| `/interpret` | Выбор документов для AI-интерпретации |
| `/help` | Справка по командам |
| `/logout` | Выход из аккаунта |
| `/status` | Количество документов |
| Фото/PDF | Загрузка документа |
| Callback | Обработка нажатий inline-кнопок |

### Callback-действия:

| Callback Data | Описание |
|---|---|
| `doc_<UUID>` | Просмотр деталей документа |
| `isel_<UUID>` | Выбор/снятие выбора документа для интерпретации |
| `interp_confirm` | Запуск интерпретации |
| `interp_cancel` | Отмена интерпретации |

---

## Кастомизация

Вся логика бота редактируется через визуальный интерфейс n8n:

- **Добавить новую команду:** добавьте условие в "Main Router" Switch-ноду и новую ветку
- **Изменить текст сообщений:** отредактируйте параметры Telegram-нод
- **Добавить логику:** используйте Code-ноды (JavaScript) для сложной обработки
- **Добавить API-вызовы:** добавьте HTTP Request ноды для вызова новых эндпоинтов

---

## Troubleshooting

### Бот не отвечает
- Проверьте что workflow активирован (зелёный тумблер)
- Проверьте что Telegram credential корректен
- Проверьте логи n8n: `docker compose logs n8n`

### Ошибки авторизации
- Проверьте что `BOT_SECRET` одинаковый в `.env` и доступен в n8n через env variable
- Проверьте что backend доступен из n8n: `docker compose exec n8n curl http://backend:8000/health`

### Ошибки загрузки файлов
- Проверьте что `TELEGRAM_BOT_TOKEN` доступен как env variable в n8n
- Максимальный размер файла через Telegram API: 20 MB

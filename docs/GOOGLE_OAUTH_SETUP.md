# Настройка Google OAuth

Инструкция по настройке авторизации через Google для MedHistory.

## Шаг 1: Создание проекта в Google Cloud Console

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Нажмите **Select a project** → **New Project**
3. Введите название проекта (например, `MedHistory`)
4. Нажмите **Create**

## Шаг 2: Настройка OAuth Consent Screen

1. В меню слева выберите **APIs & Services** → **OAuth consent screen**
2. Выберите тип пользователей:
   - **External** — для любых Google аккаунтов
   - **Internal** — только для аккаунтов вашей организации (если используете Google Workspace)
3. Нажмите **Create**
4. Заполните обязательные поля:
   - **App name**: `MedHistory`
   - **User support email**: ваш email
   - **Developer contact information**: ваш email
5. Нажмите **Save and Continue**
6. На странице **Scopes** нажмите **Add or Remove Scopes**:
   - Выберите: `openid`, `email`, `profile`
   - Нажмите **Update**
7. Нажмите **Save and Continue**
8. На странице **Test users** (если выбрали External):
   - Добавьте email-адреса тестовых пользователей
   - В режиме тестирования только эти пользователи смогут авторизоваться
9. Нажмите **Save and Continue**

## Шаг 3: Создание OAuth 2.0 Credentials

1. В меню слева выберите **APIs & Services** → **Credentials**
2. Нажмите **+ Create Credentials** → **OAuth client ID**
3. Выберите **Application type**: `Web application`
4. Введите **Name**: `MedHistory Web Client`
5. В **Authorized JavaScript origins** добавьте:
   ```
   http://localhost:5173
   ```
6. В **Authorized redirect URIs** добавьте:
   ```
   http://localhost:5173/auth/google/callback
   ```
7. Нажмите **Create**
8. Скопируйте **Client ID** и **Client Secret**

## Шаг 4: Настройка переменных окружения

Добавьте полученные данные в файл `.env.local`:

```env
GOOGLE_CLIENT_ID=123456789-abcdefg.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxx
GOOGLE_REDIRECT_URI=http://localhost:5173/auth/google/callback
```

## Шаг 5: Применение миграции базы данных

Выполните SQL-миграцию для добавления поля `google_id`:

```bash
# Подключитесь к PostgreSQL и выполните:
psql -h localhost -U medhistory_user -d medhistory -f backend/migrations/006_add_google_oauth.sql
```

Или через Docker:
```bash
docker exec -i medhistory-postgres psql -U medhistory_user -d medhistory < backend/migrations/006_add_google_oauth.sql
```

## Шаг 6: Перезапуск приложения

```bash
# Перезапустите бэкенд
docker-compose -f docker-compose.local.yml restart backend

# Или для локальной разработки без Docker
cd backend && uvicorn main:app --reload
```

## Настройка для Production

Для production окружения:

1. Добавьте ваш production домен в **Authorized JavaScript origins**:
   ```
   https://your-domain.com
   ```

2. Добавьте redirect URI для production:
   ```
   https://your-domain.com/auth/google/callback
   ```

3. Обновите `GOOGLE_REDIRECT_URI` в production.env:
   ```env
   GOOGLE_REDIRECT_URI=https://your-domain.com/auth/google/callback
   ```

4. **Важно**: Для публичного приложения необходимо пройти верификацию Google:
   - Перейдите в **OAuth consent screen**
   - Нажмите **Publish App**
   - Следуйте инструкциям по верификации

## Решение проблем

### Ошибка "redirect_uri_mismatch"
- Убедитесь, что URI в настройках Google Console точно совпадает с `GOOGLE_REDIRECT_URI`
- Проверьте протокол (http vs https) и порт

### Ошибка "access_denied"
- Проверьте, что пользователь добавлен в список тестовых пользователей (для External в режиме тестирования)

### Ошибка "invalid_client"
- Проверьте правильность `GOOGLE_CLIENT_ID` и `GOOGLE_CLIENT_SECRET`
- Убедитесь, что credentials активны в Google Console

## Архитектура авторизации

```
┌─────────────┐     1. Клик "Войти через Google"      ┌─────────────┐
│   Frontend  │ ────────────────────────────────────► │   Backend   │
│   (React)   │ ◄──────────────────────────────────── │  (FastAPI)  │
└─────────────┘     2. Возвращает Google Auth URL     └─────────────┘
       │
       │ 3. Редирект на Google
       ▼
┌─────────────┐
│   Google    │
│   OAuth     │
└─────────────┘
       │
       │ 4. После авторизации - редирект с code
       ▼
┌─────────────┐     5. Отправка code на бэкенд        ┌─────────────┐
│  Callback   │ ────────────────────────────────────► │   Backend   │
│   Page      │ ◄──────────────────────────────────── │  (FastAPI)  │
└─────────────┘     6. JWT токен                      └─────────────┘
                                                            │
                                                            │ Обмен code на token
                                                            │ + получение user info
                                                            ▼
                                                      ┌─────────────┐
                                                      │   Google    │
                                                      │   API       │
                                                      └─────────────┘
```

## Безопасность

- `GOOGLE_CLIENT_SECRET` должен храниться только на сервере, никогда на клиенте
- Используйте HTTPS в production
- State параметр защищает от CSRF атак
- Токены Google не сохраняются — используется только для получения информации о пользователе


# Admin Panel Setup Guide

## Overview

Админ-панель для системы скачивания документов Reyestr с следующими возможностями:

1. **WebAuthn/FIDO2 авторизация** - безопасный вход через YubiKey или телефон
2. **Мониторинг клиентов в реальном времени** - отслеживание активности, скорости скачивания, ошибок
3. **Навигация по карте задач** - просмотр задач по регионам, типам инстанций и датам
4. **Telegram уведомления** - получение критических ошибок в Telegram
5. **Управление профилем** - редактирование настроек пользователя

## Backend Setup

### 1. Установите зависимости

```bash
pip install -r requirements.txt
```

### 2. Настройте базу данных

Выполните миграции для создания таблиц пользователей и WebAuthn:

```bash
psql -U reyestr_user -d reyestr_db -f database/migrations/006_add_users_and_webauthn.sql
```

### 3. Настройте переменные окружения

Создайте файл `.env` в корне проекта:

```env
# Database
DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=reyestr_db
DB_USER=reyestr_user
DB_PASSWORD=reyestr_password

# API Server
API_HOST=0.0.0.0
API_PORT=8000

# Telegram Bot (для уведомлений)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

### 4. Запустите сервер

```bash
python -m server.main
```

Или через uvicorn:

```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

## Frontend Setup

### 1. Установите зависимости

```bash
cd admin
npm install
```

### 2. Настройте переменные окружения

Создайте файл `admin/.env`:

```env
VITE_API_URL=http://localhost:8000/api/v1
```

### 3. Запустите dev сервер

```bash
npm run dev
```

Админ-панель будет доступна по адресу `http://localhost:3000`

## Использование

### Регистрация пользователя

1. Откройте админ-панель
2. Перейдите на вкладку "Register"
3. Введите username и display name
4. Нажмите "Register with WebAuthn"
5. Подключите YubiKey или используйте телефон для регистрации

### Вход

1. Введите username
2. Нажмите "Login with WebAuthn"
3. Подключите зарегистрированный YubiKey или используйте телефон

### Настройка Telegram уведомлений

1. Создайте Telegram бота через [@BotFather](https://t.me/BotFather)
2. Получите токен бота
3. Добавьте токен в `.env` файл: `TELEGRAM_BOT_TOKEN=your_token`
4. Получите свой Chat ID (можно через [@userinfobot](https://t.me/userinfobot))
5. В админ-панели перейдите в Profile
6. Введите Telegram Chat ID
7. Сохраните изменения

Теперь вы будете получать уведомления о критических ошибках в Telegram.

### Мониторинг клиентов

1. Перейдите на страницу "Clients"
2. Просмотрите список всех клиентов
3. Нажмите на иконку информации для просмотра детальной активности
4. Данные обновляются автоматически каждые 2 секунды

### Навигация по задачам

1. Перейдите на страницу "Tasks Map"
2. Просмотрите индексы задач, сгруппированные по регионам и типам инстанций
3. Нажмите "View Tasks" для просмотра детальной информации

## API Endpoints

### WebAuthn

- `POST /api/v1/auth/webauthn/register/start` - Начать регистрацию
- `POST /api/v1/auth/webauthn/register/complete` - Завершить регистрацию
- `POST /api/v1/auth/webauthn/login/start` - Начать вход
- `POST /api/v1/auth/webauthn/login/complete` - Завершить вход

### Users

- `GET /api/v1/users/me` - Получить профиль
- `PATCH /api/v1/users/me` - Обновить профиль

### Clients

- `GET /api/v1/clients` - Список клиентов
- `GET /api/v1/clients/{id}/activity` - Активность клиента в реальном времени
- `GET /api/v1/clients/{id}/statistics` - Статистика клиента

### Tasks

- `GET /api/v1/tasks` - Список задач
- `GET /api/v1/tasks/indexes` - Индексы задач
- `GET /api/v1/tasks/by-index` - Задачи по индексу

## Примечания

- WebAuthn требует HTTPS в production (или localhost для разработки)
- Telegram уведомления отправляются только при критических ошибках (failed tasks)
- Мониторинг использует polling каждые 2-5 секунд (можно заменить на WebSocket)
- В production рекомендуется использовать Redis для хранения challenges и токенов

# Распределенная система загрузки документов

## Обзор

Система позволяет распределять загрузку документов из реестра между несколькими клиентами, работающими на разных хостах. Централизованный сервер управляет задачами и координирует работу клиентов.

## Архитектура

```
┌─────────────────┐
│  Gate Server    │
│  (API Server)   │
│  Port 443/HTTPS │
│  + Nginx        │
└────────┬────────┘
         │
         ├─── PostgreSQL (централизованная БД)
         │
         ├─── API Endpoints:
         │    - GET /api/v1/tasks/request  (получить задачу)
         │    - POST /api/v1/tasks/complete (отметить задачу выполненной)
         │    - GET /api/v1/tasks/status    (статус задач)
         │
    ┌────┴────┬──────────┬──────────┐
    │         │          │          │
┌───▼───┐ ┌──▼───┐  ┌───▼───┐  ┌───▼───┐
│Client1│ │Client2│  │Client3│  │ClientN│
│Host 1 │ │Host 2 │  │Host 3 │  │Host N │
└───────┘ └───────┘  └───────┘  └───────┘
```

## Компоненты

### 1. Сервер (`downloader_server.py`)

Централизованный сервер для управления задачами загрузки.

**Запуск:**
```bash
python downloader_server.py
```

**Конфигурация через переменные окружения:**
```bash
export DB_HOST=127.0.0.1
export DB_PORT=5433
export DB_NAME=reyestr_db
export DB_USER=reyestr_user
export DB_PASSWORD=reyestr_password
export API_HOST=0.0.0.0
export API_PORT=8000
export ENABLE_AUTH=true
```

**Или создайте файл `.env`:**
```
DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=reyestr_db
DB_USER=reyestr_user
DB_PASSWORD=reyestr_password
API_HOST=0.0.0.0
API_PORT=8000
ENABLE_AUTH=true
```

### 2. Клиент (`downloader_client.py`)

Клиент для подключения к серверу и выполнения задач.

**Запуск:**
```bash
python downloader_client.py \
    --api-url https://gate-server.com \
    --api-key YOUR_API_KEY \
    --client-name my-client \
    --output-dir downloaded_documents \
    --poll-interval 5 \
    --heartbeat-interval 60
```

**Параметры:**
- `--api-url` (обязательно) - URL сервера
- `--api-key` (опционально) - API ключ для аутентификации
- `--client-name` (опционально) - Имя клиента
- `--output-dir` - Директория для сохранения документов
- `--poll-interval` - Интервал опроса новых задач (секунды)
- `--heartbeat-interval` - Интервал отправки heartbeat (секунды)
- `--db-host` - Хост БД (если отличается от сервера)
- `--db-port` - Порт БД

### 3. База данных

#### Миграция

Перед использованием необходимо выполнить миграцию БД:

```bash
psql -h 127.0.0.1 -p 5433 -U reyestr_user -d reyestr_db -f database/migrations/001_add_distributed_tables.sql
```

Или через Docker:
```bash
docker exec -i reyestr_db psql -U reyestr_user -d reyestr_db < database/migrations/001_add_distributed_tables.sql
```

#### Новые таблицы

- `download_clients` - Зарегистрированные клиенты
- `download_tasks` - Задачи загрузки

### 4. Nginx конфигурация

Скопируйте `nginx.conf.example` в `/etc/nginx/sites-available/reyestr-download-server` и настройте:

1. Замените `your-gate-server.com` на ваш домен
2. Настройте SSL сертификаты
3. Создайте symlink: `ln -s /etc/nginx/sites-available/reyestr-download-server /etc/nginx/sites-enabled/`
4. Проверьте: `nginx -t`
5. Перезагрузите: `systemctl reload nginx`

## Использование

### 1. Запуск сервера

На gate server:
```bash
# Установите зависимости
pip install -r requirements.txt

# Выполните миграцию БД
psql -h 127.0.0.1 -p 5433 -U reyestr_user -d reyestr_db -f database/migrations/001_add_distributed_tables.sql

# Запустите сервер
python downloader_server.py
```

### 2. Создание задач

Задачи можно создавать через API:

```bash
curl -X POST https://gate-server.com/api/v1/tasks/create \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "search_params": {
      "CourtRegion": "11",
      "INSType": "1"
    },
    "start_page": 1,
    "max_documents": 100
  }'
```

### 3. Запуск клиентов

На каждом клиентском хосте:

```bash
# Установите зависимости
pip install -r requirements.txt

# Запустите клиент
python downloader_client.py \
    --api-url https://gate-server.com \
    --api-key YOUR_API_KEY \
    --client-name client-1
```

Клиент будет автоматически:
- Подключаться к серверу
- Запрашивать задачи
- Выполнять загрузку
- Отправлять результаты на сервер
- Отправлять heartbeat

## API Endpoints

### Получить задачу
```http
POST /api/v1/tasks/request
Headers: X-API-Key: YOUR_API_KEY
Response: {
  "task_id": "uuid",
  "search_params": {...},
  "start_page": 1,
  "max_documents": 100,
  "status": "assigned"
}
```

### Завершить задачу
```http
POST /api/v1/tasks/complete
Headers: X-API-Key: YOUR_API_KEY
Body: {
  "task_id": "uuid",
  "documents_downloaded": 95,
  "documents_failed": 2,
  "documents_skipped": 3,
  "result_summary": {...}
}
```

### Создать задачу
```http
POST /api/v1/tasks/create
Headers: X-API-Key: YOUR_API_KEY
Body: {
  "search_params": {...},
  "start_page": 1,
  "max_documents": 100
}
```

### Статус задачи
```http
GET /api/v1/tasks/{task_id}
Headers: X-API-Key: YOUR_API_KEY
```

### Список задач
```http
GET /api/v1/tasks?status_filter=pending&limit=100
Headers: X-API-Key: YOUR_API_KEY
```

### Регистрация клиента
```http
POST /api/v1/clients/register
Body: {
  "client_name": "my-client",
  "client_host": "hostname",
  "api_key": "optional-key"
}
```

### Heartbeat
```http
POST /api/v1/clients/heartbeat
Headers: X-API-Key: YOUR_API_KEY
```

## Безопасность

1. **Аутентификация**: Используйте API ключи для защиты доступа
2. **HTTPS**: Обязательно используйте HTTPS (порт 443) через nginx
3. **Rate Limiting**: Настроен в nginx для защиты от злоупотреблений
4. **Валидация**: Все входные данные валидируются через Pydantic

## Мониторинг

### Проверка здоровья сервера
```bash
curl https://gate-server.com/health
```

### Статистика задач
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  https://gate-server.com/api/v1/tasks
```

### Статистика клиентов
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  https://gate-server.com/api/v1/clients
```

## Устранение неполадок

### Сервер не запускается
- Проверьте подключение к БД
- Убедитесь, что миграция выполнена
- Проверьте логи

### Клиент не получает задачи
- Проверьте подключение к серверу: `curl https://gate-server.com/health`
- Убедитесь, что есть pending задачи
- Проверьте API ключ

### Задачи не выполняются
- Проверьте логи клиента
- Убедитесь, что БД доступна с клиента
- Проверьте настройки поиска

## Разработка

### Структура проекта

```
reyestr/
├── downloader_server.py      # Сервер (точка входа)
├── downloader_client.py     # Клиент (точка входа)
├── downloader.py            # Оригинальный downloader (локальный режим)
├── server/                  # Модули сервера
│   ├── main.py              # FastAPI приложение
│   ├── config.py            # Конфигурация
│   ├── api/                 # API модули
│   │   ├── routes.py        # API endpoints
│   │   ├── models.py        # Pydantic модели
│   │   └── auth.py          # Аутентификация
│   └── database/            # Работа с БД
│       ├── connection.py    # Connection pool
│       └── task_manager.py  # Управление задачами
├── client/                  # Модули клиента
│   └── api_client.py        # API клиент
├── database/
│   └── migrations/
│       └── 001_add_distributed_tables.sql
└── nginx.conf.example       # Конфигурация nginx
```

## Дальнейшее развитие

- [ ] Автоматическая генерация задач на основе анализа БД
- [ ] Приоритеты задач
- [ ] Автоматическое перераспределение при таймаутах
- [ ] Веб-интерфейс для мониторинга
- [ ] Метрики и аналитика
- [ ] Поддержка нескольких серверов (load balancing)

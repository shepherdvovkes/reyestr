# Статистика клиентов

## Обзор

Сервер автоматически отслеживает статистику каждого клиента, включая количество выполненных задач, загруженных документов и другую информацию.

## Как это работает

### 1. Регистрация клиента

При первом подключении клиент регистрируется на сервере и получает уникальный `client_id` (UUID).

```python
from client.api_client import DownloadServerClient

client = DownloadServerClient(
    base_url="https://gate-server.com",
    api_key="YOUR_API_KEY",
    client_name="my-client"
)

# client.client_id будет установлен после регистрации
print(f"Client ID: {client.client_id}")
```

### 2. Автоматическое отслеживание

Сервер автоматически обновляет статистику клиента при:

- **Завершении задачи** - увеличивается `total_tasks_completed`
- **Регистрации документа** - увеличивается `total_documents_downloaded`
- **Отправке heartbeat** - обновляется `last_heartbeat` и `status`

### 3. Связь документов с клиентами

Каждый зарегистрированный документ связан с клиентом через поле `client_id` в таблице `documents`. Это позволяет:

- Отслеживать, какой клиент загрузил каждый документ
- Получать статистику по документам для каждого клиента
- Анализировать производительность клиентов

## Статистика клиента

### Базовая информация

- `client_id` - Уникальный ID клиента (UUID)
- `client_name` - Имя клиента
- `client_host` - Хост клиента
- `status` - Статус ('active', 'inactive', 'error')
- `last_heartbeat` - Время последнего heartbeat
- `created_at` - Дата регистрации
- `updated_at` - Время последнего обновления

### Статистика задач

- `total_tasks_completed` - Всего выполнено задач
- `total_tasks` - Всего назначено задач
- `completed_tasks` - Успешно выполненных
- `in_progress_tasks` - В процессе выполнения
- `failed_tasks` - Провалившихся
- `pending_tasks` - Ожидающих выполнения
- `total_docs_from_tasks` - Всего документов из задач
- `total_docs_failed` - Провалившихся документов
- `total_docs_skipped` - Пропущенных документов
- `first_task_date` - Дата первой задачи
- `last_task_date` - Дата последней задачи

### Статистика документов

- `total_documents_downloaded` - Всего загружено документов
- `total_documents` - Всего зарегистрировано документов
- `unique_regions` - Уникальных регионов
- `unique_instance_types` - Уникальных типов инстанций
- `unique_case_types` - Уникальных типов дел
- `classified_documents` - Классифицированных документов
- `first_document_date` - Дата первого документа
- `last_document_date` - Дата последнего документа

## API

### Получить статистику текущего клиента

```http
GET /api/v1/clients/me/statistics
Headers: X-API-Key: YOUR_API_KEY
```

**Ответ:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "client_name": "my-client",
  "client_host": "hostname",
  "status": "active",
  "last_heartbeat": "2025-01-11T10:30:00Z",
  "total_tasks_completed": 15,
  "total_documents_downloaded": 1250,
  "created_at": "2025-01-10T08:00:00Z",
  "updated_at": "2025-01-11T10:30:00Z",
  "task_statistics": {
    "total_tasks": 15,
    "completed_tasks": 14,
    "in_progress_tasks": 1,
    "failed_tasks": 0,
    "pending_tasks": 0,
    "total_docs_from_tasks": 1250,
    "total_docs_failed": 5,
    "total_docs_skipped": 10,
    "first_task_date": "2025-01-10T08:15:00Z",
    "last_task_date": "2025-01-11T10:25:00Z"
  },
  "document_statistics": {
    "total_documents": 1250,
    "unique_regions": 5,
    "unique_instance_types": 2,
    "unique_case_types": 12,
    "classified_documents": 1200,
    "first_document_date": "2025-01-10T08:20:00Z",
    "last_document_date": "2025-01-11T10:28:00Z"
  }
}
```

### Получить статистику конкретного клиента

```http
GET /api/v1/clients/{client_id}/statistics
Headers: X-API-Key: YOUR_API_KEY
```

**Примечание:** Клиенты могут просматривать только свою собственную статистику.

### Получить список всех клиентов

```http
GET /api/v1/clients
Headers: X-API-Key: YOUR_API_KEY
```

## Использование в коде

### Получить свою статистику

```python
from client.api_client import DownloadServerClient

client = DownloadServerClient(
    base_url="https://gate-server.com",
    api_key="YOUR_API_KEY"
)

# Получить статистику текущего клиента
stats = client.get_client_statistics()

if stats:
    print(f"Client: {stats['client_name']}")
    print(f"Tasks completed: {stats['total_tasks_completed']}")
    print(f"Documents downloaded: {stats['total_documents_downloaded']}")
    print(f"Active tasks: {stats['task_statistics']['in_progress_tasks']}")
    print(f"Documents registered: {stats['document_statistics']['total_documents']}")
```

### Мониторинг в реальном времени

```python
import time

while True:
    stats = client.get_client_statistics()
    if stats:
        print(f"Tasks: {stats['task_statistics']['completed_tasks']}/{stats['task_statistics']['total_tasks']}")
        print(f"Documents: {stats['document_statistics']['total_documents']}")
    time.sleep(60)  # Обновлять каждую минуту
```

## Представления базы данных

### clients_statistics

Полная статистика всех клиентов:

```sql
SELECT * FROM clients_statistics;
```

### documents_by_client

Документы, сгруппированные по клиентам:

```sql
SELECT * FROM documents_by_client;
```

## Миграция базы данных

Перед использованием необходимо выполнить миграцию:

```bash
psql -h 127.0.0.1 -p 5433 -U reyestr_user -d reyestr_db \
  -f database/migrations/004_add_client_id_to_documents.sql
```

Или через Docker:

```bash
docker exec -i reyestr_db psql -U reyestr_user -d reyestr_db \
  < database/migrations/004_add_client_id_to_documents.sql
```

## Автоматическое обновление статистики

Статистика обновляется автоматически:

1. **При регистрации документа** - `total_documents_downloaded` увеличивается на 1
2. **При завершении задачи** - `total_tasks_completed` увеличивается на 1
3. **При отправке heartbeat** - обновляется `last_heartbeat` и `status`

Все обновления происходят атомарно в транзакциях БД.

## Преимущества

1. **Автоматическое отслеживание** - не требует ручного ввода
2. **Детальная статистика** - задачи и документы
3. **Производительность** - быстрые запросы благодаря индексам
4. **Масштабируемость** - работает с любым количеством клиентов
5. **Прозрачность** - видно вклад каждого клиента

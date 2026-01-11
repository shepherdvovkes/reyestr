# Регистрация документов на сервере

## Обзор

Сервер автоматически назначает каждому документу системный UUID ID и выполняет предварительную классификацию на основе метаданных и параметров поиска.

## Как это работает

### 1. Назначение системного ID

При регистрации документа сервер:
- Генерирует уникальный UUID (`system_id`) для внутренней идентификации
- Сохраняет внешний ID документа (`id` или `reg_number`) из реестра
- Оба ID сохраняются в базе данных

### 2. Классификация документов

Сервер автоматически классифицирует документы по:

#### Источники классификации (в порядке приоритета):

1. **Параметры поиска** (`search_params`) - наиболее надежный источник:
   - `CourtRegion` → `court_region` (например, "11" = Київська область)
   - `INSType` → `instance_type` ("1" = Перша, "2" = Апеляційна, "3" = Касаційна)

2. **Извлеченные метаданные** (`court_name`):
   - Анализ названия суда для определения региона
   - Определение типа инстанции по ключевым словам

### 3. Сохранение характеристик

Сервер сохраняет все доступные характеристики документа:
- **Основные данные**: регистрационный номер, URL, даты
- **Суд**: название суда, регион, тип инстанции
- **Дело**: тип дела, номер дела
- **Судья**: ФИО судьи
- **Решение**: тип решения, дата принятия, дата вступления в силу

## API

### Регистрация документа

```http
POST /api/v1/documents/register
Headers: X-API-Key: YOUR_API_KEY
Body: {
  "task_id": "optional-task-id",
  "search_params": {
    "CourtRegion": "11",
    "INSType": "1"
  },
  "metadata": {
    "external_id": "101476997",
    "reg_number": "101476997",
    "url": "/Review/101476997",
    "court_name": "Київський районний суд",
    "judge_name": "Іванов Іван Іванович",
    "decision_type": "Ухвала",
    "decision_date": "15.01.2024",
    "law_date": "20.01.2024",
    "case_type": "Цивільна справа",
    "case_number": "123/2024"
  }
}
```

**Ответ:**
```json
{
  "system_id": "550e8400-e29b-41d4-a716-446655440000",
  "external_id": "101476997",
  "reg_number": "101476997",
  "classified": true,
  "classification": {
    "court_region": "11",
    "instance_type": "1",
    "source": "search_params"
  },
  "message": "Document registered with system_id: 550e8400-e29b-41d4-a716-446655440000"
}
```

### Получение документа

```http
GET /api/v1/documents/{system_id}
Headers: X-API-Key: YOUR_API_KEY
```

**Ответ:**
```json
{
  "system_id": "550e8400-e29b-41d4-a716-446655440000",
  "id": "101476997",
  "reg_number": "101476997",
  "url": "/Review/101476997",
  "court_name": "Київський районний суд",
  "judge_name": "Іванов Іван Іванович",
  "decision_type": "Ухвала",
  "decision_date": "2024-01-15",
  "law_date": "2024-01-20",
  "case_type": "Цивільна справа",
  "case_number": "123/2024",
  "court_region": "11",
  "instance_type": "1",
  "classification_source": "search_params",
  "classification_date": "2025-01-11T10:30:00Z",
  "download_task_id": "task-uuid",
  "created_at": "2025-01-11T10:30:00Z",
  "updated_at": "2025-01-11T10:30:00Z"
}
```

## Автоматическая регистрация

При использовании распределенной системы (`downloader_client.py`), документы автоматически регистрируются на сервере после загрузки:

1. Клиент получает задачу от сервера
2. Клиент загружает документы
3. После сохранения каждого документа в локальную БД, клиент отправляет метаданные на сервер
4. Сервер регистрирует документ, назначает `system_id` и классифицирует его

## Структура базы данных

### Таблица `documents`

Добавлены новые поля:

- `system_id` (UUID) - Внутренний системный ID
- `court_region` (VARCHAR) - ID региона суда
- `instance_type` (VARCHAR) - Тип инстанции (1, 2, 3)
- `classification_date` (TIMESTAMP) - Дата классификации
- `classification_source` (VARCHAR) - Источник классификации
- `download_task_id` (UUID) - Ссылка на задачу загрузки

### Представления (Views)

- `documents_classified` - Документы с полной классификацией
- `documents_classification_summary` - Статистика по классификации

## Примеры использования

### Регистрация документа через API

```python
from client.api_client import DownloadServerClient

client = DownloadServerClient(
    base_url="https://gate-server.com",
    api_key="YOUR_API_KEY"
)

result = client.register_document(
    metadata={
        "external_id": "101476997",
        "reg_number": "101476997",
        "url": "/Review/101476997",
        "court_name": "Київський районний суд",
        "judge_name": "Іванов Іван Іванович",
        "decision_type": "Ухвала",
        "decision_date": "15.01.2024",
        "case_type": "Цивільна справа"
    },
    task_id="task-uuid",
    search_params={
        "CourtRegion": "11",
        "INSType": "1"
    }
)

print(f"System ID: {result['system_id']}")
print(f"Classified: {result['classified']}")
print(f"Classification: {result['classification']}")
```

### Получение документа

```python
document = client.get_document_by_system_id("550e8400-e29b-41d4-a716-446655440000")
print(f"Court: {document['court_name']}")
print(f"Region: {document['court_region']}")
print(f"Instance: {document['instance_type']}")
```

## Миграция базы данных

Перед использованием необходимо выполнить миграцию:

```bash
psql -h 127.0.0.1 -p 5433 -U reyestr_user -d reyestr_db \
  -f database/migrations/003_add_document_system_id.sql
```

Или через Docker:

```bash
docker exec -i reyestr_db psql -U reyestr_user -d reyestr_db \
  < database/migrations/003_add_document_system_id.sql
```

## Классификация по названию суда

Если параметры поиска недоступны, сервер пытается извлечь информацию из названия суда:

### Регионы

Сервер распознает следующие регионы по ключевым словам в названии суда:
- Київ → "11"
- Львів → "14"
- Одеса → "15"
- Харків → "19"
- Дніпро → "12"
- И другие...

### Типы инстанций

- "апеляційн", "апел" → `instance_type = "2"`
- "касаційн", "касац" → `instance_type = "3"`
- "районн", "міськ", "окружн" → `instance_type = "1"`

## Преимущества

1. **Единая идентификация** - каждый документ имеет уникальный системный ID
2. **Автоматическая классификация** - не требует ручного ввода
3. **Отслеживание источников** - видно, откуда взята классификация
4. **Связь с задачами** - можно отследить, какая задача загрузила документ
5. **Гибкость** - работает как с параметрами поиска, так и без них

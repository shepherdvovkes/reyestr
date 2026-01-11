# Миграции базы данных

## Порядок выполнения миграций

Миграции должны выполняться в следующем порядке:

1. **001_add_distributed_tables.sql** - Базовая структура распределенной системы (клиенты, задачи)
2. **002_add_concurrent_connections.sql** - Поддержка параллельных соединений
3. **003_add_document_system_id.sql** - Системные ID документов и классификация
4. **004_add_client_id_to_documents.sql** - Связь документов с клиентами
5. **005_add_document_download_progress.sql** - Отслеживание прогресса загрузки документов
6. **006_add_users_and_webauthn.sql** - Пользователи и WebAuthn для админ-панели

## Выполнение миграций

### Через psql

```bash
# Выполнить все миграции по порядку
for migration in database/migrations/*.sql; do
    echo "Running $migration..."
    psql -h 127.0.0.1 -p 5433 -U reyestr_user -d reyestr_db -f "$migration"
done
```

### Через Docker

```bash
# Выполнить все миграции по порядку
for migration in database/migrations/*.sql; do
    echo "Running $migration..."
    docker exec -i reyestr_db psql -U reyestr_user -d reyestr_db < "$migration"
done
```

### Выполнить конкретную миграцию

```bash
# Через psql
psql -h 127.0.0.1 -p 5433 -U reyestr_user -d reyestr_db \
  -f database/migrations/005_add_document_download_progress.sql

# Через Docker
docker exec -i reyestr_db psql -U reyestr_user -d reyestr_db \
  < database/migrations/005_add_document_download_progress.sql
```

## Описание миграций

### 001_add_distributed_tables.sql
Создает базовую структуру для распределенной системы:
- `download_clients` - зарегистрированные клиенты
- `download_tasks` - задачи загрузки
- Представления для статистики

### 002_add_concurrent_connections.sql
Добавляет поддержку параллельных соединений (если требуется).

### 003_add_document_system_id.sql
Добавляет системные UUID для документов и классификацию:
- `system_id` - внутренний UUID документа
- `court_region`, `instance_type` - классификация
- `download_task_id` - связь с задачей

### 004_add_client_id_to_documents.sql
Добавляет связь документов с клиентами:
- `client_id` в таблице `documents`
- Представления для статистики клиентов

### 005_add_document_download_progress.sql
Создает таблицу для отслеживания прогресса загрузки:
- `document_download_progress` - отслеживание начала/завершения загрузки документов
- Используется для расчета скорости и ETA

### 006_add_users_and_webauthn.sql
Создает таблицы для админ-панели:
- `users` - пользователи с поддержкой Telegram уведомлений
- `webauthn_credentials` - WebAuthn/FIDO2 учетные данные

## Проверка состояния миграций

Проверить, какие таблицы созданы:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
```

Проверить наличие конкретной таблицы:

```sql
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'document_download_progress'
);
```

## Откат миграций

⚠️ **Внимание**: Эти миграции не содержат автоматического отката. Для отката нужно вручную удалить созданные объекты.

Пример отката миграции 005:

```sql
DROP TABLE IF EXISTS document_download_progress CASCADE;
```

# Руководство по выполнению миграций

## Быстрый старт

### Выполнить все миграции одной командой

```bash
# Используя скрипт
./run_migrations.sh

# Или вручную через psql
for migration in database/migrations/*.sql; do
    psql -h 127.0.0.1 -p 5433 -U reyestr_user -d reyestr_db -f "$migration"
done
```

### Через Docker

```bash
for migration in database/migrations/*.sql; do
    docker exec -i reyestr_db psql -U reyestr_user -d reyestr_db < "$migration"
done
```

## Порядок миграций

Миграции должны выполняться строго в следующем порядке:

1. **001_add_distributed_tables.sql** - Базовая структура (клиенты, задачи)
2. **002_add_concurrent_connections.sql** - Параллельные соединения
3. **003_add_document_system_id.sql** - Системные ID и классификация документов
4. **004_add_client_id_to_documents.sql** - Связь документов с клиентами
5. **005_add_document_download_progress.sql** - Отслеживание прогресса загрузки
6. **006_add_users_and_webauthn.sql** - Пользователи и WebAuthn

## Выполнение отдельных миграций

### Миграция 005: Отслеживание прогресса загрузки

```bash
psql -h 127.0.0.1 -p 5433 -U reyestr_user -d reyestr_db \
  -f database/migrations/005_add_document_download_progress.sql
```

Эта миграция создает:
- Таблицу `document_download_progress` для отслеживания начала/завершения загрузки документов
- Индексы для производительности
- Уникальное ограничение на пару (task_id, document_id)

### Миграция 006: Пользователи и WebAuthn

```bash
psql -h 127.0.0.1 -p 5433 -U reyestr_user -d reyestr_db \
  -f database/migrations/006_add_users_and_webauthn.sql
```

Эта миграция создает:
- Таблицу `users` для пользователей админ-панели
- Таблицу `webauthn_credentials` для WebAuthn/FIDO2 аутентификации
- Поддержку Telegram уведомлений через поле `telegram_chat_id`

## Проверка выполнения миграций

### Проверить наличие таблиц

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
    'download_clients',
    'download_tasks',
    'documents',
    'document_download_progress',
    'users',
    'webauthn_credentials'
)
ORDER BY table_name;
```

### Проверить структуру таблицы

```sql
\d document_download_progress
```

### Проверить индексы

```sql
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'document_download_progress';
```

## Переменные окружения

Можно использовать переменные окружения для настройки подключения:

```bash
export DB_HOST=127.0.0.1
export DB_PORT=5433
export DB_NAME=reyestr_db
export DB_USER=reyestr_user

./run_migrations.sh
```

## Устранение проблем

### Ошибка: "relation already exists"

Если таблица уже существует, миграция использует `CREATE TABLE IF NOT EXISTS`, поэтому это не критично. Можно продолжить.

### Ошибка: "permission denied"

Убедитесь, что пользователь `reyestr_user` имеет права на создание таблиц:

```sql
GRANT ALL PRIVILEGES ON DATABASE reyestr_db TO reyestr_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO reyestr_user;
```

### Ошибка подключения

Проверьте параметры подключения:

```bash
psql -h 127.0.0.1 -p 5433 -U reyestr_user -d reyestr_db -c "SELECT 1;"
```

## Откат миграций

⚠️ **Внимание**: Эти миграции не содержат автоматического отката.

Для отката конкретной миграции нужно вручную удалить созданные объекты:

### Откат миграции 005

```sql
DROP TABLE IF EXISTS document_download_progress CASCADE;
```

### Откат миграции 006

```sql
DROP TABLE IF EXISTS webauthn_credentials CASCADE;
DROP TABLE IF EXISTS users CASCADE;
```

## После выполнения миграций

После успешного выполнения всех миграций:

1. ✅ Таблица `document_download_progress` готова для отслеживания прогресса
2. ✅ Таблица `users` готова для админ-панели и Telegram уведомлений
3. ✅ Все индексы созданы для оптимальной производительности
4. ✅ Система готова к использованию новой функциональности

## Проверка работоспособности

После миграций можно проверить, что все работает:

```python
# Проверить подключение к БД
from server.database.connection import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM document_download_progress")
print(f"Records in document_download_progress: {cur.fetchone()[0]}")
cur.close()
```

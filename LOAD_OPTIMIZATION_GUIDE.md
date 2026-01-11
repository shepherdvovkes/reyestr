# Руководство по оптимизации нагрузки

## Внесенные изменения

### 1. Увеличен пул соединений с БД

**Изменения:**
- `server/config.py` - добавлены настройки `db_pool_minconn` и `db_pool_maxconn`
- `server/database/connection.py` - пул увеличен с 10 до 250 соединений по умолчанию

**Настройка через переменные окружения:**
```bash
export DB_POOL_MINCONN=10    # Минимум соединений в пуле
export DB_POOL_MAXCONN=250   # Максимум соединений (поддержка 10 клиентов × 20 запросов)
```

**Проверка:**
При запуске сервера в логах должно быть:
```
Database connection pool created: min=10, max=250
```

### 2. Добавлен Redis для кэширования

**Изменения:**
- `docker-compose.yml` - добавлен сервис Redis
- `server/database/cache.py` - новый модуль для работы с кэшем
- `server/api/routes.py` - добавлено кэширование для:
  - Списка задач (TTL: 10 секунд)
  - Статистики клиентов (TTL: 30 секунд)
  - Документов (TTL: 60 секунд)
  - Сводки задач (TTL: 10 секунд)

**Запуск Redis:**
```bash
docker-compose up -d redis
```

**Настройка через переменные окружения:**
```bash
export REDIS_HOST=127.0.0.1
export REDIS_PORT=6379
export REDIS_DB=0
export CACHE_ENABLED=true
export CACHE_TTL_TASKS=10        # TTL для задач (секунды)
export CACHE_TTL_STATISTICS=30   # TTL для статистики (секунды)
export CACHE_TTL_DOCUMENTS=60    # TTL для документов (секунды)
```

**Проверка работы кэша:**
```bash
# Подключиться к Redis
docker exec -it reyestr_redis redis-cli

# Посмотреть все ключи кэша
KEYS cache:*

# Очистить весь кэш
FLUSHDB
```

### 3. Автоматический backup/restore БД

**Созданные скрипты:**
- `backup_database.sh` - создание бэкапа БД
- `restore_database.sh` - восстановление из бэкапа

**Создание бэкапа:**
```bash
# Бэкап в директорию ./backups (по умолчанию)
./backup_database.sh

# Бэкап в указанную директорию
./backup_database.sh /path/to/backups

# Бэкапы автоматически сжимаются (gzip)
# Старые бэкапы (старше 30 дней) автоматически удаляются
```

**Восстановление из бэкапа:**
```bash
# Восстановление с подтверждением
./restore_database.sh ./backups/reyestr_db_backup_20240101_120000.sql.gz

# Восстановление без подтверждения (для скриптов)
./restore_database.sh ./backups/reyestr_db_backup_20240101_120000.sql.gz --confirm
```

**Настройка автоматических бэкапов (cron):**
```bash
# Добавить в crontab (ежедневно в 2:00)
crontab -e

# Добавить строку:
0 2 * * * /path/to/reyestr/backup_database.sh >> /var/log/reyestr_backup.log 2>&1
```

**Настройка через переменные окружения:**
```bash
export DB_HOST=127.0.0.1
export DB_PORT=5433
export DB_NAME=reyestr_db
export DB_USER=reyestr_user
export DB_PASSWORD=reyestr_password
```

### 4. Глобальный rate limiting в nginx

**Изменения:**
- `nginx.conf` - добавлены зоны rate limiting:
  - Глобальный лимит: 50 запросов/сек на IP (поддержка 10 клиентов × 20 запросов)
  - Лимит для запросов задач: 10 запросов/сек на IP
  - Лимит для статистики: 5 запросов/сек на IP

**Настройка:**
```nginx
# Глобальный лимит для всех API запросов
limit_req_zone $binary_remote_addr zone=api_global:10m rate=50r/s;

# Лимит для запросов задач
limit_req_zone $binary_remote_addr zone=api_tasks:10m rate=10r/s;

# Лимит для статистики
limit_req_zone $binary_remote_addr zone=api_stats:10m rate=5r/s;
```

**Применение изменений:**
```bash
# Проверить конфигурацию
sudo nginx -t

# Перезагрузить nginx
sudo systemctl reload nginx
# или
sudo nginx -s reload
```

## Проверка работоспособности

### 1. Проверка пула соединений БД

```bash
# Подключиться к БД
psql -h 127.0.0.1 -p 5433 -U reyestr_user -d reyestr_db

# Проверить текущие соединения
SELECT count(*) FROM pg_stat_activity WHERE datname = 'reyestr_db';

# Проверить лимит соединений
SHOW max_connections;
```

**Важно:** Убедитесь, что `max_connections` в PostgreSQL >= `DB_POOL_MAXCONN` (250)

### 2. Проверка Redis

```bash
# Проверить статус Redis
docker ps | grep redis

# Проверить подключение
docker exec -it reyestr_redis redis-cli ping
# Должно вернуть: PONG

# Проверить использование памяти
docker exec -it reyestr_redis redis-cli INFO memory
```

### 3. Проверка кэширования

```bash
# Сделать запрос к API
curl http://localhost:8000/api/v1/tasks

# Проверить кэш в Redis
docker exec -it reyestr_redis redis-cli
KEYS cache:*
GET cache:tasks_summary:all
```

### 4. Проверка rate limiting

```bash
# Быстрые запросы (должны быть ограничены)
for i in {1..100}; do
  curl http://localhost/api/v1/tasks/request &
done

# Проверить логи nginx на наличие ошибок 503 (Too Many Requests)
tail -f /var/log/nginx/reyestr-download-error.log
```

## Настройка PostgreSQL для высокой нагрузки

**Рекомендуемые настройки в `postgresql.conf`:**

```conf
# Увеличить максимальное количество соединений
max_connections = 300

# Оптимизация памяти
shared_buffers = 256MB          # 25% от RAM для небольших серверов
effective_cache_size = 1GB      # 50-75% от RAM
work_mem = 16MB                 # Для сортировок и соединений
maintenance_work_mem = 128MB     # Для операций обслуживания

# Оптимизация запросов
random_page_cost = 1.1          # Для SSD
effective_io_concurrency = 200   # Для SSD

# Логирование медленных запросов
log_min_duration_statement = 1000  # Логировать запросы > 1 секунды
```

**Применить настройки:**
```bash
# В docker-compose.yml добавить volume для postgresql.conf
# или использовать переменные окружения PostgreSQL
```

## Мониторинг

### Метрики для отслеживания

1. **Использование пула соединений:**
   - Количество активных соединений
   - Количество ожидающих запросов

2. **Производительность кэша:**
   - Hit rate (процент попаданий в кэш)
   - Использование памяти Redis

3. **Rate limiting:**
   - Количество заблокированных запросов
   - Ошибки 503 в логах nginx

4. **Производительность БД:**
   - Время выполнения запросов
   - Количество медленных запросов

## Рекомендации

1. **Мониторинг:** Настройте мониторинг для отслеживания:
   - Использования пула соединений
   - Производительности кэша
   - Rate limiting событий

2. **Масштабирование:** При дальнейшем росте нагрузки:
   - Рассмотрите использование connection pooling на уровне приложения
   - Добавьте больше инстансов Redis (Redis Cluster)
   - Используйте read replicas для PostgreSQL

3. **Оптимизация запросов:**
   - Проверьте индексы в БД
   - Оптимизируйте медленные запросы
   - Используйте EXPLAIN ANALYZE для анализа

## Устранение проблем

### Проблема: "FATAL: too many connections"

**Решение:**
1. Увеличить `max_connections` в PostgreSQL
2. Проверить, что `DB_POOL_MAXCONN` не превышает `max_connections`
3. Проверить утечки соединений в коде

### Проблема: Redis не подключается

**Решение:**
1. Проверить, что Redis запущен: `docker ps | grep redis`
2. Проверить настройки подключения: `REDIS_HOST`, `REDIS_PORT`
3. Проверить логи: `docker logs reyestr_redis`

### Проблема: Кэш не работает

**Решение:**
1. Проверить `CACHE_ENABLED=true`
2. Проверить подключение к Redis
3. Проверить логи сервера на ошибки кэша

### Проблема: Rate limiting блокирует легитимные запросы

**Решение:**
1. Увеличить лимиты в `nginx.conf`
2. Добавить whitelist для доверенных IP
3. Настроить разные лимиты для разных эндпоинтов

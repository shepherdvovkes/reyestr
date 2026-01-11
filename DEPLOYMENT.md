# Руководство по деплою на Gate Server

## Требования

- Docker и Docker Compose установлены
- Минимум 2GB RAM
- Минимум 10GB свободного места на диске

## Быстрый старт

### 1. Подготовка

```bash
# Скопировать пример конфигурации
cp .env.example .env

# Отредактировать .env файл с вашими настройками
nano .env
```

### 2. Деплой

```bash
# Запустить все сервисы
./deploy.sh start

# Проверить статус
./deploy.sh status

# Посмотреть логи
./deploy.sh logs
```

## Структура сервисов

### Сервисы в docker-compose.prod.yml:

1. **postgres** - PostgreSQL база данных
   - Порт: 5432 (внутренний)
   - Данные: volume `postgres_data`

2. **redis** - Redis для кэширования
   - Порт: 6379 (внутренний)
   - Данные: volume `redis_data`

3. **api** - FastAPI сервер
   - Порт: 8000 (внутренний)
   - Зависит от: postgres, redis

4. **nginx** - Reverse proxy и load balancer
   - Порт: 80 (HTTP), 443 (HTTPS)
   - Проксирует запросы к API серверу

## Конфигурация

### Переменные окружения (.env)

Основные настройки:

```bash
# База данных
DB_PASSWORD=your_secure_password
DB_POOL_MAXCONN=250

# Redis
CACHE_ENABLED=true
CACHE_TTL_TASKS=10

# Безопасность
ENABLE_AUTH=true

# Nginx порты
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443
```

### Настройка PostgreSQL

После первого запуска PostgreSQL автоматически настроит `max_connections = 300`.

Если нужно изменить вручную:

```bash
docker exec reyestr_db psql -U reyestr_user -d reyestr_db -c "ALTER SYSTEM SET max_connections = 300;"
docker restart reyestr_db
```

### Настройка SSL (HTTPS)

1. Поместите SSL сертификаты в `nginx/ssl/`:
   ```bash
   mkdir -p nginx/ssl
   cp your-cert.pem nginx/ssl/cert.pem
   cp your-key.pem nginx/ssl/key.pem
   ```

2. Раскомментируйте HTTPS секцию в `nginx/nginx.conf`

3. Перезапустите nginx:
   ```bash
   docker restart reyestr_nginx
   ```

## Управление

### Команды деплоя

```bash
# Запустить все сервисы
./deploy.sh start

# Остановить все сервисы
./deploy.sh stop

# Перезапустить все сервисы
./deploy.sh restart

# Показать логи
./deploy.sh logs

# Показать статус
./deploy.sh status
```

### Ручное управление через docker-compose

```bash
# Запустить
docker-compose -f docker-compose.prod.yml up -d

# Остановить
docker-compose -f docker-compose.prod.yml down

# Пересобрать и запустить
docker-compose -f docker-compose.prod.yml up -d --build

# Показать логи
docker-compose -f docker-compose.prod.yml logs -f

# Показать статус
docker-compose -f docker-compose.prod.yml ps
```

## Мониторинг

### Проверка здоровья сервисов

```bash
# API сервер
curl http://localhost/health

# База данных
docker exec reyestr_db pg_isready -U reyestr_user

# Redis
docker exec reyestr_redis redis-cli ping
```

### Логи

```bash
# Все сервисы
./deploy.sh logs

# Конкретный сервис
docker logs reyestr_api -f
docker logs reyestr_db -f
docker logs reyestr_redis -f
docker logs reyestr_nginx -f
```

### Метрики

```bash
# Использование ресурсов
docker stats

# Использование диска
docker system df

# Использование пула соединений БД
docker exec reyestr_db psql -U reyestr_user -d reyestr_db -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'reyestr_db';"
```

## Backup и Restore

### Backup базы данных

```bash
# Внутри контейнера
docker exec reyestr_db pg_dump -U reyestr_user reyestr_db > backup.sql

# Или используя скрипт (из хоста)
./backup_database.sh
```

### Restore базы данных

```bash
# Внутри контейнера
docker exec -i reyestr_db psql -U reyestr_user reyestr_db < backup.sql

# Или используя скрипт (из хоста)
./restore_database.sh backup.sql.gz --confirm
```

## Обновление

### Обновление кода

```bash
# Получить последние изменения
git pull

# Пересобрать и перезапустить
./deploy.sh stop
./deploy.sh start
```

### Обновление зависимостей

```bash
# Обновить requirements.txt
# Затем пересобрать образ
docker-compose -f docker-compose.prod.yml build --no-cache api
docker-compose -f docker-compose.prod.yml up -d api
```

## Масштабирование

### Горизонтальное масштабирование API

```bash
# Запустить несколько инстансов API
docker-compose -f docker-compose.prod.yml up -d --scale api=3

# Nginx автоматически распределит нагрузку
```

### Оптимизация для высокой нагрузки

1. Увеличить количество workers в Dockerfile:
   ```dockerfile
   CMD ["python", "-m", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "8"]
   ```

2. Настроить PostgreSQL для высокой нагрузки (см. `database/postgresql.conf`)

3. Увеличить память Redis:
   ```yaml
   command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
   ```

## Устранение проблем

### Проблема: Контейнер не запускается

```bash
# Проверить логи
docker logs reyestr_api

# Проверить конфигурацию
docker-compose -f docker-compose.prod.yml config
```

### Проблема: База данных недоступна

```bash
# Проверить статус
docker ps | grep reyestr_db

# Проверить логи
docker logs reyestr_db

# Проверить подключение
docker exec reyestr_db pg_isready -U reyestr_user
```

### Проблема: Redis недоступен

```bash
# Проверить статус
docker ps | grep reyestr_redis

# Проверить подключение
docker exec reyestr_redis redis-cli ping
```

### Проблема: Nginx не проксирует запросы

```bash
# Проверить конфигурацию
docker exec reyestr_nginx nginx -t

# Перезагрузить конфигурацию
docker exec reyestr_nginx nginx -s reload
```

## Безопасность

### Рекомендации для продакшена

1. **Изменить пароли по умолчанию** в `.env`
2. **Включить HTTPS** с валидными сертификатами
3. **Ограничить доступ** к портам БД и Redis (не экспортировать наружу)
4. **Настроить firewall** на сервере
5. **Регулярно обновлять** образы Docker
6. **Мониторить логи** на подозрительную активность
7. **Настроить автоматические бэкапы**

### Firewall правила

```bash
# Разрешить только HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Заблокировать прямой доступ к БД и Redis
ufw deny 5432/tcp
ufw deny 6379/tcp
```

## Производительность

### Оптимизация для 10 клиентов × 20 запросов

Система уже настроена для этой нагрузки:

- ✅ Пул соединений БД: 250
- ✅ Redis кэширование: включено
- ✅ Rate limiting: настроен
- ✅ PostgreSQL max_connections: 300

### Дополнительные оптимизации

1. Использовать SSD для volumes
2. Увеличить RAM для PostgreSQL
3. Настроить connection pooling на уровне приложения
4. Использовать read replicas для PostgreSQL

## Поддержка

При возникновении проблем:

1. Проверьте логи: `./deploy.sh logs`
2. Проверьте статус: `./deploy.sh status`
3. Проверьте документацию: `LOAD_OPTIMIZATION_GUIDE.md`
4. Проверьте анализ проблем: `LOAD_ANALYSIS.md`

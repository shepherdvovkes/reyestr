# Быстрый деплой на Gate Server

## Шаг 1: Подготовка

```bash
# Скопировать конфигурацию
cp .env.example .env

# Отредактировать пароли и настройки (опционально)
nano .env
```

## Шаг 2: Деплой

```bash
# Запустить все сервисы одной командой
./deploy.sh start
```

Скрипт автоматически:
- ✅ Создаст необходимые директории
- ✅ Соберет Docker образы
- ✅ Запустит все сервисы (PostgreSQL, Redis, API, Nginx)
- ✅ Настроит PostgreSQL (max_connections = 300)
- ✅ Проверит здоровье сервисов

## Шаг 3: Проверка

```bash
# Проверить статус
./deploy.sh status

# Проверить здоровье API
curl http://localhost/health

# Посмотреть логи
./deploy.sh logs
```

## Готово!

API доступен по адресу: `http://your-server-ip/`

## Полезные команды

```bash
# Остановить все сервисы
./deploy.sh stop

# Перезапустить все сервисы
./deploy.sh restart

# Посмотреть логи в реальном времени
./deploy.sh logs

# Проверить статус
./deploy.sh status
```

## Настройка HTTPS (опционально)

1. Поместите SSL сертификаты в `nginx/ssl/`:
   ```bash
   cp your-cert.pem nginx/ssl/cert.pem
   cp your-key.pem nginx/ssl/key.pem
   ```

2. Раскомментируйте HTTPS секцию в `nginx/nginx.conf`

3. Перезапустите:
   ```bash
   ./deploy.sh restart
   ```

## Структура сервисов

- **PostgreSQL** (порт 5432, внутренний) - база данных
- **Redis** (порт 6379, внутренний) - кэширование
- **API Server** (порт 8000, внутренний) - FastAPI приложение
- **Nginx** (порт 80/443, внешний) - reverse proxy

Все сервисы работают в изолированной Docker сети.

## Подробная документация

См. `DEPLOYMENT.md` для детальной информации.

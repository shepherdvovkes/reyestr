# Быстрый старт распределенной системы

## 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

## 2. Настройка базы данных

Выполните миграцию для создания таблиц:

```bash
# Через psql
psql -h 127.0.0.1 -p 5433 -U reyestr_user -d reyestr_db -f database/migrations/001_add_distributed_tables.sql

# Или через Docker
docker exec -i reyestr_db psql -U reyestr_user -d reyestr_db < database/migrations/001_add_distributed_tables.sql
```

## 3. Запуск сервера

На gate server:

```bash
# Создайте .env файл (опционально)
cat > .env << EOF
DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=reyestr_db
DB_USER=reyestr_user
DB_PASSWORD=reyestr_password
API_HOST=0.0.0.0
API_PORT=8000
ENABLE_AUTH=false
EOF

# Запустите сервер
python downloader_server.py
```

Сервер будет доступен на `http://localhost:8000`

## 4. Создание задачи (пример)

```bash
curl -X POST http://localhost:8000/api/v1/tasks/create \
  -H "Content-Type: application/json" \
  -d '{
    "search_params": {
      "CourtRegion": "11",
      "INSType": "1"
    },
    "start_page": 1,
    "max_documents": 50
  }'
```

## 5. Запуск клиента

На клиентском хосте:

```bash
python downloader_client.py \
    --api-url http://gate-server.com:8000 \
    --output-dir downloaded_documents
```

Если аутентификация включена, добавьте `--api-key YOUR_API_KEY`

## 6. Настройка Nginx (для production)

1. Скопируйте конфигурацию:
```bash
sudo cp nginx.conf.example /etc/nginx/sites-available/reyestr-download-server
```

2. Отредактируйте файл, заменив `your-gate-server.com` на ваш домен

3. Создайте symlink:
```bash
sudo ln -s /etc/nginx/sites-available/reyestr-download-server /etc/nginx/sites-enabled/
```

4. Настройте SSL (Let's Encrypt):
```bash
sudo certbot --nginx -d your-gate-server.com
```

5. Перезагрузите nginx:
```bash
sudo systemctl reload nginx
```

## Проверка работы

### Проверка сервера:
```bash
curl http://localhost:8000/health
```

### Проверка задач:
```bash
curl http://localhost:8000/api/v1/tasks
```

### Проверка клиентов:
```bash
curl http://localhost:8000/api/v1/clients
```

## Примеры использования

### Создать несколько задач для разных страниц:

```bash
for page in {1..10}; do
  curl -X POST http://localhost:8000/api/v1/tasks/create \
    -H "Content-Type: application/json" \
    -d "{
      \"search_params\": {
        \"CourtRegion\": \"11\",
        \"INSType\": \"1\"
      },
      \"start_page\": $page,
      \"max_documents\": 100
    }"
done
```

### Запустить несколько клиентов на разных хостах:

**Host 1:**
```bash
python downloader_client.py --api-url https://gate-server.com --client-name client-1
```

**Host 2:**
```bash
python downloader_client.py --api-url https://gate-server.com --client-name client-2
```

**Host 3:**
```bash
python downloader_client.py --api-url https://gate-server.com --client-name client-3
```

## Troubleshooting

### Сервер не запускается
- Проверьте, что PostgreSQL запущен и доступен
- Убедитесь, что миграция выполнена
- Проверьте логи сервера

### Клиент не подключается
- Проверьте URL сервера
- Убедитесь, что сервер запущен: `curl http://gate-server.com/health`
- Проверьте firewall/network

### Нет задач для обработки
- Создайте задачи через API
- Проверьте статус: `curl http://gate-server.com/api/v1/tasks?status_filter=pending`

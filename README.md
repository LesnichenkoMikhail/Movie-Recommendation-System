## Запуск проекта

1. Скачайте или клонируйте репозиторий проекта.
2. Перейдите в корневую папку проекта.
3. Выполните следующие команды в терминале по очереди:


docker compose up -d db
docker compose --profile etl run --rm etl
docker compose --profile seed run --rm seed
docker compose up -d api ui

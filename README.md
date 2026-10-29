## Запуск проекта

1. Скачайте или клонируйте репозиторий проекта.
2. Перейдите в корневую папку проекта.
3. Выполните следующие команды в терминале по очереди:

1. `docker compose up -d db`
2. `docker compose --profile etl run --rm etl`
3. `docker compose --profile seed run --rm seed`
4. `docker compose up -d api ui`

# Construction CRM

CRM-система для строительной компании на **FastAPI**.

## Стек технологий

| Компонент    | Технология                           |
| ------------ | ------------------------------------ |
| Framework    | FastAPI                              |
| База данных  | PostgreSQL + SQLAlchemy (async)      |
| Миграции     | Alembic                              |
| Аутентификация | JWT (python-jose) + bcrypt          |
| Валидация    | Pydantic v2                          |
| Тесты        | pytest + httpx                       |
| Контейнеры   | Docker / docker-compose              |
| CI           | GitHub Actions                       |

## Структура проекта

```
construction_crm/
├── app/                    # Код приложения
│   ├── core/               # Конфиг, БД, безопасность
│   ├── models/             # SQLAlchemy модели
│   ├── schemas/            # Pydantic схемы
│   ├── crud/               # Операции с БД
│   ├── api/v1/endpoints/   # Эндпоинты
│   └── db/                 # Инициализация БД
├── tests/                  # Тесты
├── alembic/                # Миграции
├── scripts/                # Вспомогательные скрипты
├── .github/workflows/      # CI/CD
├── docker-compose.yml      # Локальный запуск с БД
└── Dockerfile
```

## Быстрый старт

### 1. Клонирование

```bash
git clone <repository-url>
cd construction_crm
```

### 2. Настройка окружения

```bash
cp .env.example .env
# Отредактируйте .env под свои параметры
```

### 3. Запуск через Docker (рекомендуется)

```bash
docker-compose up --build
```

### 4. Локальный запуск (без Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 5. Миграции БД

```bash
alembic revision --autogenerate -m "init"
alembic upgrade head
```

### 6. Тесты

```bash
pytest -v
```

## API документация

После запуска откройте:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Полезные команды

| Команда                          | Описание                   |
| -------------------------------- | -------------------------- |
| `pip install -r requirements.txt` | Установить зависимости    |
| `uvicorn app.main:app --reload`   | Запустить сервер (dev)    |
| `pytest -v`                       | Запустить тесты           |
| `alembic upgrade head`            | Применить миграции        |
| `alembic revision --autogenerate` | Создать новую миграцию    |

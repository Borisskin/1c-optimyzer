# server/ — Optimyzer backend API

Backend для web-кабинета, auth/billing/license activation. Поднимается
независимо от desktop приложения. Деплоится на `api.optimyzer.pro`.

## Стек

- FastAPI + SQLAlchemy 2.x + Alembic
- PostgreSQL в проде, SQLite для dev
- JWT auth (access + refresh)
- Yandex OAuth, YooKassa
- APScheduler — для recurring billing и telemetry cleanup

## Запуск локально

```bash
# из D:\1C-Optimyzer\server\
python -m venv .venv
. .venv/Scripts/activate                  # Windows
pip install -e .[dev]

cp .env.example .env                      # заполнить YANDEX_*, YOOKASSA_* по факту

alembic upgrade head                      # создаст optimyzer.db (SQLite)
uvicorn api.main:app --reload --port 8001
```

OpenAPI docs: http://127.0.0.1:8001/docs

## Тесты

```bash
pytest                                    # все тесты
pytest tests/test_auth.py -v              # только auth
pytest --cov-report=html                  # html coverage в htmlcov/
```

## Структура

| Папка        | Назначение                                                  |
| ------------ | ----------------------------------------------------------- |
| `api/`       | FastAPI app + routers                                       |
| `models/`    | SQLAlchemy модели (User, Subscription, Credits, …)          |
| `schemas/`   | Pydantic схемы запросов/ответов                             |
| `services/`  | Бизнес-логика (Yandex OAuth client, YooKassa, soft caps)    |
| `migrations/`| Alembic                                                     |
| `tests/`     | pytest                                                      |

## Конфигурация

Все настройки через `.env` (см. `.env.example`). Pydantic Settings подтягивает
их в `api.settings.Settings`. В коде — `from api.settings import settings`.

## Деплой (заметка для будущего)

Прод запускается на VDS под systemd unit `optimyzer-api.service`,
nginx reverse-proxy перед uvicorn. Подробности — в Phase 2.x prompt'е.

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

Конфигурация — через единый `.env` в корне репозитория (см. `<repo>/.env.example`).

```bash
# Один раз — скопировать env-шаблон и заполнить:
cp ../.env.example ../.env                # из server/, или прямо в корне

# из D:\1C-Optimyzer\server\
python -m venv .venv
. .venv/Scripts/activate                  # Windows
pip install -e .[dev]

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

Все настройки через единый `.env` в корне репозитория (см. `<repo>/.env.example`).
Pydantic Settings подтягивает их в `api.settings.Settings` через абсолютный путь
(`PROJECT_ROOT/.env` — резолвится один раз при импорте, независимо от cwd).
В коде — `from api.settings import settings`.

## OAuth callback на порту 80 (dev-сетап)

Yandex OAuth app зарегистрирован с `redirect_uri = http://localhost/success`.
Apache (на :80) проксирует `/success` в наш FastAPI на :8001/success.

Apache (httpd.conf):

```apache
ProxyPass /success http://127.0.0.1:8001/success
ProxyPassReverse /success http://127.0.0.1:8001/success
```

Альтернатива nginx (если 80-й заняли nginx-ом):

```nginx
location = /success {
    proxy_pass http://127.0.0.1:8001/success;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

Если хочется без proxy — можно поднимать uvicorn прямо на :80 (Windows
обычно позволяет без admin, на Linux/Mac нужен sudo или setcap CAP_NET_BIND_SERVICE).

## Деплой (заметка для будущего)

Прод запускается на VDS под systemd unit `optimyzer-api.service`,
nginx reverse-proxy перед uvicorn. См. `landing/nginx.conf.example` —
там готовый конфиг с `optimyzer.pro`, `account.optimyzer.pro`, `api.optimyzer.pro`.

# Deploy Checklist — переход с dev на prod

Что НУЖНО изменить когда переходим с локального тестирования на production VDS.
Источник правды для будущих сессий Claude Code — если что-то деплоится,
сначала прочитать этот файл.

## 1. Yandex OAuth (oauth.yandex.ru/client)

| Что | Dev (сейчас) | Production |
|---|---|---|
| Redirect URI | `http://localhost/success` (тест Сергея) | `https://api.optimyzer.pro/success` |
| Тип приложения | Веб-сервисы | Веб-сервисы |
| Permissions | login:email, login:info | login:email, login:info |
| Application name | произвольно | «Optimyzer» |

**Сергей должен сделать в Yandex OAuth admin:**
1. Открыть https://oauth.yandex.ru/client → существующее приложение (ID `4afe5af8633b44c69e1f93a8fc39b537`)
2. В «Redirect URI» **заменить** `http://localhost/success` на `https://api.optimyzer.pro/success`
   (или добавить вторым URI — Yandex поддерживает несколько, удобно держать оба для dev+prod)
3. Сохранить

## 2. Env (root `.env`) — production значения

```env
# General
ENV=production
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0                                  # bind на все интерфейсы за nginx
PORT=8001                                     # nginx проксирует https://api.optimyzer.pro → :8001

# Database — PostgreSQL вместо SQLite!
DATABASE_URL=postgresql+psycopg2://optimyzer:PASSWORD@127.0.0.1:5432/optimyzer

# JWT — сгенерить новый, длинный
JWT_SECRET=<python -c "import secrets; print(secrets.token_urlsafe(64))">

# Yandex OAuth
YANDEX_REDIRECT_URI=https://api.optimyzer.pro/success
YANDEX_CLIENT_SECRET=<из oauth.yandex.ru>

# YooKassa — production credentials (не sandbox!)
YOOKASSA_SHOP_ID=<реальный>
YOOKASSA_SECRET_KEY=<реальный>
YOOKASSA_WEBHOOK_SECRET=<если YooKassa включит подпись>
YOOKASSA_RETURN_URL=https://account.optimyzer.pro/credits?status=pending

# CORS — production домены
CORS_ALLOWED_ORIGINS=https://account.optimyzer.pro,https://optimyzer.pro

# SMTP — реальный почтовик
SMTP_HOST=smtp.yandex.ru
SMTP_PORT=465
SMTP_USE_TLS=true
SMTP_USER=hello@optimyzer.pro
SMTP_PASSWORD=<пароль приложения из Yandex Mail>
SMTP_FROM=Optimyzer <hello@optimyzer.pro>

# Admin (для /v1/admin/*) — сильный пароль
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<random 32+ chars>

# Cookies — HTTPS-only, общий домен
COOKIE_SECURE=true
COOKIE_DOMAIN=.optimyzer.pro                  # точка спереди → шеринг между api. и account.
COOKIE_SAMESITE=lax

# Anthropic — production ключ (отдельный от dev!)
ANTHROPIC_API_KEY=<новый production key>

# Cabinet / Frontend (читаются Vite при build)
VITE_API_BASE=https://api.optimyzer.pro
VITE_CLOUD_API_BASE=https://api.optimyzer.pro
VITE_CABINET_URL=https://account.optimyzer.pro
VITE_LANDING_URL=https://optimyzer.pro
```

## 3. Nginx config

Готовый template — `landing/nginx.conf.example`. Проверить что:
- SSL сертификаты получены через `certbot --nginx -d optimyzer.pro -d www.optimyzer.pro -d account.optimyzer.pro -d api.optimyzer.pro`
- `proxy_pass http://127.0.0.1:8001` для `api.optimyzer.pro`
- `try_files $uri $uri/ /index.html` для cabinet (SPA fallback)
- Static cache headers для landing assets
- `/download` редирект на GitHub Releases

## 4. PostgreSQL setup

```bash
sudo -u postgres psql
CREATE USER optimyzer WITH PASSWORD '...';
CREATE DATABASE optimyzer OWNER optimyzer;
GRANT ALL PRIVILEGES ON DATABASE optimyzer TO optimyzer;
\q

cd /var/www/optimyzer/server
alembic upgrade head
```

## 5. systemd service для uvicorn

`/etc/systemd/system/optimyzer-api.service`:

```ini
[Unit]
Description=Optimyzer FastAPI backend
After=network.target postgresql.service

[Service]
Type=simple
User=optimyzer
WorkingDirectory=/var/www/optimyzer/server
EnvironmentFile=/var/www/optimyzer/.env
ExecStart=/var/www/optimyzer/server/.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8001
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

`systemctl enable --now optimyzer-api`

## 6. APScheduler — включается в production автоматически

В `server/api/main.py` есть startup hook который стартует scheduler **только если ENV=production**:

```python
if settings.env != "production":
    return
from services.scheduler import start
start()
```

Три cron'а: `recurring_billing` (03:00 МСК), `deactivate_expired_credits` (04:00), `telemetry_cleanup` (05:00).

## 7. Cabinet build

```bash
cd /var/www/optimyzer/cabinet
npm ci                            # не install — детерминированно из package-lock.json
npm run build                     # → dist/
# nginx сам отдаёт dist/ как статику
```

## 8. Что НЕ забыть

- [ ] Ротировать **все** dev-ключи (Anthropic, YooKassa sandbox, JWT) перед prod
- [ ] Yandex Метрика — раскомментировать `<script>` в `landing/index.html` и заменить `YOUR_COUNTER_ID`
- [ ] GitHub Releases — выложить первые binary (msi/dmg/AppImage) чтобы `/download` редирект не вёл в 404
- [ ] DNS A-записи: `optimyzer.pro`, `www.optimyzer.pro`, `account.optimyzer.pro`, `api.optimyzer.pro` → IP VDS
- [ ] Проверить что `.env` НЕ закоммитен (только `.env.example` с placeholder'ами)
- [ ] `nginx -t` перед каждым reload
- [ ] Первая тестовая покупка через **production** YooKassa за минимальную сумму (~10 ₽), чтобы проверить весь end-to-end flow + чек 54-ФЗ + поступление денег

# landing/ — Optimyzer лендинг

Статика для `optimyzer.pro`. Скопировано из `DESIGN_CONCEPT/` + заменены
mock-ссылки на реальные (cabinet, GitHub, mailto).

## Файлы

| Файл              | Назначение                                          |
| ----------------- | --------------------------------------------------- |
| `index.html`      | Главная страница (hero, фичи, тарифы, FAQ, footer)  |
| `styles.css`      | Стили (Pulse палитра, общая с cabinet)              |
| `assets/`         | favicon.svg, og-image.png, 9 скриншотов desktop     |
| `robots.txt`      | разрешаем индексацию, sitemap                       |
| `sitemap.xml`     | главные страницы                                    |
| `nginx.conf.example` | пример конфига для деплоя (см. Phase 2.1)        |

## Локальная проверка

```bash
cd landing/
python -m http.server 8000   # или любой static server
```

Открыть http://localhost:8000.

## Деплой (Phase 2.1)

1. Купить domain `optimyzer.pro` у российского регистратора
2. Арендовать VDS, прокинуть DNS A-записи на IP
3. Установить nginx + certbot
4. Скопировать `landing/` → `/var/www/optimyzer/landing/`
5. Скопировать `nginx.conf.example` → `/etc/nginx/sites-available/optimyzer.pro`
   (отредактировать пути, домены)
6. `certbot --nginx -d optimyzer.pro -d www -d account -d api`
7. `nginx -t && systemctl reload nginx`

## Что НЕ забыть перед launch

- [ ] Заменить `YOUR_COUNTER_ID` на реальный ID Yandex.Metrika (в index.html)
- [ ] Раскомментировать `<script>` блок Metrika
- [ ] Заполнить `/docs/` (Phase 2.6) — без них некоторые ссылки в footer ведут в 404
- [ ] Проверить что GitHub Releases содержит binary артефакты (для /download редиректа)
- [ ] Lighthouse audit (Performance > 85, SEO > 90)

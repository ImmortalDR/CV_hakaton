# CC1 · Поверхность поставки

DoD: сервисы, build/image, bind, секреты, тома, health и restart сверены с [compose](../../../compose.yaml), [env](../../../.env.example), [configure](../../../scripts/configure.py). База cf91823; это инвентарь исходного compose, а не конфигурация публичного сервера.

| Сервис / image или build | Host → container | Env / секрет | Том | Health / restart | Для внутреннего контура |
|---|---|---|---|---|---|
| db / postgres:16-alpine, digest закреплён | 127.0.0.1:5547 → 5432 | POSTGRES_USER/DB=fsp; POSTGRES_PASSWORD обязателен | fsp_db → /var/lib/postgresql/data | pg_isready, 3s/3s/30; unless-stopped | Loopback, но публикацию БД лучше убрать; Docker/SSH админ доверенный |
| api / apps/api | нет host port; сеть compose :8000 | DATABASE_URL с паролем; DEMO_MODE, PUBLIC_URL, COOKIE_SECURE; SMTP_* | нет постоянного файлового тома | HTTP /api/health, 5s/4s/20; unless-stopped | Да после false для DEMO_MODE, TLS и SMTP; API ждёт healthy db |
| task-worker / apps/api | нет | DATABASE_URL | нет | healthcheck отсутствует; unless-stopped | Нужен мониторинг scheduler; ждёт healthy api |
| web / apps/web | BIND_ADDRESS (default 127.0.0.1):3080 → 80 | env приложения нет; прокси /api к api:8000 | нет | wget /api/health, 5s/4s/20; unless-stopped | A: private bind; B: loopback за прокси; ждёт healthy api |
| edge / caddy:2.11.7-alpine, digest закреплён | host network; TLS/HTTP listener Caddy (обычно 443/80), не ports compose | HTTPS_HOST, HTTPS_SITE_ADDRESSES, ACME_DIRECTORY | deploy/Caddyfile ro; fsp_tls_data:/data, fsp_tls_config:/config | HTTPS_HOST/api/health, 30s/5s/3, start 30s; unless-stopped | По умолчанию выключен, профиль https; для A/B используем TLS заказчика, не публичный ACME |

Базовое имя проекта `fsp-mvp`; `-p` меняет префикс томов, но **не** фиксированные порты. У томов нет external/name. Dry-run обязан убрать DB host port и заменить web port. Caddy проксирует фиксированный localhost:3080 и не подходит для параллельного dry-run.

API Dockerfile: python:3.12-slim, apt fonts-dejavu-core, pip requirements.lock, USER fsp, alembic upgrade head → seed → uvicorn без access log. Web: node:22-alpine → npm ci/build → nginx:1.28-alpine. Base image теги API/web не закреплены digest; обновление и сканирование — отдельный шлюз заказчика. Nginx ограничивает body 64k, задаёт CSP/антифрейминг; access log по умолчанию включён. Политика ротации Docker-логов в compose отсутствует.

configure создаёт только отсутствующий .env (0600, случайный token_hex(24)), существующий сохраняет. Дефолты — **демо** по HTTP, не рабочие безопасные настройки. DEMO_MODE=false отключает demo login/seed и привязку симуляции ФСП, но не удаляет ранее созданные demo-аккаунты. SMTP обязателен для рабочей регистрации. Скачивание зависимостей разрешено, зеркала выбирает заказчик.

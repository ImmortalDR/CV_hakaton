# Публичный HTTPS-стенд

Адрес: **https://85.137.26.131/**. Используется стандартный порт 443.
HTTP на порту 80 отвечает 308 и перенаправляет на HTTPS.
Порт 3080 — внутренний upstream на `127.0.0.1`, открывать его в браузере
удалённого компьютера больше не нужно.

## Конфигурация

В `compose.yaml` добавлен необязательный профиль `https` с отдельным Caddy
2.11.7, закреплённым по digest. Конфигурация — `deploy/Caddyfile`.
Для данного Linux-сервера используется `network_mode: host`: Caddy слушает
80/443 и обращается к `127.0.0.1:3080`. Административный API Caddy выключен.
База и API не получают новых внешних портов.

В существующем `.env` установлены следующие несекретные параметры:

```dotenv
COMPOSE_PROFILES=https
HTTPS_HOST=85.137.26.131
PUBLIC_URL=https://85.137.26.131
COOKIE_SECURE=true
BIND_ADDRESS=127.0.0.1
```

Пароль БД и остальные настройки сохраняются. Без профиля `https` новый
локальный запуск по-прежнему использует HTTP на localhost:3080 и
COOKIE_SECURE=false. Для другого публичного IP нужно заменить HTTPS_HOST
и PUBLIC_URL. Порты 80/443 должны быть свободны и доступны из Интернета.

```bash
docker compose config --quiet
docker compose run --rm --no-deps edge caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
docker compose up -d --no-deps --wait api web edge
curl --fail https://85.137.26.131/api/health
docker compose ps
docker compose logs --tail=30 edge
```

Сертификат выпущен публичным Let's Encrypt с профилем `shortlived`.
Caddy управляет автоматическим продлением; отдельный cron не требуется.
Ключи и состояние ACME хранятся в новых томах `fsp-mvp_fsp_tls_data` и
`fsp-mvp_fsp_tls_config`, вне Git. Эти тома нужно сохранять при обновлениях.
Текущий сертификат: issuer Let's Encrypt YE1, SAN IP Address:85.137.26.131,
окончание действия 2026-10-14 13:50:07 UTC. Будущее продление ещё не наступило;
наличие конфигурации продления не выдаётся за выполненный renewal-тест.
В логах подтверждены получение ARI и запуск фонового обслуживания сертификатов.

Документация: [IP-сертификаты Let's Encrypt](https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability),
[ACME profile в Caddy](https://caddyserver.com/docs/caddyfile/directives/tls#issuers).

## Выполненные проверки, 2026-10-07 22:49–22:51 UTC

- `docker compose config --quiet` и `caddy validate` — успешно.
- Сначала успешно выпущен staging-сертификат, затем отдельный доверенный
  production-сертификат. HTTP-01 проверен серверами Let's Encrypt извне.
- `curl --fail https://85.137.26.131/api/health` — HTTP 200, `status=ok`.
  Проверка доверия TLS включена, флаг `-k` не использовался.
- Python `ssl.create_default_context()` подтвердил цепочку и IP в SAN,
  соединение TLS 1.3.
- Chromium через Playwright, без `ignore_https_errors`: HTTP → HTTPS,
  загрузка приложения, демовход кандидата и работодателя, проверка роли через
  `/api/auth/me`, выход и последующий 401. В обеих сессиях cookie имеют
  Secure, HttpOnly, SameSite=Lax; ошибок JavaScript нет.
- Внешние GET `/api/health` через Globalping из Buffalo (US), Sao Paulo (BR)
  и Lagos (NG) вернули HTTP 200 с ожидаемым JSON. Measurement:
  `2EZDCw0GRcpifGZ6A00021H8k`. Эти пробы подтверждают сетевую доступность.
  Globalping отдельно сообщил `ERR_TLS_CERT_ALTNAME_INVALID` для IP-цели;
  его TLS-результат не засчитывается как успешная проверка сертификата.
  Доверие сертификату независимо подтверждено curl, Python SSL и Chromium.
- API, БД и edge имеют статус healthy. Все семь контейнеров
  `intellect-org-os` остались остановленными; их ресурсы не изменялись.

Первый запрос Globalping использовал HEAD и получил 405: health поддерживает
GET. Повторная проверка явно использовала GET, результат указан выше.
Исходные отчёты и снимки браузера сохранены локально в `audit/current/https/`
и `local-backups/https-external-*.json`. Значения cookie в отчёты не включены.

Первопричина недоступности порта 3080 из сети пользователя не установлена:
локальная проверка этого порта не доказывала внешнюю доступность. Новый вход
через 443 проверен независимыми внешними узлами. Проверки именно из сети
пользователя и в его Firefox не выполнялись.

Для отключения только этого HTTPS-прокси: `docker compose stop edge`.
Сохранённый проект `intellect-org-os` автоматически не запускается.

# Публичный HTTPS-стенд

Адрес: **https://85-137-26-131.sslip.io/**. Используется стандартный порт 443.
HTTP на порту 80 отвечает 308 и перенаправляет на HTTPS.
Прежний адрес `https://85.137.26.131/` отвечает 301 и перенаправляет на домен,
сохраняя путь и query string. DNS домена указывает на `85.137.26.131`.
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
HTTPS_HOST=85-137-26-131.sslip.io
HTTPS_SITE_ADDRESSES=85-137-26-131.sslip.io, 85.137.26.131
PUBLIC_URL=https://85-137-26-131.sslip.io
COOKIE_SECURE=true
BIND_ADDRESS=127.0.0.1
```

Пароль БД и остальные настройки сохраняются. Без профиля `https` новый
локальный запуск по-прежнему использует HTTP на localhost:3080 и
COOKIE_SECURE=false. Для другого публичного домена/IP нужно заменить HTTPS_HOST
и PUBLIC_URL. HTTPS_SITE_ADDRESSES необязателен: по умолчанию равен HTTPS_HOST;
при указании перечисляет основной адрес и алиасы через запятую. Для каждого
адреса Caddy получает/обновляет сертификат, алиасы перенаправляет на HTTPS_HOST.
Порты 80/443 должны быть свободны и доступны из Интернета.

```bash
docker compose config --quiet
docker compose run --rm --no-deps edge caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
docker compose up -d --no-deps --force-recreate --wait api web edge
curl --fail https://85-137-26-131.sslip.io/api/health
docker compose ps
docker compose logs --tail=30 edge
```

Сертификат выпущен публичным Let's Encrypt с профилем `shortlived`.
Caddy управляет автоматическим продлением; отдельный cron не требуется.
Ключи и состояние ACME хранятся в новых томах `fsp-mvp_fsp_tls_data` и
`fsp-mvp_fsp_tls_config`, вне Git. Эти тома нужно сохранять при обновлениях.
Web пересоздаётся вместе с API, чтобы nginx разрешил актуальный адрес API
после смены контейнера. Том БД и накопленные данные сохраняются.

Текущий сертификат домена: issuer Let's Encrypt YE2,
SAN DNS:85-137-26-131.sslip.io, окончание действия 2026-10-15 04:04:12 UTC.
Сертификат IP сохранён для перенаправления. Будущее продление ещё не наступило;
наличие конфигурации продления не выдаётся за выполненный renewal-тест.
В логах подтверждены получение ARI и запуск фонового обслуживания сертификатов.

Документация: [IP-сертификаты Let's Encrypt](https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability),
[ACME profile в Caddy](https://caddyserver.com/docs/caddyfile/directives/tls#issuers).

## Проверка домена, 2026-10-08 13:02–13:05 UTC

- `docker compose config --quiet` и `caddy validate` — успешно.
- Доверенный сертификат домена получен через production ACME; внешние
  TLS-ALPN-01 проверки Let's Encrypt завершились успешно.
- `curl --fail` и Python `ssl.create_default_context()` — HTTP 200 / TLS 1.3,
  корректный SAN и доверенная цепочка. Проверка сертификата не отключалась.
- Chromium / Playwright: HTTP → HTTPS, оба демовхода, правильные роли через
  `/api/auth/me`, Secure + HttpOnly + SameSite=Lax, выход → 401,
  ошибок JavaScript нет. HTTPS по прежнему IP перенаправляет на домен;
  путь и query string сохранены.
- Внешние GET `/api/health` через Globalping из Tokyo (JP), Helsinki (FI),
  Sydney (AU): все три HTTP 200 и `tls.authorized=true`.
  Measurement: `2rvsfsIu8c52x0KgR00021HMV`.
- В API установлен новый PUBLIC_URL и COOKIE_SECURE=true. API, БД, edge —
  healthy; web работает. Семь контейнеров `intellect-org-os` остаются stopped.

Отчёты TLS, браузера, внешних проб и снимки экранов:
`audit/current/https-domain/` (локально, без значений cookie).
Это проверка развёртывания и авторизации; предметная логика приложения
не менялась, полный набор её тестов повторно не запускался.

## История: проверка IP, 2026-10-07 22:49–22:51 UTC

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

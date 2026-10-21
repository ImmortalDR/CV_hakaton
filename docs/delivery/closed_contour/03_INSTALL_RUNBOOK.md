# CC3 · Установка у заказчика

DoD: Linux → configure → build → up → health → API → откат. Два варианта A/B ниже. Скачивание зависимостей **разрешено** (deps download = allowed). Это не air-gap. Фактический прогон — CC4; установка на инфраструктуре заказчика, SMTP и TLS заказчика пока NOT_RUN.

## 1. Подготовить отдельную VM

Ubuntu 24.04 LTS или совместимый Debian/Linux с systemd. План пилота: 4 vCPU, 8 GiB RAM, 30 GiB свободного SSD; это исходная оценка, не измеренный SLA. Администратор устанавливает Git, Python 3, curl, tar, Docker Engine и Compose v2 из одобренного репозитория; проверяет `docker version`, `docker compose version` (на прогоне 2.40.3). Членство в docker-группе эквивалентно высоким привилегиям. Не устанавливать рядом с боевым демо без выделения ресурсов.

Разрешить исходящие DNS/HTTPS к выбранным Git/registry/apt/pip/npm зеркалам; runtime нужен SMTP заказчика (обычно STARTTLS 587). Образы берутся из Docker Hub, API ставит apt/pip, web выполняет npm ci. Proxy/CA/зеркала согласует ИТ заказчика; скачивание зависимостей само по себе не требует отправки резюме. Не отключать проверку TLS ради зеркала.

Вход: HTTPS 443 к прокси; 3080 только из доверенной LAN/от прокси; SSH только админам. БД :5547 только loopback базового compose; API :8000 только сеть Docker. Запретить доступ к 5547 извне и от непривилегированных локальных пользователей. Учесть Docker firewall, проверить фактические listeners, не полагаться только на UFW.

## 2. Получить отдельную копию и секреты

```bash
git clone --branch codex/closed-contour-readiness https://github.com/ImmortalDR/CV_hakaton.git fsp-customer
cd fsp-customer
git rev-parse HEAD
python3 scripts/configure.py
chmod 600 .env
```

Зафиксировать SHA поставки в журнале изменений. Если ветка ещё не отправлена — получить от команды git bundle/архив именно этого SHA. Не копировать .env и том демо. В защищённом редакторе задать в .env: `DEMO_MODE=false`, настоящий `PUBLIC_URL=https://<имя-сервиса>`, `COOKIE_SECURE=true`, `SMTP_HOST`, `SMTP_PORT=587`, `SMTP_TLS=true`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`. Сгенерированный POSTGRES_PASSWORD сохранить. PUBLIC_URL влияет на ссылки в письмах, COOKIE_SECURE — на cookie. Удалить/не задавать COMPOSE_PROFILES=https; встроенный edge не требуется.

## 3. Выбрать доступ

**A — внутренняя сеть / private bind.** `BIND_ADDRESS=<IPv4 интерфейса внутренней сети VM>`; не `0.0.0.0`. Для рабочих ПДн внутренний TLS-прокси с сертификатом корпоративного УЦ публикует `PUBLIC_URL` и обращается к private-IP:3080; firewall разрешает 3080 только ему. Если клиенты ходят прямо по HTTP в LAN, это допускается только для синтетической проверки с COOKIE_SECURE=false; такой режим не принимается для рабочих данных. Сервис не требует доступа из интернета.

**B — за reverse-proxy заказчика.** Прокси на той же VM: `BIND_ADDRESS=127.0.0.1`, upstream `http://127.0.0.1:3080`. Удалённый прокси: private bind как A и ACL только на его IP; loopback недоступен с другой машины. Прокси терминирует TLS, сохраняет Host, передаёт доверенные X-Forwarded-*; не доверять заголовкам внешнего клиента. Политику real IP и rate limit проверить отдельно: nginx приложения не передаёт X-Forwarded-For, поэтому текущий API может видеть адрес nginx для всех клиентов. Ограничения body, timeouts и access-log с фильтрацией секретов задаёт заказчик. Внешняя доступность определяется его периметром.

## 4. Собрать и запустить свой проект

На новой VM имя проекта ниже закрепляется за этой установкой. Не запускать эти команды в каталоге другого стенда. Порты 3080/5547 должны быть свободны; иначе остановиться и согласовать другой конфиг, не останавливать чужие контейнеры.

```bash
unset COMPOSE_FILE COMPOSE_PROJECT_NAME COMPOSE_PROFILES
docker compose --env-file .env -p fsp-customer -f compose.yaml config --quiet
docker compose --env-file .env -p fsp-customer -f compose.yaml build
docker compose --env-file .env -p fsp-customer -f compose.yaml up -d --wait --wait-timeout 180 db api task-worker web
docker compose --env-file .env -p fsp-customer -f compose.yaml ps
```

Первый старт API выполняет Alembic и отключённый seed. Для варианта A health проверять по private-IP:3080; для B локального — по 127.0.0.1:3080:

```bash
curl --fail --max-time 10 http://127.0.0.1:3080/api/health
curl --fail --max-time 10 http://127.0.0.1:3080/api/catalog
```

Ожидается `status=ok`, `demo=false`. Далее с клиентской машины проверить HTTPS через доверенный корпоративный CA, регистрацию обеих ролей/письмо/вход, отсутствие demo login, актуальные ACL и PDF, отсутствие публичной БД. Это приёмка заказчика HUMAN/NOT_RUN, а не результат локального dry-run. Чистый .env=false не удаляет demo-данные из старого тома: всегда новая БД.

## 5. Backup, обновление, откат

Перед обновлением: зафиксировать текущий SHA и образы, остановить записи (web/API/worker в окно обслуживания), снять `pg_dump -Fc -U fsp fsp` через `docker compose ... exec -T db`; сохранить stdout в защищённый файл вне git, проверить восстановление в отдельную БД. Команда `...` здесь означает тот же набор `--env-file .env -p fsp-customer -f compose.yaml`; не использовать имя публичного проекта. Согласовать RPO/RTO и срок копий. Не копировать работающий каталог PGDATA как полноценный backup.

Остановить только свою установку:

```bash
docker compose --env-file .env -p fsp-customer -f compose.yaml down
```

Том сохраняется. Откат приложения: отдельный checkout предыдущего SHA, пересборка/зафиксированные образы; совместимость миграций не гарантирована — при несовместимости восстановить предобновленческий dump в новый том и переключить сервис в окно обслуживания. Backup/restore здесь инструкция, NOT_RUN до отдельной репетиции; `down -v` для рабочих данных не применять. Удаление одноразового тестового тома делает только скрипт CC4 своего уникального проекта.

## 6. Репетиция без чужих данных

`bash scripts/closed_contour_dry_run.sh` создаёт временную копию исходников из HEAD, запускает configure, строит отдельные images/containers/network/volume, использует случайный loopback web port без публикации БД, проверяет health/API и удаляет только свой проект. Лог — `evidence/cc-dry-run-*.log`. TLS/SMTP/backup и внешний доступ A/B этот локальный прогон не доказывает.

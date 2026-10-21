# Протокол агента · закрытый контур · 2026-10-21

## W0

Рабочий каталог `/root/hakaton-contour`, ветка `codex/closed-contour-readiness`, исходный HEAD `cf91823219e76974a688e8c74f8d3f15dce54e84`.
Основной клон: `/root/hakaton`, ветка `main`, HEAD `ffd9e05806a727dc7c6706582b375a1021e6ec83`, грязный WIP сохранён.
Полный stdout pwd / branch / HEAD / status обоих деревьев: [w0-state.txt](evidence/w0-state.txt).
`git merge-base --is-ancestor codex/fsp-mvp HEAD`: exit 0. Worktree уже существовал. Docker Compose 2.40.3; свободно 47 GiB.
Не использовались reset, stash, force-push; публичный compose не запускался.

## Границы ревью

Трек ограничен CC по прямому указанию пользователя. Исходные PDF/PPTX, созвоны, весь корпус сторонних репозиториев и Stage A не перечитывались; полный аудит MVP не заявлен. Бинарные материалы не изменены и не осматривались в этом треке. WORKSPACE_MAP и REVIEW_PROTOCOL прочитаны; старые матрица/brief/audit/acceptance просмотрены как контекст (часть общего вывода усечена, полное чтение не заявляется).
Содержательно прочитаны канон, backlog, verify-by-task, старт/runbook трека, шаблон human, compose, env.example, configure, Dockerfile API/web, nginx, Caddyfile, models, schemas, outputs, main (частями), pdf, tasks, task_worker, seed, fsp_provider, git workflow и ignore.

### Проход 1 — устройство

Compose: PostgreSQL, API, worker, nginx; edge opt-in https с host network. Секреты генерируются configure, root .env не отслеживается. DEMO_MODE по умолчанию true в compose: для рабочих данных нужен отдельный чистый проект и false. PDF создаётся в памяти из проекции.

### Проход 2 — связи и границы

Вход nginx → API → PostgreSQL; worker использует ту же БД. API запуск мигрирует и вызывает seed, который проверяет DEMO_MODE. Проекция проверяет owner/company grant и publication; PDF использует ту же проекцию. Snapshot сохраняет оценки, при чтении контакты проецируются заново. Отзыв публикации удаляет grants, приостанавливает задания, но не удаляет пользователя/историю. SMTP выносит email и ссылку во внешнюю систему; HTTP access log nginx способен сохранить URI с идентификаторами. Срок хранения записей не равен сроку годности токена.

### Проход 3 — отрицательные сценарии и DoD CC

Один -p недостаточен для параллельной установки: фиксированные host ports конфликтуют. Нужен производный compose без edge, без host DB port и с динамическим web bind на loopback. Запрещены внешние/фиксированные имена томов и наследование COMPOSE_PROFILES/FILE/PROJECT из shell. Dry-run только синтетический, без SMTP. Недостатки рабочего внедрения: нет удаления аккаунта/retention, полноценных audit trail, MFA/SSO, распределённого rate limit и доказанной политики backup. Они документируются, не превращаются в Stage A правки.

Автоматические проверки и выполненные тесты ниже отделены от этих выводов чтения. Отсутствие теста означает NOT_RUN, а не PASS безопасности.

## W1 → W2

CC0–CC2: артефакты созданы, отдельные коммиты. CC3 первоначально PARTIAL: runbook написан, ожидает CC4 install smoke. В исходном каноне `git diff --check` сообщает Markdown hard-break пробелы; канон сохранён без нормализации. Новые файлы проверяются отдельно.

## W2 завершение

CC4: `bash scripts/closed_contour_dry_run.sh`, exit 0. Полный лог: [cc-dry-run-20261021T185211Z-233571.log](evidence/cc-dry-run-20261021T185211Z-233571.log).
SHA256 исполненного скрипта: `d4d7ba393a71ffc3e9cb57c19b6ea946843315ace202154e9761498eb3d90168`. Source HEAD в логе b0a4c77; исходники приложения с базы cf91823 не менялись.

```text
API /api/health HTTP 200 expected=200
health ok; demo=false
API /api/catalog HTTP 200 expected=200
API /api/openapi.json HTTP 200 expected=200
API /api/me/profile HTTP 401 expected=401
API /api/auth/demo HTTP 404 expected=404
API /api/auth/demo HTTP 403 expected=403
minimum API and negative access checks passed
worker process ok
cleanup verified: no project containers or volumes
EXIT_CODE=0
```

CC3 PARTIAL → PASS: configure/build/up/health/API/down прошли в изолированной копии. Customer TLS/SMTP, backup/restore и сетевые A/B остаются NOT_RUN, указаны в runbook. Контейнеры/том удалены; build cache и уникальные images оставлены (без runtime .env), глобальный prune не выполнялся.
CC5: [hygiene](evidence/config-hygiene.txt), [отрицательные контроли и mode 0600](evidence/config-negative-controls.txt). CC1: [сверка bind/DEMO/profile/тома](evidence/inventory-crosscheck.txt).

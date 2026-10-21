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

## W3–W5: содержательная проверка артефактов

CC6: 10 угроз, доверенные зоны и активы; проверены источник/дыра/владелец каждой строки. Наличие middleware rate-limit не названо DDoS-защитой. CC7: явно not_implemented, у reverse-proxy цепочка client IP не подтверждена. CC8: 15 пунктов, выполнены env-ignore/placeholder, configure 0600/repeat и loopback/DEMO=false smoke; customer чекбоксы пустые.
CC9: каждая техническая строка с кодом, правовые решения LEGAL_REVIEW_NEEDED. Browser search/open использован для нормативного ориентира: копия 152-ФЗ Минобрнауки ред. 24.06.2025 открылась; страница Минтруда timeout; Росгвардия содержит старую редакцию, не использована как актуальное правовое заключение. Полный правовой аудит и актуальность на дату пилота не подтверждены. CC10: нет отдельного поля ожиданий зарплаты; есть вилка приглашения. CC11: DEMO_MODE не анонимизирует ввод; FOR_JURY уже запрещает реальные ПДн. CC12: onepager разделяет доказанное/NOT_RUN, без договорных гарантий. CC13: ровно один добавленный абзац в FOR_JURY. CC14: 162 слова с заголовком, чтение вслух NOT_RUN.

## W6: независимая сверка внутри текущей сессии (без субагентов)

Команды:

```bash
python3 scripts/verify_closed_contour_artifacts.py
python3 scripts/check_closed_contour_config.py
bash -n scripts/closed_contour_dry_run.sh
```

Результаты: все три exit 0. Полный stdout первой команды: [artifact-checks.txt](evidence/artifact-checks.txt); второй — [config-hygiene.txt](evidence/config-hygiene.txt), третья stdout не имеет. Это автоматическая структурная проверка, не функциональная регрессия всего MVP. Верификатор дополнительно подтверждает SHA256 исполненного скрипта и отсутствие изменений apps/compose/env.example/configure/deploy относительно cf91823. Скрипт dry-run исполнялся до его коммита, но точный hash сохранён выше; исходники приложения после прогона не менялись.

Слабое место runbook при повторном чтении: слишком общая установка инструментов и сокращённая backup-команда. В W6 добавлены конкретные apt-команды для чистой Ubuntu и полный пример pg_dump без ellipsis. Их исполнение на VM заказчика/restore честно NOT_RUN; текущий Docker хоста не переустанавливался.

### CCV3 — PARTIAL

`curl --silent --show-error --fail --max-time 20 --write-out ... https://85-137-26-131.sslip.io/api/health`: exit 0, HTTP 200, `{"status":"ok","demo":true,"version":"1.0.0"}`. [Полный вывод](evidence/public-health.txt).
Основной клон в W0 был на main; в W6 — fix/jury-single-window с тем же HEAD и дополнительными изменениями. Первая автоматическая попытка потребовать точное совпадение status завершилась AssertionError — это выявленное параллельное изменение, не скрытый PASS. [Diff](evidence/main-concurrent-diff.txt), [состояние](evidence/main-final-state.txt). Отдельная проверка множеств строк status: все начальные modified/untracked пути остаются. С нашей стороны основной клон только читался, reset/stash/checkout/force-push там не выполнялись; побайтовая сохранность чужих файлов не доказана, оставлена владельцу. Публичные контейнеры не пересобирались и их тома не использовались.

### CCV2 — HUMAN_ONLY

[Протокол](HUMAN_VERIFY_PROTOCOL_CLOSED_CONTOUR.md) создан по исходному шаблону с датой и evidence. Галочки ★, юридическое принятие, готовность произнести pitch, сеть/TLS/SMTP заказчика, restore и подтверждение WIP остаются человеку. Отсутствие ответов не считается согласием. Push не выполнен: канон относит его к человеческой фазе H. Локальная ветка содержит отдельные коммиты по must-задачам.

### Ограничения проверки

Не запускались: общий pytest/browser suite MVP, пентест/DDoS, полный image scan, customer A/B routing и CA, SMTP заказчика, backup/restore, юридический аудит. Не менялись приложения и исходные подборки. Наличие npm ci строки «0 vulnerabilities» в логе не принимается за аудит всех компонентов. Raw dry-run stdout сохранён без нормализации; diff --check у raw log и исходного канона сообщает trailing whitespace, в новых authored code/docs таких ошибок нет (шаблон human сохраняет Markdown breaks).

## Доказательства по каждой must-задаче

Ниже выдержки новых артефактов (6–10 строк); дополняют полный лог и автоматические результаты, не заменяют чтение файла.

### CC1 · PASS

`docs/delivery/closed_contour/01_INVENTORY.md`

```text
# CC1 · Поверхность поставки

DoD: сервисы, build/image, bind, секреты, тома, health и restart сверены с [compose](../../../compose.yaml), [env](../../../.env.example), [configure](../../../scripts/configure.py). База cf91823; это инвентарь исходного compose, а не конфигурация публичного сервера.

| Сервис / image или build | Host → container | Env / секрет | Том | Health / restart | Для внутреннего контура |
|---|---|---|---|---|---|
| db / postgres:16-alpine, digest закреплён | 127.0.0.1:5547 → 5432 | POSTGRES_USER/DB=fsp; POSTGRES_PASSWORD обязателен | fsp_db → /var/lib/postgresql/data | pg_isready, 3s/3s/30; unless-stopped | Loopback, но публикацию БД лучше убрать; Docker/SSH админ доверенный |
| api / apps/api | нет host port; сеть compose :8000 | DATABASE_URL с паролем; DEMO_MODE, PUBLIC_URL, COOKIE_SECURE; SMTP_* | нет постоянного файлового тома | HTTP /api/health, 5s/4s/20; unless-stopped | Да после false для DEMO_MODE, TLS и SMTP; API ждёт healthy db |
| task-worker / apps/api | нет | DATABASE_URL | нет | healthcheck отсутствует; unless-stopped | Нужен мониторинг scheduler; ждёт healthy api |
| web / apps/web | BIND_ADDRESS (default 127.0.0.1):3080 → 80 | env приложения нет; прокси /api к api:8000 | нет | wget /api/health, 5s/4s/20; unless-stopped | A: private bind; B: loopback за прокси; ждёт healthy api |
```

### CC2 · PASS

`docs/delivery/closed_contour/02_DATA_MAP.md`

```text
# CC2 · Карта данных

DoD: сущности → поля → назначение → хранение → удаление. Источник всех таблиц БД — [models.py](../../../apps/api/fsp/models.py); ограничения входа — [schemas.py](../../../apps/api/fsp/schemas.py), выходы — [outputs.py](../../../apps/api/fsp/outputs.py). Это перечень технических фактов, не юридическая классификация.

| Сущность / группа | Поля и назначение | Хранение: факт / предложение | Удаление: факт |
|---|---|---|---|
| User, ПДн/аутентификация | email, password_hash Argon2, role, verified, demo, created_at; вход | PostgreSQL, бессрочно до админоперации; предложено утвердить срок у оператора | API удаления аккаунта нет |
| Session, Verification, PasswordReset, технические | token_hash, user_id, expires_at, used; доступ и восстановление | Валидность 1 день / 1 час / 30 минут в [main](../../../apps/api/fsp/main.py), это не срок удаления строк | logout удаляет текущую session; reset все sessions; TTL cleanup нет |
| Profile, ПДн/профессиональные | name, phone, about, roles, soft_skills, skills, experience_years, industry, specialization; самодекларация; claimed/verified_grade, verified_attempt_id, grade_changed_at | БД, общего retention нет; предложено хранить по цели найма и согласованному сроку | редактирование/снятие публикации есть, физического удаления нет |
| Profile, ФСП | fsp_identity, achievements JSON | DemoProvider, симуляция, [provider](../../../apps/api/fsp/fsp_provider.py) | unlink очищает эти поля; не весь профиль |
```

### CC3 · PASS

`docs/delivery/closed_contour/03_INSTALL_RUNBOOK.md`

```text
# CC3 · Установка у заказчика

DoD: Linux → configure → build → up → health → API → откат. Два варианта A/B ниже. Скачивание зависимостей **разрешено** (deps download = allowed). Это не air-gap. Фактический прогон — CC4; установка на инфраструктуре заказчика, SMTP и TLS заказчика пока NOT_RUN.

## 1. Подготовить отдельную VM

Ubuntu 24.04 LTS или совместимый Debian/Linux с systemd. План пилота: 4 vCPU, 8 GiB RAM, 30 GiB свободного SSD; это исходная оценка, не измеренный SLA. Администратор устанавливает Git, Python 3, curl, tar, Docker Engine и Compose v2 из одобренного репозитория; проверяет `docker version`, `docker compose version` (на прогоне 2.40.3). Членство в docker-группе эквивалентно высоким привилегиям. Не устанавливать рядом с боевым демо без выделения ресурсов.

Пример установки инструментов для чистой Ubuntu 24.04 через её одобренное apt-зеркало (на VM заказчика, не на публичном стенде):

```

### CC4 · PASS

`docs/delivery/closed_contour/evidence/cc-dry-run-20261021T185211Z-233571.log`

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

### CC5 · PASS

`docs/delivery/closed_contour/04_SECRETS_AND_CONFIG.md`

```text
# CC5 · Секреты и конфигурация

DoD: checklist + исполняемая проверка [check_closed_contour_config.py](../../../scripts/check_closed_contour_config.py). Запуск: `python3 scripts/check_closed_contour_config.py`. Проверяет индекс git, ignore и допустимые placeholder-значения .env.example; не заменяет сканирование всей истории git.

| Проверка | Действие / владелец |
|---|---|
| ☐ Новый секрет БД | `python3 scripts/configure.py`, файл 0600; не переносить секрет демо. Админ |
| ☐ Существующий .env | configure сохраняет; сверить значения в защищённом редакторе. Не печатать в лог |
| ☐ DEMO_MODE=false | Чистая рабочая БД; false не удаляет синтетику из старой БД. Админ |
| ☐ PUBLIC_URL | Доступный пользователям HTTPS URL, без лишнего path; проверить ссылки в письмах |
```

### CC6 · PASS

`docs/delivery/closed_contour/05_THREAT_MODEL.md`

```text
# CC6 · Модель угроз для пилота

DoD: активы, доверенные зоны, ≥6 угроз, существующие меры/дыры/владелец. Оценка основана на чтении кода; пентест и нагрузочная атака NOT_RUN. PASS документа не означает отсутствие уязвимостей.

Активы: профили/контакты, согласия, ответы/эталоны и результаты тестов, задания компаний, сессии/SMTP/DB credentials, backup. Зоны доверия: браузер недоверенный → TLS/периметр заказчика → nginx → API/worker → PostgreSQL. Отдельные границы: SMTP, registry/pip/npm/apt при сборке, администратор Docker/SSH и получатель скачанного PDF. Docker network не защищает от администратора хоста.

| Угроза | Уже есть, источник | Дыра / остаточный риск | Кто закрывает |
|---|---|---|---|
| Чужой работодатель читает контакты/API/PDF/старый поиск | [main projection/snapshot_view/pdf](../../../apps/api/fsp/main.py): owner/company grant, проверка публикации на чтении; [pdf](../../../apps/api/fsp/pdf.py) из проекции | Повторный adversarial ACL-тест релиза обязателен; полученный ранее PDF не отзывается | Мы — ACL-регрессия; заказчик — обращение с экспортом |
| Утечка после отзыва / бессрочное хранение | [main update_profile](../../../apps/api/fsp/main.py): удаление grants, tasks.suspend | Физическое удаление аккаунта, retention и удаление из backup не реализованы | Мы — механизм; заказчик/юрист — сроки и запросы субъекта |
```

### CC8 · PASS

`docs/delivery/closed_contour/07_HARDENING_CHECKLIST.md`

```text
# CC8 · Приёмка внутреннего контура

DoD: ≥8 проверок, ≥2 выполненные автоматические. ☐ означает действие на инфраструктуре заказчика, не заранее поставленную приёмку. Доказательства локального прогона приведены отдельно.

| Проверка | Авто / человек | Свидетельство или действие |
|---|---|---|
| ☐ .env исключён из git | Авто | `python3 scripts/check_closed_contour_config.py`: [PASS](evidence/config-hygiene.txt) |
| ☐ Секреты случайные, файл 0600 | Авто + админ | [Повтор configure и права](evidence/config-negative-controls.txt): PASS; рабочую ротацию согласовать |
| ☐ Только loopback/private bind | Авто + сетевик | Dry-run loopback ephemeral, без DB publish: [лог](evidence/cc-dry-run-20261021T185211Z-233571.log); A/B на VM проверить `ss -lnt`, firewall и curl с недоверенной подсети |
| ☐ TLS/CA и secure cookies | Человек | Проверить сертификат, редирект HTTP, cookie Secure в браузере; NOT_RUN у заказчика |
```

### CC9 · PASS

`docs/delivery/closed_contour/08_PDN_152_NOTES.md`

```text
# CC9 / CC11 · ПДн: заготовка для юридического и эксплуатационного согласования

DoD: сильные технические утверждения имеют источник; правовые выводы помечены LEGAL_REVIEW_NEEDED. Это карта вопросов к пилоту, не заключение о соответствии 152-ФЗ.

Нормативный ориентир: [152-ФЗ, копия редакции от 24.06.2025 на сайте Минобрнауки](https://minobrnauki.gov.ru/open_ministry/gossluzhba/entry/files/%D0%A4%D0%B5%D0%B4%D0%B5%D1%80%D0%B0%D0%BB%D1%8C%D0%BD%D1%8B%D0%B9%20%D0%B7%D0%B0%D0%BA%D0%BE%D0%BD%20%D0%BE%D1%82%2027.07.2006%20N%20152-%D0%A4%D0%97%20%28%D1%80%D0%B5%D0%B4.%20%D0%BE%D1%82%2024.06.2025.pdf), открыта 21.10.2026. Определение оператора связано с определением целей и состава обработки (ст. 3); перечень тем для проверки: основания/поручение (ст. 6), согласия (ст. 9/10.1), трансграничная передача (ст. 12), права субъекта (ст. 14), автоматизированные решения (ст. 16), локализация/обязанности/защита/прекращение обработки/уведомления (ст. 18–22). Актуальность редакции на дату пилота и применимость каждого положения — LEGAL_REVIEW_NEEDED. Текст на другом официальном сайте оказался старой редакцией; не использован как подтверждение актуальности.

| Тема | Факт / источник | Что согласовать до рабочих ПДн |
|---|---|---|
| Роли on-prem | [Runbook](03_INSTALL_RUNBOOK.md): БД на VM заказчика, разработчик не получает обязательного runtime-доступа | Гипотеза: заказчик = оператор; команда = поставщик ПО, а при доступе поддержки может потребоваться поручение обработки. LEGAL_REVIEW_NEEDED: договор, доступ, субподрядчики |
| Публичный сервис / SaaS | [Канон §0](../../closed_contour_2026-10-21/COMPREHENSIVE_CLOSED_CONTOUR_2026-10-21.md): демо отдельно от поставки | Роль фактического оператора публичной платформы не устанавливается этим пакетом. Нельзя автоматически переносить on-prem распределение ролей на SaaS. LEGAL_REVIEW_NEEDED |
```

### CC12 · PASS

`docs/delivery/closed_contour/READY_TO_DEPLOY_ONEPAGER.md`

```text
# Готовность к внедрению у заказчика

**Команда «Нанотехнологический альянс» подготовила комплект для технического пилота.** Изолированная установка собрана и запущена, health/API проверены, тестовые ресурсы удалены: [лог, exit 0](evidence/cc-dry-run-20261021T185211Z-233571.log). Запуск с рабочими ПДн требует приёмки ИТ, ИБ и юридических условий заказчика.

**Два контура.** Публичный демо-стенд остаётся доступным жюри. Корпоративная поставка устанавливается отдельно на Linux-сервер заказчика: доступ только из внутренней сети или через его reverse-proxy. Внешнюю доступность определяет заказчик. Скачивание зависимостей разрешено; полный air-gap не входит в этот комплект.

**Как внедряем.** Сначала согласуем VM, сеть, TLS и почту; затем ставим приложение с новой БД и секретами. Проверяем вход двух ролей, адресное раскрытие контактов, PDF и отзыв согласия на синтетике. Перед рабочими данными согласуем хранение/удаление, резервное восстановление, мониторинг и ответственных. [Пошаговая установка A/B](03_INSTALL_RUNBOOK.md).

**Что передаём.** Инвентарь сервисов и данных, скрипт репетиции установки, проверку секретов, [модель угроз](05_THREAT_MODEL.md), [hardening checklist](07_HARDENING_CHECKLIST.md), [карту вопросов ПДн](08_PDN_152_NOTES.md), [границу кадровых функций](09_LABOR_BOUNDARY.md), [матрицу доказательств](VERIFY_CLOSED_CONTOUR_MATRIX.json).

```

### CCV1 · PASS

`docs/delivery/closed_contour/VERIFY_CLOSED_CONTOUR_MATRIX.json`

```text
{
  "track": "closed_contour_readiness",
  "verified_at": "2026-10-21",
  "source_base": "cf91823219e76974a688e8c74f8d3f15dce54e84",
  "scope": "Технический комплект пилота; PASS документов не означает промышленную/юридическую приёмку",
  "human_approval": "PENDING",
  "legal_review": "NEEDED",
  "customer_acceptance": "NOT_RUN",
  "tasks": [
    {
```

## Коммиты до итоговой фиксации CCV1

```text
0c57c03 docs(contour): isolate readiness scope and preserve initial workspace evidence
0efdcb0 docs(contour): identify deployment boundaries before customer installation
14fef28 docs(contour): expose data retention and consent limitations for deployment
b0a4c77 docs(contour): make LAN and customer-proxy installation repeatable
2891ba6 security(contour): verify env hygiene before handing off configuration
e195cda test(contour): prove isolated installation and clean up only its disposable resources
fc100b3 docs(security): assign concrete threat gaps to product and customer owners
be5ba14 docs(security): bound rate limiting claims and define customer edge responsibilities
c31b8df docs(contour): give operators a hardening acceptance checklist with measured checks
a1d1692 docs(privacy): ground deployment claims and route legal decisions to review
73bc9e0 docs(contour): keep hiring capabilities distinct from employment recordkeeping
81aeff5 docs(pitch): present demonstrated installation readiness with explicit pilot gates
f491b37 docs(pitch): link readiness without expanding Stage A scope
```

Итоговый SHA CCV1 сообщается в чате; `git log cf91823..codex/closed-contour-readiness --oneline` воспроизводит полный список. Финальная фиксация включает матрицу и этот протокол.

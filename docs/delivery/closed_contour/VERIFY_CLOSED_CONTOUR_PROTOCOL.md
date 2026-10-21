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


## Independent verify (Cursor) 2026-10-21

- Verifier: `cursor_independent_r1`
- Evidence: `evidence/INDEPENDENT_VERIFY_R1.json`
- Time: 2026-10-21T19:03:15.837744+00:00
- Result: must IDs all PASS; CCV2 HUMAN_ONLY; CCV3 PARTIAL
- Live `/api/health`: HTTP 200, demo=true
- Dry-run log: `EXIT_CODE=0`, isolated project `fsp-cc-dryrun-…`, cleanup verified
- FOR_JURY pointer: present (`Closed contour readiness` → onepager)
- Human ★ still required before pitch claim «готовы внедрить» is team-approved

## Adversarial re-verify vs original canon

Дата UTC: 2026-10-21T19:08:40.566934+00:00. Проверяемый HEAD: `e0106f32114826752bb0087e913c00fe983b31c0`. Предыдущие PASS не использованы как основание. Требования только канон → список ID/must JSON → ASTRA_VERIFY_BY_TASK_CC. При конфликте общего §1 и точного §5 применён список must из JSON по явному заданию пользователя.

Содержательное ревью: все документы поставки CC0–CC14, канон §0/3/5/6/8, модели и входные схемы, профильная проекция/согласия/приглашения/SMTP, tasks, PDF, nginx, Dockerfiles, compose, configure и dry-run. Проверены ссылки на группы данных. Автоматика (grep/хеши/структура JSON) ниже — вспомогательна. Бинарные материалы не требуются этим треком и не читались. Полный продуктовый regression, пентест, юридическая редакция, TLS/SMTP заказчика и restore не проверялись.

Первичная фиксация до проверок: pwd=/root/hakaton-contour; branch=codex/closed-contour-readiness; HEAD=e0106f32114826752bb0087e913c00fe983b31c0; единственный untracked — prompts/ASTRA_REVERIFY_CLOSED_CONTOUR.md (сохранён). Основной клон: fix/jury-single-window, ffd9e05806a727dc7c6706582b375a1021e6ec83, modified/untracked WIP (в том числе README.md, apps/api/fsp/main.py, apps/web/src/App.tsx); curl вернул {"status":"ok","demo":true,"version":"1.0.0"}. Повторные полные команды ниже.

Проход 1: требования и документы. Проход 2: сверка утверждений с кодом/конфигом и старым логом. Проход 3: контрпроверка запретов, новый isolated dry-run и полнота матрицы. Это три прохода scoped review контура, не новое полное ревью всех исходных материалов MVP.

Старый dry-run открыт заново: маркеры изоляции/health/cleanup/exit 0 присутствуют. Его source_sha=b0a4c77..., в котором ещё нет самого скрипта; код приложения/compose/configure не изменён, но для устранения неоднозначности повторён запуск из текущего HEAD. Новый лог: docs/delivery/closed_contour/evidence/cc-dry-run-20261021T190622Z-255369.log. Build cache использован; чистая БД создана и удалена.

§6 NOT TODO: совпадения полного rg просмотрены в контексте: это запреты, отрицания, not_implemented и цитаты проверок, а не обещания. Старые evidence JSON и протоколы не служат источниками требований. CC11 означает наличие политики, а не доказательство отсутствия реальных ПДн в публичной БД.

### CC0 — PASS → PASS

DoD (канон §3, дословно): Файлы на месте; в README/delivery есть ссылка «Closed contour readiness»; 0 обещаний air-gap / ФСТЭК

Канон, JSON, стартовый файл на месте; README содержит два контура и явный NOT TODO; указатель из FOR_JURY.

Открыто в этой сессии: `docs/delivery/closed_contour/README.md`; SHA256 `b77e7cfd24432f901e472d37468e102fa8f6fd7b9d9a9556a892aacaec1f4d1e`.
```text
# Closed contour readiness

[Канон](../../closed_contour_2026-10-21/COMPREHENSIVE_CLOSED_CONTOUR_2026-10-21.md) · [Статусы](../../closed_contour_2026-10-21/BACKLOG_CLOSED_CONTOUR.json) · [Протокол](VERIFY_CLOSED_CONTOUR_PROTOCOL.md).

Два контура: публичный демо остаётся доступным; корпоративная поставка устанавливается отдельно, доступ определяет заказчик. Скачивание зависимостей разрешено.

NOT TODO: полный air-gap, сертификация ФСТЭК/ГОСТ, enterprise WAF, превращение продукта в VPN-only, замена 1С/ЗУП, юридическое заключение о соответствии 152-ФЗ и правки Q1–Q7.
```

### CC1 — PASS → PASS

DoD (канон §3, дословно): Файл `docs/delivery/closed_contour/01_INVENTORY.md`: таблица сервис→порт→секрет→том→health; отдельно колонка «ок для внутреннего контура?»

Сверены db bind 127.0.0.1:5547:5432, web BIND_ADDRESS:3080:80, fsp_db mount, pg_isready, https profile и DEMO_MODE; расхождений нет.

Открыто в этой сессии: `docs/delivery/closed_contour/01_INVENTORY.md`; SHA256 `b175ff00337d05c403c441dd2233848233459100331f222d2eaf37f796e93d8e`.
```text
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
```

### CC2 — PASS → PASS

DoD (канон §3, дословно): `02_DATA_MAP.md`: сущность → поля → зачем → срок хранения (факт/предложение) → удаление (есть/нет)

Прочитаны модели/схемы, PDF и логирование; группы данных имеют ссылки, сроки отсутствуют явно, отзыв не назван удалением.

Открыто в этой сессии: `docs/delivery/closed_contour/02_DATA_MAP.md`; SHA256 `dd1d46956539987019009b7d595611c7c75a73b6c2e2eba1b131ffb6aa00fafe`.
```text
# CC2 · Карта данных

DoD: сущности → поля → назначение → хранение → удаление. Источник всех таблиц БД — [models.py](../../../apps/api/fsp/models.py); ограничения входа — [schemas.py](../../../apps/api/fsp/schemas.py), выходы — [outputs.py](../../../apps/api/fsp/outputs.py). Это перечень технических фактов, не юридическая классификация.

| Сущность / группа | Поля и назначение | Хранение: факт / предложение | Удаление: факт |
|---|---|---|---|
| User, ПДн/аутентификация | email, password_hash Argon2, role, verified, demo, created_at; вход | PostgreSQL, бессрочно до админоперации; предложено утвердить срок у оператора | API удаления аккаунта нет |
| Session, Verification, PasswordReset, технические | token_hash, user_id, expires_at, used; доступ и восстановление | Валидность 1 день / 1 час / 30 минут в [main](../../../apps/api/fsp/main.py), это не срок удаления строк | logout удаляет текущую session; reset все sessions; TTL cleanup нет |
| Profile, ПДн/профессиональные | name, phone, about, roles, soft_skills, skills, experience_years, industry, specialization; самодекларация; claimed/verified_grade, verified_attempt_id, grade_changed_at | БД, общего retention нет; предложено хранить по цели найма и согласованному сроку | редактирование/снятие публикации есть, физического удаления нет |
| Profile, ФСП | fsp_identity, achievements JSON | DemoProvider, симуляция, [provider](../../../apps/api/fsp/fsp_provider.py) | unlink очищает эти поля; не весь профиль |
| Consent, ContactGrant | processing/publication/version/time; candidate/company/invitation; история согласий и адресный доступ | consent история без TTL; grant до отзыва | снятие processing/publication удаляет grants; историю Consent сохраняет, [main update_profile/decide](../../../apps/api/fsp/main.py) |
| Company, CompanyMember | name/description/sector/contact; user/company; реквизиты общения, могут быть ПДн представителя | БД без TTL | правка компании есть; удаление через API отсутствует |
| Attempt, Evidence | seed/version/questions с эталонами, answers/result/status/dates; skill/correct/total; подтверждение компетенций | БД без TTL, expires_at закрывает попытку, не удаляет | удаления через API нет; эталоны не передаются до результата |
| Need, Snapshot | criteria JSON, items JSON (оценки, доказательства, ID); история подбора работодателя | БД без TTL; контактные поля не копируются в items, выдача перепроецируется | endpoint удаления нет; снятый профиль скрывается при чтении истории, [main snapshot_view](../../../apps/api/fsp/main.py) |
| Invitation, Message | description, salary_min/max RUB (предложение работодателя, не ожидания кандидата), company_name/contact, status; text/author/time | БД без TTL; свободный текст способен содержать ПДн | отзыв блокирует доступ к чату, не стирает историю |
```

### CC3 — PASS → PASS

DoD (канон §3, дословно): `03_INSTALL_RUNBOOK.md`: предусловия ОС, порты, шаги 1…N, откат, проверка health; явно «deps download = allowed»; вариант A: только LAN (`BIND_ADDRESS=внутр`), вариант B: reverse-proxy заказчика

Шаги Linux/configure/A-B/build/up/health/backup/down прочитаны; новая репетиция CC4 успешна. ОС/Docker уже установлены; TLS/SMTP/restore заказчика NOT_RUN.

Открыто в этой сессии: `docs/delivery/closed_contour/03_INSTALL_RUNBOOK.md`; SHA256 `5bae53b78f489f87758845e72f2ff20a58f83ad36fda0033c851ad56f710d58f`.
```text
# CC3 · Установка у заказчика

DoD: Linux → configure → build → up → health → API → откат. Два варианта A/B ниже. Скачивание зависимостей **разрешено** (deps download = allowed). Это не air-gap. Фактический прогон — CC4; установка на инфраструктуре заказчика, SMTP и TLS заказчика пока NOT_RUN.

## 1. Подготовить отдельную VM

Ubuntu 24.04 LTS или совместимый Debian/Linux с systemd. План пилота: 4 vCPU, 8 GiB RAM, 30 GiB свободного SSD; это исходная оценка, не измеренный SLA. Администратор устанавливает Git, Python 3, curl, tar, Docker Engine и Compose v2 из одобренного репозитория; проверяет `docker version`, `docker compose version` (на прогоне 2.40.3). Членство в docker-группе эквивалентно высоким привилегиям. Не устанавливать рядом с боевым демо без выделения ресурсов.

Пример установки инструментов для чистой Ubuntu 24.04 через её одобренное apt-зеркало (на VM заказчика, не на публичном стенде):

```bash
sudo apt-get update
sudo apt-get install -y git python3 curl tar docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo docker version
```

Открыто в этой сессии: `docs/delivery/closed_contour/evidence/cc-dry-run-20261021T190622Z-255369.log`; SHA256 `80d1b7983331c43f3b36c32751dfdccbf29b86b57894b340eeae5548a9d07fcd`.
```text
UTC=20261021T190622Z project=fsp-cc-dryrun-20261021t190622z-255369
source_sha=e0106f32114826752bb0087e913c00fe983b31c0
STEP copy committed source and configure
isolation verified: local daemon, unique volume/network, no edge, no DB host port, loopback ephemeral web
STEP build
STEP up
API /api/health HTTP 200 expected=200
health ok; demo=false
API /api/catalog HTTP 200 expected=200
API /api/openapi.json HTTP 200 expected=200
API /api/me/profile HTTP 401 expected=401
API /api/auth/demo HTTP 404 expected=404
API /api/auth/demo HTTP 403 expected=403
STEP verify worker process
STEP down disposable project (including its disposable volume)
cleanup verified: no project containers or volumes
EXIT_CODE=0
```

Остаток / границы: Customer VM, TLS/SMTP A/B и backup/restore NOT_RUN.

### CC4 — PASS → PASS

DoD (канон §3, дословно): `scripts/closed_contour_dry_run.sh` (или py) + лог `evidence/cc-dry-run-*.log`: configure → build → up → health → минимальный API ping → down **своего** compose-проекта; exit 0

Повторный dry-run текущего HEAD: уникальные проект/том/сеть, loopback 32769, health demo=false, API 200/401/403/404, cleanup и exit 0.

Открыто в этой сессии: `scripts/closed_contour_dry_run.sh`; SHA256 `d4d7ba393a71ffc3e9cb57c19b6ea946843315ace202154e9761498eb3d90168`.
```text
#!/usr/bin/env bash
# Disposable installation from committed source. Never operates on base compose at runtime.
set -Eeuo pipefail
umask 077
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
mkdir -p docs/delivery/closed_contour/evidence tmp
stamp=$(date -u +%Y%m%dT%H%M%SZ)
project="fsp-cc-dryrun-${stamp,,}-$$"
log="$root/docs/delivery/closed_contour/evidence/cc-dry-run-$stamp-$$.log"
exec > >(tee "$log") 2>&1
printf 'UTC=%s project=%s\n' "$stamp" "$project"
printf 'source_sha=%s\n' "$(git rev-parse HEAD)"
work=$(mktemp -d "$root/tmp/cc-install.XXXXXXXX")
ready=false
```

Открыто в этой сессии: `docs/delivery/closed_contour/evidence/cc-dry-run-20261021T190622Z-255369.log`; SHA256 `80d1b7983331c43f3b36c32751dfdccbf29b86b57894b340eeae5548a9d07fcd`.
```text
UTC=20261021T190622Z project=fsp-cc-dryrun-20261021t190622z-255369
source_sha=e0106f32114826752bb0087e913c00fe983b31c0
STEP copy committed source and configure
isolation verified: local daemon, unique volume/network, no edge, no DB host port, loopback ephemeral web
STEP build
STEP up
API /api/health HTTP 200 expected=200
health ok; demo=false
API /api/catalog HTTP 200 expected=200
API /api/openapi.json HTTP 200 expected=200
API /api/me/profile HTTP 401 expected=401
API /api/auth/demo HTTP 404 expected=404
API /api/auth/demo HTTP 403 expected=403
STEP verify worker process
STEP down disposable project (including its disposable volume)
cleanup verified: no project containers or volumes
EXIT_CODE=0
```

Остаток / границы: Build использовал Docker cache; это не установка ОС/Docker и не тест зеркал.

### CC5 — PASS → PASS

DoD (канон §3, дословно): `04_SECRETS_AND_CONFIG.md` + тест/grep в CI или скрипте: `.env` не в git; `.env.example` без реальных секретов

Свежий config checker: индекс без runtime env, ignore работает, example только placeholders. Временный configure: 0600 и повтор сохраняет байты.

Открыто в этой сессии: `docs/delivery/closed_contour/04_SECRETS_AND_CONFIG.md`; SHA256 `a8a91c14b8bac38ecc0eaa8747ba207df2664c3113238323cf6f3c348c585ea7`.
```text
# CC5 · Секреты и конфигурация

DoD: checklist + исполняемая проверка [check_closed_contour_config.py](../../../scripts/check_closed_contour_config.py). Запуск: `python3 scripts/check_closed_contour_config.py`. Проверяет индекс git, ignore и допустимые placeholder-значения .env.example; не заменяет сканирование всей истории git.

| Проверка | Действие / владелец |
|---|---|
| ☐ Новый секрет БД | `python3 scripts/configure.py`, файл 0600; не переносить секрет демо. Админ |
| ☐ Существующий .env | configure сохраняет; сверить значения в защищённом редакторе. Не печатать в лог |
| ☐ DEMO_MODE=false | Чистая рабочая БД; false не удаляет синтетику из старой БД. Админ |
| ☐ PUBLIC_URL | Доступный пользователям HTTPS URL, без лишнего path; проверить ссылки в письмах |
| ☐ COOKIE_SECURE=true | После подключения TLS; HTTP проверка с реальными сессиями не принимается |
| ☐ SMTP | Внутренний relay, STARTTLS, отдельная учётка с минимальными правами; протестировать обе роли |
| ☐ .env не в git | Автоскрипт проверяет также вложенные runtime .env.*; example допускается только с placeholder |
| ☐ Ротация | Смену пароля существующей PostgreSQL БД проводить согласованно в БД и .env: одна правка POSTGRES_PASSWORD не меняет пароль уже инициализированного тома |
| ☐ Хранение | .env в защищённом каталоге, root/Docker admins доверенные; Docker inspect способен раскрыть env; secrets manager пока не интегрирован |
```

### CC6 — PASS → PASS

DoD (канон §3, дословно): `05_THREAT_MODEL.md` в формате: угроза → уже есть → дыра → кто чинит (мы/заказчик)

10 угроз с механизмом, дырой и владельцем; ACL/согласия, middleware, PDF lock, nginx и compose сверены. Это review модели угроз, не пентест.

Открыто в этой сессии: `docs/delivery/closed_contour/05_THREAT_MODEL.md`; SHA256 `b2055148cd5473b137009005d225b0cb72d41ccf3225005865d6723cc26ff81f`.
```text
# CC6 · Модель угроз для пилота

DoD: активы, доверенные зоны, ≥6 угроз, существующие меры/дыры/владелец. Оценка основана на чтении кода; пентест и нагрузочная атака NOT_RUN. PASS документа не означает отсутствие уязвимостей.

Активы: профили/контакты, согласия, ответы/эталоны и результаты тестов, задания компаний, сессии/SMTP/DB credentials, backup. Зоны доверия: браузер недоверенный → TLS/периметр заказчика → nginx → API/worker → PostgreSQL. Отдельные границы: SMTP, registry/pip/npm/apt при сборке, администратор Docker/SSH и получатель скачанного PDF. Docker network не защищает от администратора хоста.

| Угроза | Уже есть, источник | Дыра / остаточный риск | Кто закрывает |
|---|---|---|---|
| Чужой работодатель читает контакты/API/PDF/старый поиск | [main projection/snapshot_view/pdf](../../../apps/api/fsp/main.py): owner/company grant, проверка публикации на чтении; [pdf](../../../apps/api/fsp/pdf.py) из проекции | Повторный adversarial ACL-тест релиза обязателен; полученный ранее PDF не отзывается | Мы — ACL-регрессия; заказчик — обращение с экспортом |
| Утечка после отзыва / бессрочное хранение | [main update_profile](../../../apps/api/fsp/main.py): удаление grants, tasks.suspend | Физическое удаление аккаунта, retention и удаление из backup не реализованы | Мы — механизм; заказчик/юрист — сроки и запросы субъекта |
| Подбор пароля / захват сессии | [main](../../../apps/api/fsp/main.py): Argon2, hash токенов, httpOnly/SameSite, rate 20/min на auth | Нет MFA/SSO; rate в памяти процесса; за nginx общий IP; demo endpoint без этого лимита | Мы — усиление auth/ключ лимита; заказчик — edge/risk policy |
| Перехват по сети / подмена proxy headers | [compose](../../../compose.yaml): default loopback, API без host port; COOKIE_SECURE configurable | Default HTTP и false не годятся рабочим ПДн; TLS A/B не испытан; доверие proxy/IP надо проверить | Заказчик — TLS/CA/ACL; мы — совместная проверка |
| CSRF/XSS/инъекции в свободном тексте | [main security](../../../apps/api/fsp/main.py): X-Requested-With для mutations; [nginx](../../../apps/web/nginx.conf): CSP; [pdf](../../../apps/api/fsp/pdf.py): escape | Нет независимого пентеста; текст может содержать ПДн; заголовок не заменяет авторизацию | Мы — проверки UI/API/PDF; заказчик — ограничение ввода данных |
| SSRF / вредоносный upload | В [main](../../../apps/api/fsp/main.py)/[schemas](../../../apps/api/fsp/schemas.py) нет endpoint загрузки файла/скачивания произвольного URL; ФСП [DemoProvider](../../../apps/api/fsp/fsp_provider.py) локальный | Нет антивируса/upload sandbox; при добавлении импортов модель угроз пересмотреть; SMTP env доверенный админский ввод | Мы — контроль будущих интеграций; заказчик — egress ACL |
| DoS CPU/RAM/канала (поиск, PDF, login) | nginx 64k body; auth throttling; [pdf](../../../apps/api/fsp/pdf.py) сериализует генерацию lock | Нет общих квот/rate-limit, пагинации всех тяжёлых выдач, защиты канала; base compose без resource limits | Мы — application quotas; заказчик — edge/канал/лимиты контейнеров |
```

### CC7 — PASS → PASS

DoD (канон §3, дословно): Раздел в `05_…` или `06_EDGE_AND_DDOS.md` + честный `not_implemented` список

Auth middleware 20 за 60 секунд по client.host в памяти; nginx 64k; список not_implemented явно исключает WAF/anti-DDoS.

Открыто в этой сессии: `docs/delivery/closed_contour/06_EDGE_AND_DDOS.md`; SHA256 `2a4b546e06abe5178216488d8f36fc2c805e1c607208b969c65c9965dbb78f19`.
```text
# CC7 · Периметр и anti-DDoS

DoD: честно разделить код и меры заказчика. [main.py security](../../../apps/api/fsp/main.py) ограничивает перечисленные auth endpoints до 20 запросов за 60 секунд на request.client.host в памяти процесса. [nginx](../../../apps/web/nginx.conf) ограничивает тело 64k. Это защита от части злоупотреблений, а не anti-DDoS.

| Угроза | Уже есть | Дыра | Владелец |
|---|---|---|---|
| Auth brute force | Локальный лимит auth, Argon2 | Сброс при restart, нет общего backend счётчика; nginx-IP может объединить клиентов | Мы — учёт идентичности/распределённость; заказчик — edge limits |
| Истощение PDF/search | 64k body, PDF lock | Общего request/concurrency лимита нет, lock не экономит канал | Мы — квоты/пагинация; заказчик — timeout/connection limits |
| Переполнение внешнего канала | Внутренняя установка может не иметь публичного маршрута | Если сервис публичен, firewall приложения не остановит объёмный DDoS | Заказчик/оператор связи — upstream фильтрация и план инцидента |
| Подделка клиентского IP | Доверенный nginx как upstream | Real IP chain не подтверждён; X-Forwarded-* от клиента нельзя считать истиной | Заказчик + мы — доверенные proxy CIDR и проверка цепочки |

`not_implemented`: enterprise WAF, anti-DDoS scrubbing, distributed limiter, per-user quotas для всех API, fail2ban rules, SIEM/SOC integration, MFA, нагрузочное доказательство стойкости. Встроенный Caddy — TLS reverse-proxy, не WAF. Npm build report не является пентестом.

Заказчик выбирает существующий WAF/reverse-proxy, лимиты соединений/тела/времени, защиту SSH (возможен fail2ban) и upstream anti-DDoS при публичном доступе. Внешний CDN/WAF не включать автоматически: TLS termination и передача данных третьей стороне требуют отдельной схемы ПДн и LEGAL_REVIEW_NEEDED. Для LAN — ACL, сегментация, мониторинг и защита от внутреннего DoS всё равно нужны. Конкретный продукт и SLA в этом пакете не выбраны и не закуплены.
```

### CC8 — PASS → PASS

DoD (канон §3, дословно): `07_HARDENING_CHECKLIST.md` с ☐ и колонкой «автопроверка / человек»

15 строк авто/человек; checker и отдельный configure 0600/preserve исполнены заново; дополнительно новый dry-run подтверждает bind и demo=false.

Открыто в этой сессии: `docs/delivery/closed_contour/07_HARDENING_CHECKLIST.md`; SHA256 `085d2cfffb97b0499dd68128de7d9122e6d13e56043ecc6b7b44c65c9b9c2110`.
```text
# CC8 · Приёмка внутреннего контура

DoD: ≥8 проверок, ≥2 выполненные автоматические. ☐ означает действие на инфраструктуре заказчика, не заранее поставленную приёмку. Доказательства локального прогона приведены отдельно.

| Проверка | Авто / человек | Свидетельство или действие |
|---|---|---|
| ☐ .env исключён из git | Авто | `python3 scripts/check_closed_contour_config.py`: [PASS](evidence/config-hygiene.txt) |
| ☐ Секреты случайные, файл 0600 | Авто + админ | [Повтор configure и права](evidence/config-negative-controls.txt): PASS; рабочую ротацию согласовать |
| ☐ Только loopback/private bind | Авто + сетевик | Dry-run loopback ephemeral, без DB publish: [лог](evidence/cc-dry-run-20261021T185211Z-233571.log); A/B на VM проверить `ss -lnt`, firewall и curl с недоверенной подсети |
| ☐ TLS/CA и secure cookies | Человек | Проверить сертификат, редирект HTTP, cookie Secure в браузере; NOT_RUN у заказчика |
| ☐ DEMO_MODE=false и чистая БД | Авто + админ | Dry-run health demo=false, demo endpoint 404; не переносить review accounts |
| ☐ SMTP только разрешённый relay | Человек | Доставка/STARTTLS, отзываемые credentials, ссылки PUBLIC_URL; NOT_RUN |
| ☐ API/worker/db недоступны снаружи | Авто + сетевик | Dry-run compose ps: только web 127.0.0.1; customer firewall и Docker rules проверить отдельно |
| ☐ Backup PostgreSQL и restore | Человек | Зашифрованный dump вне git, восстановление в другую БД, согласованные RPO/RTO; NOT_RUN |
| ☐ Контроль SSH/Docker/socket | Человек | Именные админы, минимальные права, нет mount docker.sock в приложении; журнал выдачи доступа |
```

Открыто в этой сессии: `docs/delivery/closed_contour/evidence/cc-dry-run-20261021T190622Z-255369.log`; SHA256 `80d1b7983331c43f3b36c32751dfdccbf29b86b57894b340eeae5548a9d07fcd`.
```text
UTC=20261021T190622Z project=fsp-cc-dryrun-20261021t190622z-255369
source_sha=e0106f32114826752bb0087e913c00fe983b31c0
STEP copy committed source and configure
isolation verified: local daemon, unique volume/network, no edge, no DB host port, loopback ephemeral web
STEP build
STEP up
API /api/health HTTP 200 expected=200
health ok; demo=false
API /api/catalog HTTP 200 expected=200
API /api/openapi.json HTTP 200 expected=200
API /api/me/profile HTTP 401 expected=401
API /api/auth/demo HTTP 404 expected=404
API /api/auth/demo HTTP 403 expected=403
STEP verify worker process
STEP down disposable project (including its disposable volume)
cleanup verified: no project containers or volumes
EXIT_CODE=0
```

Свежая дополнительная автопроверка: копия scripts/configure.py во временном каталоге; первый запуск, stat.S_IMODE == 0o600, повторный запуск, сравнение bytes .env, удаление временной копии.
```text
Local .env created; credentials are not printed
.env already exists; preserved
PASS: configure mode=0600; existing bytes preserved; temporary copy removed
```

### CC9 — PASS → PASS

DoD (канон §3, дословно): `08_PDN_152_NOTES.md`: только утверждения с отсылкой к коду/докам; спорное помечено `LEGAL_REVIEW_NEEDED`

On-prem/SaaS, согласия, адресный grant, отзыв, отсутствие полного экспорта/удаления и внешние потоки описаны со ссылками. LEGAL_REVIEW_NEEDED сохранён.

Открыто в этой сессии: `docs/delivery/closed_contour/08_PDN_152_NOTES.md`; SHA256 `e11f95090d976fae44f2b15482df720f1f8c50d57f0aeb1b555dbb1c09272a76`.
```text
# CC9 / CC11 · ПДн: заготовка для юридического и эксплуатационного согласования

DoD: сильные технические утверждения имеют источник; правовые выводы помечены LEGAL_REVIEW_NEEDED. Это карта вопросов к пилоту, не заключение о соответствии 152-ФЗ.

Нормативный ориентир: [152-ФЗ, копия редакции от 24.06.2025 на сайте Минобрнауки](https://minobrnauki.gov.ru/open_ministry/gossluzhba/entry/files/%D0%A4%D0%B5%D0%B4%D0%B5%D1%80%D0%B0%D0%BB%D1%8C%D0%BD%D1%8B%D0%B9%20%D0%B7%D0%B0%D0%BA%D0%BE%D0%BD%20%D0%BE%D1%82%2027.07.2006%20N%20152-%D0%A4%D0%97%20%28%D1%80%D0%B5%D0%B4.%20%D0%BE%D1%82%2024.06.2025.pdf), открыта 21.10.2026. Определение оператора связано с определением целей и состава обработки (ст. 3); перечень тем для проверки: основания/поручение (ст. 6), согласия (ст. 9/10.1), трансграничная передача (ст. 12), права субъекта (ст. 14), автоматизированные решения (ст. 16), локализация/обязанности/защита/прекращение обработки/уведомления (ст. 18–22). Актуальность редакции на дату пилота и применимость каждого положения — LEGAL_REVIEW_NEEDED. Текст на другом официальном сайте оказался старой редакцией; не использован как подтверждение актуальности.

| Тема | Факт / источник | Что согласовать до рабочих ПДн |
|---|---|---|
| Роли on-prem | [Runbook](03_INSTALL_RUNBOOK.md): БД на VM заказчика, разработчик не получает обязательного runtime-доступа | Гипотеза: заказчик = оператор; команда = поставщик ПО, а при доступе поддержки может потребоваться поручение обработки. LEGAL_REVIEW_NEEDED: договор, доступ, субподрядчики |
| Публичный сервис / SaaS | [Канон §0](../../closed_contour_2026-10-21/COMPREHENSIVE_CLOSED_CONTOUR_2026-10-21.md): демо отдельно от поставки | Роль фактического оператора публичной платформы не устанавливается этим пакетом. Нельзя автоматически переносить on-prem распределение ролей на SaaS. LEGAL_REVIEW_NEEDED |
| Цели / состав | [Карта данных](02_DATA_MAP.md), [models](../../../apps/api/fsp/models.py): регистрация, оценка навыков, подбор, приглашение, диалог и задания | Юрист/оператор утверждает цели и минимизацию. Не принимать специальные категории, паспортные/медицинские документы в свободный текст. LEGAL_REVIEW_NEEDED |
| Обработка / публикация | [schemas Registration/ProfileInput](../../../apps/api/fsp/schemas.py): processing=True при регистрации, запрет publication без processing; [main update_profile](../../../apps/api/fsp/main.py), [models Consent](../../../apps/api/fsp/models.py): версия и история флагов | Наличие checkbox и version не доказывает достаточность текста, отдельность согласия, полномочия лица и условия распространения. LEGAL_REVIEW_NEEDED: формы/версии/порядок доказательства |
| Контакты компании | [main decide/projection](../../../apps/api/fsp/main.py): принятие приглашения создаёт ContactGrant(candidate, company); PDF из той же проекции | Это техническое адресное разрешение, не готовая юридическая форма передачи. Определить получателей и основания. LEGAL_REVIEW_NEEDED |
| Отзыв | [main update_profile/chat_allowed](../../../apps/api/fsp/main.py), [tasks suspend](../../../apps/api/fsp/tasks.py): grants удаляются, публикация скрывается, задания приостанавливаются | Отзыв ≠ удаление, уже выгруженный PDF не отзывается. Оператору нужен процесс обращения к получателям/удаления. LEGAL_REVIEW_NEEDED |
| Доступ / исправление / экспорт | [main own_profile/update_profile/pdf](../../../apps/api/fsp/main.py): доступ и правка профиля, PDF компетенций; [pdf](../../../apps/api/fsp/pdf.py) | Полного экспорта истории всех данных субъекта нет. Нужен ручной регламент проверки личности/ответа, затем реализация экспорта. LEGAL_REVIEW_NEEDED |
```

Остаток / границы: Юридическая актуальность и принятие HUMAN_ONLY; правовое заключение не выполнялось.

### CC10 — PASS → PASS

DoD (канон §3, дословно): `09_LABOR_BOUNDARY.md`: граница продукта vs HRIS; что нельзя обещать на питче

Явная граница HRIS и список запретов питча; поля RUB приглашения и tasks.review согласованы с кодом.

Открыто в этой сессии: `docs/delivery/closed_contour/09_LABOR_BOUNDARY.md`; SHA256 `440d5810a3a50b6a80246c97fd507efa2eea8a810075ed4f335ccdda58597694`.
```text
# CC10 · Трудовые аспекты: граница продукта

DoD: отделить найм от кадрового учёта и перечислить запрещённые обещания. Факты основаны на [models](../../../apps/api/fsp/models.py), [schemas](../../../apps/api/fsp/schemas.py), [tasks](../../../apps/api/fsp/tasks.py).

Продукт хранит профессиональный профиль, заявленный/подтверждённый грейд, навыки и опыт, предложение работодателя с зарплатной вилкой RUB, приглашения, диалог, согласие на периодические задания, ответы и обратную связь компании. Отдельного поля зарплатных ожиданий кандидата в этих моделях нет. Свободный текст может содержать лишние сведения: оператору нужна политика минимизации.

Это не кадровый учёт: нет реестра трудовых договоров, подписания ЭП, приказов, расчёта зарплаты/налогов, табелей, отпусков, больничных и электронных трудовых книжек. Ответ на приглашение — статус в продукте, а не реализованный механизм заключения трудового договора. Оценка задания работодателем хранится отдельно и не меняет подтверждённый грейд (tasks.review).

На питче нельзя обещать:

- замену 1С/ЗУП, HRIS, кадрового ЭДО или полного пакета ТД;
- юридически значимое заключение договора кнопкой «Принять»;
- законность любого тестового задания, отказа или алгоритма ранжирования;
- объективность на всём рынке труда без внешней валидации;
- автоматическое исполнение трудовых обязанностей/обязательную неоплачиваемую работу кандидата.
```

### CC11 — PASS → PASS

DoD (канон §3, дословно): Уже частично в for-jury; добавить явный блок в `08_…` и в onepager

Блок demo и onepager запрещают реальные ПДн, FOR_JURY подтверждает политику общих review accounts. Содержимое публичной БД не проверялось.

Открыто в этой сессии: `docs/delivery/closed_contour/08_PDN_152_NOTES.md`; SHA256 `e11f95090d976fae44f2b15482df720f1f8c50d57f0aeb1b555dbb1c09272a76`.
```text
## demo

На публичном sslip **нельзя вводить реальные ПДн**; использовать только вымышленные имена/контакты и синтетические задания. Это согласовано с [FOR_JURY](../FOR_JURY.md): общие review-аккаунты демонстрационные. Их логины/пароли не переносить в рабочую установку и в этот пакет.

[seed.py](../../../apps/api/fsp/seed.py) создаёт синтетику только при DEMO_MODE=true; [main](../../../apps/api/fsp/main.py) включает demo login и симуляцию подтверждения без SMTP в demo. DEMO_MODE не распознаёт реальные ПДн и не обезличивает свободный текст. False выключает эти возможности, но не удаляет ранее записанные данные. У оператора должен быть процесс обработки случайно внесённых ПДн; правовые основания и удаление — LEGAL_REVIEW_NEEDED. Рабочая поставка начинается с новой БД и false.

Принятие документа и условий обработки: HUMAN_ONLY, [протокол человека](HUMAN_VERIFY_PROTOCOL_CLOSED_CONTOUR.md). Все юридические вопросы остаются открытыми до решения уполномоченного лица; технический PASS CC9 означает полноту этой заготовки.
```

Остаток / границы: Запрет реальных ПДн — политика, не результат аудита содержимого публичной БД.

### CC12 — PASS → PASS

DoD (канон §3, дословно): `docs/delivery/closed_contour/READY_TO_DEPLOY_ONEPAGER.md` (+ при желании PDF позже человеком)

Onepager сохраняет публичный демо, выбор внешнего доступа заказчиком и deps allowed; есть ссылки CC3/CC6/CC9 и NOT_RUN. Подпись человека pending.

Открыто в этой сессии: `docs/delivery/closed_contour/READY_TO_DEPLOY_ONEPAGER.md`; SHA256 `814f8fee9ab9b5eed34e406c918de69a9ed60e874d75638684c0cb0369d4f4f2`.
```text
# Готовность к внедрению у заказчика

**Команда «Нанотехнологический альянс» подготовила комплект для технического пилота.** Изолированная установка собрана и запущена, health/API проверены, тестовые ресурсы удалены: [лог, exit 0](evidence/cc-dry-run-20261021T185211Z-233571.log). Запуск с рабочими ПДн требует приёмки ИТ, ИБ и юридических условий заказчика.

**Два контура.** Публичный демо-стенд остаётся доступным жюри. Корпоративная поставка устанавливается отдельно на Linux-сервер заказчика: доступ только из внутренней сети или через его reverse-proxy. Внешнюю доступность определяет заказчик. Скачивание зависимостей разрешено; полный air-gap не входит в этот комплект.

**Как внедряем.** Сначала согласуем VM, сеть, TLS и почту; затем ставим приложение с новой БД и секретами. Проверяем вход двух ролей, адресное раскрытие контактов, PDF и отзыв согласия на синтетике. Перед рабочими данными согласуем хранение/удаление, резервное восстановление, мониторинг и ответственных. [Пошаговая установка A/B](03_INSTALL_RUNBOOK.md).

**Что передаём.** Инвентарь сервисов и данных, скрипт репетиции установки, проверку секретов, [модель угроз](05_THREAT_MODEL.md), [hardening checklist](07_HARDENING_CHECKLIST.md), [карту вопросов ПДн](08_PDN_152_NOTES.md), [границу кадровых функций](09_LABOR_BOUNDARY.md), [матрицу доказательств](VERIFY_CLOSED_CONTOUR_MATRIX.json).

**Что ещё не проверено (`NOT_RUN`).** Сеть/TLS/SMTP заказчика, backup/restore, пентест, устойчивость к DDoS, приёмка на его VM. Удаление аккаунта и автоматические сроки хранения пока не реализованы. Юридические роли, основания, сроки, трансграничные потоки и процедуры субъекта требуют `LEGAL_REVIEW_NEEDED`. [Проверка человеком](HUMAN_VERIFY_PROTOCOL_CLOSED_CONTOUR.md) ещё не подписана.

**Граница обещания.** Комплект подтверждает возможность технической установки. Он не обещает сертификацию ФСТЭК, enterprise WAF, юридическое соответствие 152-ФЗ или замену 1С/ЗУП. На публичном демо и в общих review-аккаунтах используются только синтетические данные; реальные ПДн вводить нельзя. Формулировку для питча согласуют Данила/Никита.
```

Остаток / границы: Согласование onepager человеком pending.

### CC13 — PASS → PASS

DoD (канон §3, дословно): 1 абзац + ссылка; не переносить must Q* сюда

FOR_JURY содержит один короткий абзац Closed contour readiness со ссылкой; Q-задачи не перенесены.

Открыто в этой сессии: `docs/delivery/FOR_JURY.md`; SHA256 `44aaa3209ca6f620e46fb4a9788c3dff4145f52935873ae34b27f2fdc3f8b39c`.
```text
# Самостоятельная проверка этапа A · 10–15 минут

> Перед отправкой: push отложен пользователем 21 октября. Проверенный код и новые документы сохранены локально. Основной ручной маршрут уже пройден с сопровождением. После разрешения на публикацию — проверить GitHub-ссылки и отправить комплект. [Текущий статус](CURRENT_STATUS_2026-10-21.md), [сценарные аккаунты и их использование](REVIEW_ACCOUNTS_2026-10-21.md).

Все review-аккаунты общие и демонстрационные. Не вводите реальные данные.

| Роль | Логин | Пароль |
|---|---|---|
| Кандидат | review.candidate.fsp@example.org | Review-Cand-2026! |
| Работодатель | review.employer.fsp@example.org | Review-Emp-2026! |
| Другая компания | review.employer2.fsp@example.org | Review-Emp2-2026! |

1. Откройте кандидата в отдельном браузерном профиле. В обзоре проверьте публикацию, подтверждённый уровень и достижения ФСП. ФСП не требуется для прохождения теста.
2. Для нового теста зарегистрируйте отдельный вымышленный аккаунт с доступным вам почтовым ящиком и подтвердите адрес. Имена **fresh_python** и **fresh_sql_middle** в [сценарных аккаунтах](REVIEW_ACCOUNTS_2026-10-21.md) обозначают первоначальную подготовку: они уже использованы человеком и могут быть на cooldown. Готовый **ready_candidate** нужен для быстрого показа результата и приглашений: у него уже есть попытка Junior, её срок не сбрасывать. Общие review-аккаунты могут упираться в ограничения.
3. Введите ответ, перейдите в обзор, вернитесь и обновите страницу: ответ остаётся, срок не продлевается. Нажмите завершение с пропусками и отмените подтверждение. Новые дробные задания явно указывают округление половины вверх. Полное решение теста не обязательно для проверки этого исправления.
```

### CC14 — PASS → PASS

DoD (канон §3, дословно): `PITCH_CLOSED_CONTOUR_90S.md` — отдельно, не блокер must CC1–CC8/CC12

Текст проверен по содержанию и счётчиком слов <=190; хронометраж человеком не выполнялся.

Открыто в этой сессии: `docs/delivery/closed_contour/PITCH_CLOSED_CONTOUR_90S.md`; SHA256 `a782538b528fc6c68cd34cea1e67f6486fa69fad6b59faa88545c2c6e6ba2f1c`.
```text
# Как ставим у вас · текст для 60–90 секунд

Мы подготовили комплект для технического пилота внутри компании. Публичный демо при этом остаётся доступным: вы можете проверить продукт сейчас, а корпоративную поставку развернуть отдельно.

Приложение устанавливается на Linux-сервер заказчика. Доступ возможен из внутренней сети или через ваш reverse-proxy. Скачивание зависимостей разрешено. Мы передаём пошаговую инструкцию, карту данных, список настроек безопасности и скрипт репетиции установки.

Этот скрипт уже собрал приложение с новой базой, проверил работоспособность API и ограничения доступа, затем удалил только собственные тестовые ресурсы. Результат сохранён в логе.

Перед рабочими данными вместе с вашими ИТ и ИБ проверяем сеть, сертификаты, почту, резервное восстановление и права доступа. Отдельно согласуем цели обработки, сроки хранения и порядок удаления. Удаление аккаунта и автоматические сроки хранения ещё требуют реализации. Мы показываем эти ограничения заранее.

Платформа помогает оценивать компетенции и организовать контакт кандидата с работодателем. Она не заменяет кадровый учёт. Мы не обещаем сертификацию, готовый anti-DDoS или юридическое заключение: демонстрируем проверяемый путь установки и понятный перечень условий пилота.
```

Остаток / границы: Чтение вслух и 90-секундный хронометраж HUMAN_ONLY.

### CCV1 — PASS → PASS

DoD (канон §3, дословно): `VERIFY_CLOSED_CONTOUR_MATRIX.json` + `VERIFY_CLOSED_CONTOUR_PROTOCOL.md`

Новая матрица охватывает 18 уникальных ID, прямые DoD канона, свежие цитаты/команды и must_gaps; подписи не имитируются.

### CCV2 — HUMAN_ONLY → HUMAN_ONLY

DoD (канон §3, дословно): `HUMAN_VERIFY_PROTOCOL_CLOSED_CONTOUR.md` по шаблону

Протокол человека существует, ★ и все клетки пусты; принятие Данилой/Никитой/юристом pending.

Открыто в этой сессии: `docs/delivery/closed_contour/HUMAN_VERIFY_PROTOCOL_CLOSED_CONTOUR.md`; SHA256 `f472ad4b400b4e371d1b23e86ec377bc5f9ef365b0ca6c4df46b6fa5b11d8c8c`.
```text

## 1. Смысл (★)

| ID | Кто | Что сделать | Зачем | Результат |
|---|---|---|---|---|
| H-CC-FRAME ★ | Данила / Никита | Прочитать onepager `READY_TO_DEPLOY_ONEPAGER.md` за ≤3 мин → сказать вслух: «мы обещаем внедрение у заказчика, а не VPN-only продукт» — совпадает ли с текстом | Не уехать от запроса Данилы | ☐ PASS ☐ FAIL ☐ SKIP |
| H-CC-DEPS ★ | Данила | В runbook найти фразу про скачивание зависимостей → разрешено ли явно | Совпадает с «Разрешено скачивать зависимости» | ☐ PASS ☐ FAIL ☐ SKIP |

```

Остаток / границы: Все human ★ pending; агент не ставит галочки.

### CCV3 — PARTIAL → PASS

DoD (канон §3, дословно): health sslip ok; `git status` основного клона не «clean» из-за наших `reset --hard`

В этой сессии sslip HTTP 200, основной клон остаётся грязным на fix/jury-single-window; выполнялись только read-only git команды, reset не было.

Остаток / границы: Не доказывает побайтовую сохранность WIP до начала этой сессии; полный UI smoke NOT_RUN.

### Команды и релевантный stdout этой сессии

```bash
pwd; git branch --show-current; git rev-parse HEAD; git status -sb
```
```text
/root/hakaton-contour
codex/closed-contour-readiness
e0106f32114826752bb0087e913c00fe983b31c0
## codex/closed-contour-readiness
?? docs/closed_contour_2026-10-21/prompts/ASTRA_REVERIFY_CLOSED_CONTOUR.md

exit_code=0
```

```bash
git -C /root/hakaton branch --show-current; git -C /root/hakaton rev-parse HEAD; git -C /root/hakaton status -sb
```
```text
fix/jury-single-window
ffd9e05806a727dc7c6706582b375a1021e6ec83
## fix/jury-single-window
 M README.md
 M apps/api/fsp/main.py
 M apps/api/fsp/schemas.py
 M apps/web/src/App.tsx
 M apps/web/src/DemoEntry.tsx
 M apps/web/src/navigation.ts
 M apps/web/src/style.css
 M docs/delivery/API.md
 M docs/delivery/CHANGELOG_STAGE_A.md
 M docs/delivery/FOR_JURY.md
 M docs/delivery/STAGE_A.docx
 M docs/delivery/STAGE_A.pdf
 M docs/delivery/STAGE_A_SMOKE.md
 M docs/delivery/VALIDATION.md
 M docs/delivery/openapi.json
 M docs/final_backlog_2026-10-20/COMPREHENSIVE_STAGE_A_2026-10-21.md
 M tests/browser_jury.py
 M tests/browser_navigation.py
 M tests/browser_sessions.py
 M tests/run_jury_isolated.py
 M tests/test_demo_runs.py
?? docs/00_START_HERE_TEAM_AND_AGENTS.md
?? docs/ASTRA_CODEX_RUNBOOK_STAGE_A.md
?? docs/BACKLOG_TASK2.md
?? docs/COMPREHENSIVE_STAGE_A_2026-10-21.md
?? docs/CONTROL_CHECKLIST.md
?? docs/FINALIST_PREP_PACK_2026-10-20.tgz
?? docs/FSP-audit-2026-10-20.zip
?? docs/FSP-audit-2026-10-20/
?? docs/FSP_ORG_EXPLAINER_2026-10-20.md
?? docs/HUMAN_UNDERSTAND_PITCH_2026-10-20.md
?? docs/METRICS_LOCK.md
?? docs/ONBOARDING_NIKITA_FULL_MAP_2026-10-20.md
?? docs/PITCH_CHECKLIST.md
?? docs/PITCH_THEORY_100_2026-10-20.md
?? docs/REMAINING_NOW.md
?? docs/RUNBOOK_PITCH.md
?? docs/STATUS.md
?? docs/SUBMISSION_LINKS.md
?? docs/TASK2.md
?? docs/TASK2_CLOSURE.md
?? docs/VERIFY_NOW.md
?? docs/assets/
?? docs/call_organizers_2026-10-20.tgz
?? docs/call_organizers_2026-10-20/
?? docs/closed_contour_2026-10-21/
?? docs/delivery/HANDOFF_SNAPSHOT_README.md
?? docs/final_backlog_2026-10-20/00_START_HERE_TEAM_AND_AGENTS.md
?? docs/final_backlog_2026-10-20/ASTRA_CODEX_RUNBOOK_STAGE_A.md
?? docs/final_backlog_2026-10-20/ASTRA_MASTER_PROMPT_STAGE_A.txt
?? docs/final_backlog_2026-10-20/CALL_NOTES_2026-10-20.md
?? docs/final_backlog_2026-10-20/FINAL_INSTRUCTIONS_AND_BACKLOG_2026-10-20.md
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20.zip
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/01-home.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/02-profile.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/03-candidate-overview.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/04-test-in-progress.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/05-answer-lost.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/06-test-borderline.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/06-test-borderline.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/07-fsp-before.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/08-without-fsp.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/09-blank-message.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/10-profile-validation.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/11-bank-without-fsp.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/12-empty-react.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/13-old-selection-before.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/14-current-selection.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/14-current-selection.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/15-old-selection-after.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/16-sql-selection.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/17-partial-selection.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/18-task-plan-offered.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/19-employer-dialogue.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/20-salary-validation.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/21-task-answer.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/22-invitation-rejected.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/23-fsp-restored.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/24-task-evaluated.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/25-task-resume-duplicate.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/25-task-resume-duplicate.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/26-task-closed.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/27-profile-hidden.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/28-contact-revoked.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/29-old-selection-privacy.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/30-revoked-dialogue.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/31-mobile-profile.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/32-mobile-test.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/33-mobile-matching.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/34-salary-auto-adjust.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/35-consent-restored.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/36-final-demo-01-profile.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/37-first-test-questions.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/38-first-test-passed.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/38-first-test-passed.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/39-employer07-empty-invites.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/40-isolation-candidate01.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/41-isolation-candidate02.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/42-middle-questions.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/43-incomplete-test-submit.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/44-candidate-cross-pdf-denied.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/45-company07-contacts.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/46-company08-empty-invites.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/47-company08-hidden-contacts.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/48-python-senior-questions.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/49-python-senior-result.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/50-sql-junior-questions.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/51-sql-junior-result.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/52-sql-middle-questions.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/53-sql-middle-result.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/54-rounding-error.jpg
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/55-sql-senior-questions.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/56-sql-senior-result.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/57-company09-profile.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/58-company10-profile.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/59-modal-keyboard.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/60-logged-out-pdf-denied.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/README.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/candidate-hidden.pdf
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/candidate-own.pdf
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/candidate01-before-consent.pdf
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/candidate01-company07-consented.pdf
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/candidate01-company08-hidden.pdf
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/coverage.json
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/pdf-consented-preview.png
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/pdf-hidden-preview.png
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/pdf-text-check.txt
?? docs/final_backlog_2026-10-20/FSP-audit-2026-10-20/report.html
?? docs/final_backlog_2026-10-20/FSP_ORG_EXPLAINER_2026-10-20.md
?? docs/final_backlog_2026-10-20/HUMAN_UNDERSTAND_PITCH_2026-10-20.md
?? docs/final_backlog_2026-10-20/ONBOARDING_NIKITA_FULL_MAP_2026-10-20.md
?? docs/final_backlog_2026-10-20/README.md
?? docs/final_backlog_2026-10-20/TEAM_BACKLOG_ONEPAGER_2026-10-20.md
?? docs/final_backlog_2026-10-20/assets/
?? docs/final_backlog_2026-10-20/prompts/
?? docs/final_backlog_2026-10-20/templates/
?? docs/finalist_prep_pack_2026-10-20/
?? docs/presentation/FSP_NIKITA_SUBMISSION.pptx
?? docs/presentation/LESSONS_LCT_2026-10-09.md
?? logs/

exit_code=0
```

```bash
curl -fsS --max-time 30 -w '\nHTTP_STATUS=%{http_code}\n' https://85-137-26-131.sslip.io/api/health
```
```text
{"status":"ok","demo":true,"version":"1.0.0"}
HTTP_STATUS=200

exit_code=0
```

```bash
python3 scripts/check_closed_contour_config.py
```
```text
PASS: runtime .env files absent from git index
PASS: .env ignored
PASS: example contains only approved placeholders and loopback defaults

exit_code=0
```

```bash
rg -n '5547|BIND_ADDRESS|fsp_db|profiles:|DEMO_MODE|pg_isready' compose.yaml
```
```text
10:      - fsp_db:/var/lib/postgresql/data
12:      - "127.0.0.1:5547:5432"
14:      test: ["CMD-SHELL", "pg_isready -U fsp -d fsp"]
23:      DEMO_MODE: ${DEMO_MODE:-true}
58:      - "${BIND_ADDRESS:-127.0.0.1}:3080:80"
66:    profiles: [https]
88:  fsp_db:

exit_code=0
```

```bash
rg -n -i 'air.?gap|ФСТЭК|ГОСТ|VPN.only|только.{0,12}VPN|полностью соответств|enterprise WAF|1С|ЗУП|кадровый учёт' docs/delivery/closed_contour
```
```text
docs/delivery/closed_contour/09_LABOR_BOUNDARY.md:7:Это не кадровый учёт: нет реестра трудовых договоров, подписания ЭП, приказов, расчёта зарплаты/налогов, табелей, отпусков, больничных и электронных трудовых книжек. Ответ на приглашение — статус в продукте, а не реализованный механизм заключения трудового договора. Оценка задания работодателем хранится отдельно и не меняет подтверждённый грейд (tasks.review).
docs/delivery/closed_contour/09_LABOR_BOUNDARY.md:11:- замену 1С/ЗУП, HRIS, кадрового ЭДО или полного пакета ТД;
docs/delivery/closed_contour/VERIFY_CLOSED_CONTOUR_PROTOCOL.md:133:DoD: Linux → configure → build → up → health → API → откат. Два варианта A/B ниже. Скачивание зависимостей **разрешено** (deps download = allowed). Это не air-gap. Фактический прогон — CC4; установка на инфраструктуре заказчика, SMTP и TLS заказчика пока NOT_RUN.
docs/delivery/closed_contour/VERIFY_CLOSED_CONTOUR_PROTOCOL.md:238:**Два контура.** Публичный демо-стенд остаётся доступным жюри. Корпоративная поставка устанавливается отдельно на Linux-сервер заказчика: доступ только из внутренней сети или через его reverse-proxy. Внешнюю доступность определяет заказчик. Скачивание зависимостей разрешено; полный air-gap не входит в этот комплект.
docs/delivery/closed_contour/README.md:7:NOT TODO: полный air-gap, сертификация ФСТЭК/ГОСТ, enterprise WAF, превращение продукта в VPN-only, замена 1С/ЗУП, юридическое заключение о соответствии 152-ФЗ и правки Q1–Q7.
docs/delivery/closed_contour/08_PDN_152_NOTES.md:19:| Защита / инциденты | [Threat model](05_THREAT_MODEL.md), [hardening](07_HARDENING_CHECKLIST.md): перечень мер и дыр | Определить уровень защищённости, документы оператора, уведомления/сроки инцидентов, ответственного, аудит. ФСТЭК-сертификация не заявлена. LEGAL_REVIEW_NEEDED |
docs/delivery/closed_contour/06_EDGE_AND_DDOS.md:12:`not_implemented`: enterprise WAF, anti-DDoS scrubbing, distributed limiter, per-user quotas для всех API, fail2ban rules, SIEM/SOC integration, MFA, нагрузочное доказательство стойкости. Встроенный Caddy — TLS reverse-proxy, не WAF. Npm build report не является пентестом.
docs/delivery/closed_contour/03_INSTALL_RUNBOOK.md:3:DoD: Linux → configure → build → up → health → API → откат. Два варианта A/B ниже. Скачивание зависимостей **разрешено** (deps download = allowed). Это не air-gap. Фактический прогон — CC4; установка на инфраструктуре заказчика, SMTP и TLS заказчика пока NOT_RUN.
docs/delivery/closed_contour/HUMAN_VERIFY_PROTOCOL_CLOSED_CONTOUR.md:15:| H-CC-FRAME ★ | Данила / Никита | Прочитать onepager `READY_TO_DEPLOY_ONEPAGER.md` за ≤3 мин → сказать вслух: «мы обещаем внедрение у заказчика, а не VPN-only продукт» — совпадает ли с текстом | Не уехать от запроса Данилы | ☐ PASS ☐ FAIL ☐ SKIP |
docs/delivery/closed_contour/HUMAN_VERIFY_PROTOCOL_CLOSED_CONTOUR.md:30:| H-CC-PDN ★ | Данила (+ юрист по желанию) | В `08_PDN_152_NOTES.md` нет голословного «полностью соответствуем»; спорное помечено `LEGAL_REVIEW_NEEDED` | Не подставить команду | ☐ PASS ☐ FAIL ☐ SKIP |
docs/delivery/closed_contour/HUMAN_VERIFY_PROTOCOL_CLOSED_CONTOUR.md:31:| H-CC-LABOR | Данила | В `09_LABOR_BOUNDARY.md` ясно: это не кадровый учёт / не полный пакет ТД | Не обещать HRIS | ☐ PASS ☐ FAIL ☐ SKIP |
docs/delivery/closed_contour/PITCH_CLOSED_CONTOUR_90S.md:11:Платформа помогает оценивать компетенции и организовать контакт кандидата с работодателем. Она не заменяет кадровый учёт. Мы не обещаем сертификацию, готовый anti-DDoS или юридическое заключение: демонстрируем проверяемый путь установки и понятный перечень условий пилота.
docs/delivery/closed_contour/READY_TO_DEPLOY_ONEPAGER.md:5:**Два контура.** Публичный демо-стенд остаётся доступным жюри. Корпоративная поставка устанавливается отдельно на Linux-сервер заказчика: доступ только из внутренней сети или через его reverse-proxy. Внешнюю доступность определяет заказчик. Скачивание зависимостей разрешено; полный air-gap не входит в этот комплект.
docs/delivery/closed_contour/READY_TO_DEPLOY_ONEPAGER.md:13:**Граница обещания.** Комплект подтверждает возможность технической установки. Он не обещает сертификацию ФСТЭК, enterprise WAF, юридическое соответствие 152-ФЗ или замену 1С/ЗУП. На публичном демо и в общих review-аккаунтах используются только синтетические данные; реальные ПДн вводить нельзя. Формулировку для питча согласуют Данила/Никита.
docs/delivery/closed_contour/VERIFY_CLOSED_CONTOUR_MATRIX.json:125:      "finding": "Нет обещаний HRIS/1С/ЗУП/юридического заключения договора; трудовые решения LEGAL_REVIEW_NEEDED."
docs/delivery/closed_contour/05_THREAT_MODEL.md:20:План до рабочих данных: совместно закрыть TLS/SMTP/backup, юридический процесс удаления/retention и инцидентов; согласовать риски или доработать приложение. Меры не называются ФСТЭК-аттестацией. Сетевое устройство заказчика неизвестно; конкретные подсети и ответственные ФИО заполняются при пилоте.

exit_code=0
```

```bash
git diff --stat b0a4c77e9f4d050362f247cd6e5bdbf8cc285aae HEAD -- compose.yaml apps scripts/configure.py scripts/closed_contour_dry_run.sh
```
```text
 scripts/closed_contour_dry_run.sh | 112 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 112 insertions(+)

exit_code=0
```

```bash
rg -n 'UTC=|source_sha=|STEP|isolation verified|API /|health ok|worker process ok|Removed|cleanup verified|EXIT_CODE=' docs/delivery/closed_contour/evidence/cc-dry-run-20261021T190622Z-255369.log
```
```text
1:UTC=20261021T190622Z project=fsp-cc-dryrun-20261021t190622z-255369
2:source_sha=e0106f32114826752bb0087e913c00fe983b31c0
5:STEP copy committed source and configure
7:isolation verified: local daemon, unique volume/network, no edge, no DB host port, loopback ephemeral web
8:STEP build
185:STEP up
225:API /api/health HTTP 200 expected=200
226:health ok; demo=false
227:API /api/catalog HTTP 200 expected=200
228:API /api/openapi.json HTTP 200 expected=200
229:API /api/me/profile HTTP 401 expected=401
230:API /api/auth/demo HTTP 404 expected=404
231:API /api/auth/demo HTTP 403 expected=403
233:STEP verify worker process
234:worker process ok
235:STEP down disposable project (including its disposable volume)
240: Container fsp-cc-dryrun-20261021t190622z-255369-web-1  Removed
243: Container fsp-cc-dryrun-20261021t190622z-255369-task-worker-1  Removed
247: Container fsp-cc-dryrun-20261021t190622z-255369-api-1  Removed
251: Container fsp-cc-dryrun-20261021t190622z-255369-db-1  Removed
254: Volume fsp-cc-dryrun-20261021t190622z-255369_fsp_db  Removed
255: Network fsp-cc-dryrun-20261021t190622z-255369_default  Removed
256:cleanup verified: no project containers or volumes
257:EXIT_CODE=0

exit_code=0
```

```bash
docker ps -aq --filter label=com.docker.compose.project=fsp-cc-dryrun-20261021t190622z-255369; docker volume ls -q --filter label=com.docker.compose.project=fsp-cc-dryrun-20261021t190622z-255369; docker network ls -q --filter label=com.docker.compose.project=fsp-cc-dryrun-20261021t190622z-255369
```
```text

exit_code=0
```

```bash
rg -n 'Closed contour|реальные данные' docs/delivery/FOR_JURY.md
```
```text
5:Все review-аккаунты общие и демонстрационные. Не вводите реальные данные.
39:Closed contour readiness: подготовлен [комплект технического пилота у заказчика](closed_contour/READY_TO_DEPLOY_ONEPAGER.md) с изолированным прогоном установки и границами ИБ/ПДн. Публичный демо остаётся доступным; приёмка инфраструктуры и юридических условий заказчика ещё требуется.

exit_code=0
```

```bash
python3 - <<'INNER'
from pathlib import Path
p=Path('docs/delivery/closed_contour/PITCH_CLOSED_CONTOUR_90S.md')
n=len(p.read_text().split('\n',1)[1].split()); assert n<=190; print('pitch_words=',n)
p=Path('docs/delivery/closed_contour/07_HARDENING_CHECKLIST.md'); print('hardening_rows=',sum(s.startswith('| ☐') for s in p.read_text().splitlines()))
INNER
```
```text
pitch_words= 152
hardening_rows= 15

exit_code=0
```

```bash
python3 - <<'INNER'
import json
from pathlib import Path
b=json.loads(Path('docs/closed_contour_2026-10-21/BACKLOG_CLOSED_CONTOUR.json').read_text()); m=json.loads(Path('docs/delivery/closed_contour/VERIFY_CLOSED_CONTOUR_MATRIX.json').read_text()); ids=[r['id'] for r in m['tasks']]; assert len(ids)==len(set(ids))==18; assert set(ids)=={r['id'] for r in b['tasks']}; assert not m['must_gaps']; assert all(r['status']=='PASS' for r in m['tasks'] if r['id'] in b['must_for_pitch_claim']); print('PASS: 18 unique IDs; canon DoD per ID; must_gaps=[]; human=PENDING')
INNER
```
```text
PASS: 18 unique IDs; canon DoD per ID; must_gaps=[]; human=PENDING

exit_code=0
```

### Решение

`must_gaps=[]`: агентские DoD держатся. **До заполнения human ★ нельзя заявлять безусловное «готовы внедрить».** CCV2=HUMAN_ONLY/pending, рабочий контур заказчика NOT_RUN. Основной клон не изменялся нашими командами; reset/force-push/снос его томов не выполнялись. Код продукта и runbook не исправлялись.

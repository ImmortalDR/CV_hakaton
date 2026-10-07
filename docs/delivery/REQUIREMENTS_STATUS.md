# Итоговая матрица соответствия

Исходные формулировки и источники сохранены в `docs/REQUIREMENTS_MATRIX.md`.
`pass` означает исполненный сценарий в указанной границе MVP, не отсутствие
любых ошибок. Ограничения не скрыты в этом статусе. Общие результаты и
команды — `VALIDATION.md`; внешний SMTP/ФСП и человеческий пилот — not_run.

| ID | Реализация | Проверка / факт | Статус и границы |
|---|---|---|---|
| M01 | main.py auth, App.tsx Auth | регистрация двух ролей в Chromium, одноразовость/срок/роль в test_api | pass в демо; реальная SMTP-доставка not_run |
| M02 | schemas.ProfileInput, ProfileForm | UI сохранение полей, API профиль | pass, выбран разрешённый ТЗ ручной ввод |
| M03 | pdf.py + единая projection | Cyrillic extraction, запрет второй компании, browser download | pass |
| M04 | bank.py, Assessments | 6 категорий, самостоятельный grade, реальные варианты | pass; отрасль MVP только ИТ |
| M05 | Attempt/Evidence/Profile | самодекларация и FSP не присваивают grade; успешная серверная проверка | pass в рубрике MVP |
| M06 | 12 семейств, fingerprint, oracle | 600 unit-вариантов + 720 вариантов оценки; 2880 независимых проверок в evaluation | реализовано; психометрическая сопоставимость на людях not_run |
| M07 | submit | провал первого/повторного теста и истечение времени | pass, автоматического понижения нет |
| M08 | timestamps, 90 дней / 24 часа | точные границы, история, добровольное изменение | pass |
| M09 | Invitation + decide | принятие/отклонение, чужой кандидат, повтор | pass |
| M10 | Consent + Profile privacy | отзыв/повторная публикация/скрытие стажа, снимки/PDF/чат | pass; удаление аккаунта и политика хранения отложены |
| M11 | fsp_provider.py, FSP UI | привязка/отвязка, без ФСП полный Chromium-сценарий | pass для явно обозначенного mock; реальный реестр not_run |
| M12 | Company/CompanyMember | собственная компания, UI сохранение, разделение двух компаний | pass; один сотрудник на компанию в UI |
| M13 | NeedInput, SearchPage | подтверждённая структура и выдача по категории | pass; без автоматического NLP |
| M14 | GET candidates | spec/grade/verified skill/FSP фильтры, unknown исключён из verified skill | pass |
| M15 | matching.py + evidence UI | 0,80 P@5 против 0,475; источник и дата; FSP только внутри категории | pass на синтетике, рыночная релевантность не доказана |
| M16 | Need + Snapshot | новые снимки, возврат, запрет другой компании, актуальная приватность | pass; доказательства исторические, PDF текущий |
| M17 | invite без Vacancy | UI предложение адресному кандидату | pass |
| M18 | InviteInput + DB CHECK | 8 негативных комбинаций, положительные целые RUB | pass, ноль запрещён |
| M19 | invitation snapshots | компания/описание/контакт/условия до принятия | pass |
| M20 | ContactGrant + projection | полный lifecycle API/поиск/PDF, две компании, raw text | pass, адресное разрешение; скачанное ранее отозвать нельзя |
| M21 | state transitions | sent/viewed/accepted/rejected у сторон, повторы и параллельность | pass |
| M22 | свой backend/БД | сценарий без внешних вакансий и платных моделей | pass |
| M23 | evaluation fixtures/protocol/oracles | явные labels, dev/test, baseline, матрица ошибок и сохранённые провалы | pass как собственная синтетическая процедура; экспертов 0 |
| M24 | исходники, lock, compose, migrations | образы собраны; новая БД и повтор seed; Git workflow | pass; код отправлен в GitHub, ветка codex/fsp-mvp; локальная история сохранена |
| M25 | docs/delivery + OpenAPI | схемы 27 операций / 35 моделей, DOCX/PDF, инструкции | реализовано; визуальная проверка документов — release-checks |
| M26 | роли, Argon2, hashed tokens, CSRF, safe views | доступ по чужим ID, cookie, отказ SMTP и rollback, audits | pass в проверенном объёме; производственная аттестация не заявлена |
| M27 | demo + шаблон PPTX | браузерный walkthrough, скриншоты, презентация по обязательным блокам | MVP/демо реализованы; имена/роли по TEAM_TASKS.md; фамилии/контакты и история не предоставлены |
| R01 | loopback стенд + SSH / видео | Compose и Chromium | pass через разрешённую альтернативу видео + локальный запуск; публичного домена нет |
| R02 | один Compose-проект | 30 пользователей, 270 чтений, p95 3,04 с, 0 ошибок | pass в ограниченном замере, масштабирование отложено |
| R03 | FSP_INTEGRATION.md | проект OIDC/Keycloak и границы провайдера | проект подготовлен, внешняя интеграция not_run |
| O01 | вакансии/самостоятельный отклик | отсутствуют | не реализовано, необязательное |
| O02 | задания работодателя | отсутствуют | не реализовано, необязательное |
| O03 | Message, Chat | диалог только после принятия и при действующем согласии | pass |
| O04 | адаптивность, явные условия | Chromium 390/1440 px, no overflow | адаптивность pass; ATS и модерация не реализованы |
| D01 | python/data × Junior/Middle/Senior | 6 blueprints | pass |
| D02 | React/TS + FastAPI + PostgreSQL | production build + integration + Docker | pass |

Ключевые тесты: `tests/test_api.py`, `tests/test_bank.py`,
`tests/test_matching.py`, `tests/browser_flow.py`, `tests/load_probe.py`.
Невыполненное полное ревью стороннего архива остаётся отдельным ограничением,
разрешённым к обходу для перехода к реализации последним указанием пользователя.

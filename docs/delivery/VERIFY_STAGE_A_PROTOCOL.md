> Исторический протокол/передача состояния. Его SHA, счётчики, not_run и незаполненные человеческие пункты относятся к указанному в нём времени. Текущий итог после ручного прохода и регистрации: [CURRENT_STATUS_2026-10-21.md](CURRENT_STATUS_2026-10-21.md). Не использовать этот снимок как текущий TODO.

# Независимая проверка этапа A — round 2

Сессия: **independent_r2**. Дата: 2026-10-21T10:48:31.092494+00:00. Ветка `codex/fsp-mvp`, проверенный HEAD `ab915af6eb771c9688d60f08dcf1bd9211f59d25`.
Стенд: https://85-137-26-131.sslip.io/.
Канон: `docs/final_backlog_2026-10-20/COMPREHENSIVE_STAGE_A_2026-10-21.md`; затем accept B01–B06/U01–U04 в findings.json, BACKLOG_STAGE_A.json и три ASTRA_VERIFY методики. Старый PROMPT_ASTRA.md не читался.

**Сейчас отправку закрывать нельзя.** Технических FAIL не найдено; 14 PASS, 1 PARTIAL (Pck2), 1 HUMAN_ONLY (Pck5). После успешного push, проверки актуальных ссылок и всех человеческих must — можно отправлять. Факт отправки закрывает Pck5, а не зелёный smoke.

## Независимость и границы

Предыдущие матрицы, «0 FAIL», ab915af и старые smoke не использованы как доказательства. Существующие скрипты прочитаны, их assertions сопоставлены с accept, затем заново исполнены на новых вымышленных аккаунтах. Независимость здесь означает новые исполнения и самостоятельные вердикты; тестовый код частично существующий, не независимая человеческая экспертиза.

Содержательное чтение: канон и accept, методики, релевантные ветки App.tsx (черновик/confirm/overview/форма), smoke/probe, tests/conftest.py, test_stage_a.py, matching, scheduler и privacy lifecycle тесты; скрипты метрик и текущие CHANGELOG/FOR_JURY/VALIDATION/SUBMISSION_LINKS. Три прохода в объёме этого аудита: критерии → связи UI/API/проверок → отрицательные сценарии и сверка вердиктов с упаковкой. Это не новый полный трёхпроходный аудит исходного архива.

Автоматика: pytest, HTTPS Chromium, API/PDF assertions, build, SHA256 и метрики перечислены ниже. Бинарные PDF проверены извлечением текста внутри smoke; новый визуальный рендер PDF/PPTX человеком не выполнен. Презентация проверена diff, не заявлена прочитанной. Оригинальное ТЗ/встреча и весь сторонний архив повторно не читались: объём ограничен исходными критериями этапа A. SMTP, реальный ФСП, люди/эксперты, нагрузка, полный ACL и комплект исходников — не закрываются этим отчётом.

На входе канон имел пользовательское изменение карты файлов и множество untracked материалов. Они не включаются в коммит проверки. SHA256 использованного канона сохранён в environment.json. BACKLOG не переписан: свежие вердикты задач не меняют его done/partial/human_pending; его старые verification остаются историческими утверждениями. Поле Q7.matching_now=1.1.0 — исходный baseline, live=1.2.0.

## Окружение и воспроизводимость

`git branch --show-current` → codex/fsp-mvp; `git rev-parse HEAD` → ab915af6eb771c9688d60f08dcf1bd9211f59d25.
`curl -fsS https://85-137-26-131.sslip.io/api/health` → `{"status":"ok","demo":true,"version":"1.0.0"}`.
`docker compose ps --format json` → [compose.json](evidence/independent_r2/compose.json).
API/db/web/edge healthy; worker running. DB mount `fsp-mvp_fsp_db` сохранён. Ни down -v, ни reset/rebuild/deploy, ни destructive reset не выполнялись.

[Хеши](evidence/independent_r2/hashes.json): для каждого `apps/api/fsp/*.py` сравнили SHA256 bytes workspace, `git show HEAD:path`, `docker compose exec -T api|task-worker cat /app/fsp/name`. Все 14+14 совпали. После fresh build для всех 3 файлов dist сравнили bytes с `/usr/share/nginx/html/relative_path` контейнера web и HTTPS URL. Все совпали. Это доказательство содержимого, не git-метка образа.

pytest очищает только отдельную `fsp_test` через штатную fixture; `fsp` не очищалась. Live smoke/probe создают свои demo users, скрывают только свои профили и закрывают/приостанавливают свои задания. Existing review accounts использованы только для login. Проверки не являются нулевой записью в БД: вымышленные записи сохраняются.

## Команды и свежие результаты

Все команды из `/root/hakaton`; exit codes завершившихся процессов проверены.

| Команда | Результат | Сырой вывод |
|---|---|---|
| `COOKIE_SECURE=false python3 scripts/run_local.py .venv/bin/pytest -q tests` | exit0, 97 passed, 2 warnings, 47.49s | [pytest.log](evidence/independent_r2/pytest.log) |
| `python3 scripts/run_local.py .venv/bin/python scripts/smoke_stage_a.py --out docs/delivery/evidence/independent_r2/smoke.json` | exit0, 18 групп, page_errors=[] | [smoke.log](evidence/independent_r2/smoke.log) |
| `python3 scripts/run_local.py .venv/bin/python scripts/probe_stage_a_q1.py` | exit0, оба PASS | [q1-probe.log](evidence/independent_r2/q1-probe.log) |
| `npm --prefix apps/web run build` | exit0, tsc и vite | [build.log](evidence/independent_r2/build.log) |
| `PYTHONPATH=apps/api:. .venv/bin/python` → stage_a_matching.main(), bank_v2_audit.main() | exit0; вывод ниже | [metrics.log](evidence/independent_r2/metrics.log) |
| `git ls-remote origin refs/heads/codex/fsp-mvp` | remote 2e6d6da, не HEAD | [remote.log](evidence/independent_r2/remote.log) |

COOKIE_SECURE=false задан только процессу тестов: TestClient работает с HTTP, production .env и secure-cookie не менялись. Метрики запускались с перенаправлением `Path.write_text` в evidence/independent_r2 (unittest.mock.patch), чтобы не переписывать evaluation/*.json. Алгоритмы и входные данные не менялись. Свежие полные результаты сохранены рядом.

Дополнительная контрпроба: [исходник](evidence/independent_r2/extra-probe-source.txt) копируется в `/tmp/independent-r2-extra.py`, запуск `python3 scripts/run_local.py .venv/bin/python /tmp/independent-r2-extra.py`. Первый запуск подтвердил B05/B06, затем упал на ошибочном точном accessible-label селекторе SQL, не найдя элемент. Это ошибка измерительного скрипта, не доказательство дефекта продукта. Селектор исправлен на существующий label.field + текст SQL + select; продукт не менялся. [Первый лог](evidence/independent_r2/extra-probe.log) сохранён; [повтор](evidence/independent_r2/extra-probe-rerun.log) учитывается отдельно.

## Q1/B01 и Q3: отрицательные пути

Полный smoke действительно выполняет `route.abort()` для PUT answers: сервер сохраняет старое значение, UI показывает ошибку. Leave cancel удерживает экран; leave accept разрешает Обзор; после round-trip значение и предупреждение остаются. Reload вызывает beforeunload; закрытие с run_before_unload и новая вкладка восстанавливают dirty draft. Снятие сбоя и возврат дают ACK; API содержит новый ответ, localStorage очищен, id/expires_at прежние. Отдельный probe заменяет сбой сети HTTP503, меняет два ответа, отменяет reload и нажимает «Повторить сохранение»; задержанный ACK для 44 не стирает ввод 55. Это исполненные assertions, не вывод из наличия localStorage в коде.

```text
PASS independent HTTP503 / two dirty answers / cancel reload / manual flush
PASS independent delayed ACK / newer edit retained / ordered flush / stable id and expiry
```

Q3 direct API без confirm_incomplete возвращает 409 и оставляет active, answers и expires_at. UI: 7 пустых из 8, Cancel сохраняет active, Accept завершает. Pytest дополнительно проверяет absent/false flag и whitespace. Текст native confirm явно сообщает неверные ответы и 24 часа пересдачи (App.tsx); понятность текста человеку ещё не оценена.

## Q7: измерение, не обещание улучшения

VERSION matching-1.1.0 → matching-1.2.0; банк 2.1.0. Live версии проверены smoke, соответствие production выбранным весам — pytest. Сетка выбирается по dev, holdout используется после выбора; синтетическая авторская релевантность не является экспертной истиной. Документированное precommit намерение нельзя ретроспективно доказать как независимый эксперимент.

| Выборка | Кандидаты / запросы | P@5 до | P@5 после |
|---|---:|---:|---:|
| dev | 16 / 2 | 1.00 | 1.00 |
| holdout/test | 48 / 8 | 0.80 | 0.80 |

Веса 60/15/20/5 → 30/15/45/10. **Улучшение P@5 не доказано.** Test+FSP меняют порядок внутри категории; самодекларация не даёт баллов. VERSION + таблица в VALIDATION и описание в FOR_JURY совпадают с повтором.

```text
{"old_weights": [60, 15, 20, 5], "selected_weights": [30, 15, 45, 10], "selection": "max dev P@5; tie: minimum L1 distance to old weights, then tuple order"}
dev 1.0 -> 1.0
test 0.8 -> 0.8
{"oracle_checks": 36000, "oracle_mismatches": [], "simulated_attempts": 42000, "analytic_iid": [{"version": "1.2.0", "probability_correct": 0.8, "pass_probability": 0.6144000000000001}, {"version": "1.2.0", "probability_correct": 0.9, "pass_probability": 0.8019000000000001}, {"version": "2.1.0", "probability_correct": 0.8, "pass_probability": 0.7340032000000002}, {"version": "2.1.0", "probability_correct": 0.9, "pass_probability": 0.9300217499999999}]}
1.2.0 frequent_guess mean pass 0.025 pair agreement 0.9534
1.2.0 noise_10 mean pass 0.7997 pair agreement 0.6795
1.2.0 noise_20 mean pass 0.5933 pair agreement 0.5167
1.2.0 old_families_only mean pass 1 pair agreement 1.0
2.1.0 frequent_guess mean pass 0 pair agreement 1.0
2.1.0 noise_10 mean pass 0.926 pair agreement 0.8628
2.1.0 noise_20 mean pass 0.714 pair agreement 0.5914
2.1.0 old_families_only mean pass 0 pair agreement 1.0
```

36 000 сверок эталонов без расхождений; 42 000 синтетических попыток — не люди. Сохраняются 4 семейства по 2 вопроса, устойчивость к заучиванию и профессиональные грейды не валидированы пилотом. Q7 PASS именно по техническому DoD канона и честной процедуре, не по рыночному качеству.

## Все ID и accept аудита

| ID | Вердикт | Основание |
|---|---|---|
| Q1 | PASS | failed PUT → leave cancel/accept → round-trip → warning → reload/close/reopen → retry ACK; id/expiry stable |
| Q2 | PASS | Live bank 2.1.0, hint 90,625 → 90,63 |
| Q3 | PASS | Direct submit without confirm: 409, active, draft/expiry unchanged; UI 7 из 8, cancel → active, accept → completed |
| Q4 | PASS | Новый, неподтверждённый, подтверждённый published/hidden; CTA, publication without relogin; composer removed, PDF404 |
| Q5 | PASS | Ярлыки selection/invitation/PDF; статусы приглашения; filters/reload/scroll; dated snapshot/changed banner; две суммы вкладов; unique labels |
| Q6 | PASS | Evaluate85 → pause → resume: одна выдача, next_issue_at прежний; UI дата=API |
| Q7 | PASS | [60,15,20,5] → [30,15,45,10]; dev1→1; holdout .8→.8; 36000 oracle checks/0 mismatches, 42000 synthetic attempts |
| Pck1 | PASS | Равная P@5 соответствует CHANGELOG; улучшение не заявлено |
| Pck2 | PARTIAL | Три review login200; OpenAPI exact |
| Pck3 | PASS | health ok/demo true; db volume fsp-mvp_fsp_db; product diff empty |
| Pck4 | PASS | 18 групп PASS, page_errors=[]; полный scripts/smoke_stage_a.py |
| Pck5 | HUMAN_ONLY | Внешняя отправка не проверяется git; SUBMISSION_LINKS подготовлен локально |
| REG_FSP | PASS | Junior без ФСП остаётся Junior; demo-winner +6 к score, grade прежний |
| REG_ISO | PASS | До согласия PDF без email; после — email только у адресата, другая компания без контактов; outsider PDF403 |
| REG_OLD_SEL | PASS | Старый search доступен после нового; hidden candidate исключён; dated snapshot+changed banner |
| NOTTODO | PASS | Stage A diff demo/docs/presentation пуст; продукт в этой сессии не изменён |

B01→Q1; B02→Q2; B03→Q3; B04→Q6; B05/B06→Q4; U01–U04→Q5. Все accept сопоставлены: повторный вход/срок через server lifecycle и live restore; B03 последствия в confirm; B04 граница/повтор/concurrent/closed через time tests; B06 republish/new invite через дополнительный live probe; U03 смена специализации дополнительно выполнена; U04 unknown/unmet и суммы проверены отдельно. Субъективное «легко/понятно» вынесено в human, не объявлено наблюдением человека.

confirmed_by_audit проверены вновь, а не унаследованы: no_fsp_keeps_category + fsp_bonus_does_not_change_grade → REG_FSP; old_selections_preserved → REG_OLD_SEL; cross_company_contacts_isolated + cross_candidate_pdf_denied → REG_ISO. Это проверенные сценарии, не полный ACL.

## Pck1 и NOT TODO

Текущий CHANGELOG содержит Q1–Q7, историю STOP явно отделяет от актуального статуса и ссылается на протокол. Его утверждения про dirty draft/retry/confirm совпали с новым прогоном; 97 тестов, 18 групп и P@5 .8→.8 воспроизведены. Упоминание 20 целевых тестов относится к прошлому прогону: в этой сессии они отдельно не повторялись, полный suite включает соответствующие тесты. Противоречий свежим вердиктам не обнаружено; changelog не редактировался для получения PASS.

NOTTODO: diff Stage A `git diff 2e6d6da HEAD -- demo docs/presentation` пуст; новый IRT pipeline не добавлен в перечне/истории apps/evaluation; веса имеют замер; FOR_JURY/CHANGELOG явно называют SMTP not_run и ФСП демонстрационным. Питч не репетировался, новый функционал и редизайн в verify не добавлялись, настройки VPN/SSH не менялись. Время чужой работы вне git не наблюдалось. Отдельный untracked PPTX не подтверждает замену отслеживаемой презентации.

## §6 канона — пункт за пунктом

| Пункт | Статус | Сверка |
|---|---|---|
| Q1–Q3 закрыты или обоснован stop | PASS | Q1–Q3 PASS по свежим проверкам; stop не нужен. |
| Q7 новая VERSION + таблица на выборке | PASS | matching-1.2.0; VALIDATION содержит dev1→1/test.8→.8; свежий rerun совпал. |
| Q4–Q6 сделано или partial в changelog | PASS | Технические DoD PASS; календарная неделя и человеческие оценки выделены. |
| Pck1–Pck3 | PARTIAL | Pck1/Pck3 PASS; Pck2 ожидает публикацию актуальной ветки и human walk. |
| Pck4 smoke green | PASS | 18 свежих групп, page_errors=[]; Q1–Q3 не FAIL. |
| Pck5 ссылки ушли | HUMAN_ONLY | Не отправлены агентом; подтверждения человека нет. |

## Блокеры и передача

Нет воспроизведённых must FAIL. Текущий блокер публикации: remote не содержит проверенный HEAD; Проверка `GIT_TERMINAL_PROMPT=0 git push --dry-run origin codex/fsp-mvp` завершилась exit128: `fatal: could not read Username for https://github.com: terminal prompts disabled` ([лог](evidence/independent_r2/push-preflight.log)). Это конкретный блокер авторизации; dry-run ничего не отправил. Нужны успешный обычный push, актуальные GitHub-ссылки, заполнение HUMAN_VERIFY_PROTOCOL_STAGE_A.md (включая ★) и фактическая отправка человеком. Только после успешных push+human можно слать; этап A целиком ещё не закрыт. SMTP и реальная неделя не являются скрыто выполненными проверками.

Код продукта, исходные подборки, БД и пользовательские документы не исправлялись. Коммит ограничен этими тремя документами и новыми сырыми доказательствами в docs/delivery/evidence/independent_r2. Старые результаты сохранены в git-истории; новые файлы не копируют их вердикты.

## Дополнение к воспроизведению и контролю документов

Дополнительный live probe повторно завершился exit0:

```text
PASS B05 orb before/after confirmation; B06 hide, republish stays denied, new accepted invite opens composer
PASS U03 specialization changes relevant skill controls and required default; untested skills labeled
```

В первом запуске ошибочный селектор был `form.get_by_label('SQL', exact=True)`; в сохранённом исходнике повтора — `form.locator('label.field').filter(has=hr.get_by_text('SQL',exact=True)).locator('select')`. Оба лога сохранены, FAIL инструмента не скрыт.

Метрики без записи в исходные результаты можно повторить так:

```python
from pathlib import Path
from unittest.mock import patch
from evaluation import stage_a_matching, bank_v2_audit
write = Path.write_text
out = Path('docs/delivery/evidence/independent_r2')
def redirected(path, data, *args, **kwargs):
    return write(out / path.name, data, *args, **kwargs)
with patch.object(Path, 'write_text', redirected):
    stage_a_matching.main()
    bank_v2_audit.main()
```

Запуск с `PYTHONPATH=apps/api:. .venv/bin/python`. Свежий matching result совпал с отслеживаемым JSON целиком. [source-hashes.json](evidence/independent_r2/source-hashes.json) фиксирует версии скриптов и упаковки. Проверены 16 уникальных ID, все ссылки evidence, все human_checks_required и локальные ссылки FOR_JURY/SUBMISSION_LINKS; отсутствующих не найдено. `git diff --check` для трёх основных документов чист. После добавления сырых логов staged-check показал trailing whitespace и пустую последнюю строку в extra-probe.log: это исходное форматирование traceback Playwright, сохранённое без изменения. Человеческие клетки не заполнены агентом.

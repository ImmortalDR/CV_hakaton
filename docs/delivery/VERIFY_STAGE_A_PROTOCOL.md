# Свежая проверка этапа A по канону после исправления Q1

Дата: 2026-10-21T10:35:44.229363+00:00. Ветка `codex/fsp-mvp`. Проверенный код стенда: `7f3dde4cbe5b17b0f16154e4ede90a91673428f8`.
Критерии: `COMPREHENSIVE_STAGE_A_2026-10-21.md`, путь и SHA источников — в [матрице](VERIFY_STAGE_A_MATRIX.json); B01–B06/U01–U04 accept из findings. Не использован PROMPT_ASTRA.md.

Проверка выполнена после фикса и деплоя заново. Предыдущие PASS не перенесены как доказательства. Независимость здесь — от старых вердиктов и от happy-path smoke: отдельная контрпроба использует HTTP503 и задержку ACK. Исправление и проверку выполнял один агент; независимый человек/второй агент не участвовал. Человеческие отметки не подделаны.

## E0. Окружение и два цикла

На старте HEAD `d4501b9`; пользовательские untracked материалы и изменение COMPREHENSIVE сохранены без включения в коммиты. Исходная E3 доступна через `git show d4501b9:docs/delivery/VERIFY_STAGE_A_PROTOCOL.md`.

1. `e5f78dd`: persistent draft, сравнение с серверным снимком, guard, retry и negative smoke. Build/deploy выполнены. 97 pytest PASS. Smoke **FAIL**: guard также блокировал возврат из Обзора; [сырой лог](evidence/q1-recovery/loop1-smoke-failure.log). Это новый дефект первого исправления, не закрытый PASS.
2. `7f3dde4`: guard только на уход из теста. Повторно build/up api web; повторно 97 pytest; 18 smoke групп PASS; отдельная контрпроба PASS; 20 целевых PASS. На этом условие пользователя 0 FAIL выполнено.

Команды деплоя (два запуска, без down/volume removal):

```bash
docker compose build api web
docker compose up -d --no-deps api web
```
Worker не менялся, но его исходники также сверены. БД не сбрасывалась; тестовый pytest использует отдельную fsp_test, guard в conftest запрещает другое имя. Live smoke/probe добавляют только собственные вымышленные профили и скрывают их в finally. Исходные профили и сохранённые подборки не удаляются.

Вывод второго запуска up:

```text
 Container fsp-mvp-api-1  Recreate
 Container fsp-mvp-api-1  Recreated
 Container fsp-mvp-web-1  Recreate
 Container fsp-mvp-web-1  Recreated
 Container fsp-mvp-api-1  Starting
 Container fsp-mvp-api-1  Started
 Container fsp-mvp-api-1  Waiting
 Container fsp-mvp-api-1  Healthy
 Container fsp-mvp-web-1  Starting
 Container fsp-mvp-web-1  Started
```

```text
SERVICE       STATUS
api           Up 4 minutes (healthy)
db            Up 9 days (healthy)
edge          Up 9 days (healthy)
task-worker   Up 2 hours
web           Up 4 minutes (healthy)
```

## E1. Полный свежий pytest

```bash
COOKIE_SECURE=false python3 scripts/run_local.py .venv/bin/pytest -q tests
```

```text
........................................................................ [ 74%]
.........................                                                [100%]
=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/fastapi/testclient.py:1
  /root/hakaton/.venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

.venv/lib/python3.12/site-packages/starlette/testclient.py:53
  /root/hakaton/.venv/lib/python3.12/site-packages/starlette/testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
97 passed, 2 warnings in 38.46s
```

97 PASS, две предупреждающие записи зависимостей. HTTP TestClient использует COOKIE_SECURE=false; боевой HTTPS cookie режим не менялся. Проверены ownership, состояние попыток, контакты/PDF/чат, повторная публикация и новое согласие, задания и регрессии. Это не полный внешний security-аудит.

## E2. Live HTTPS smoke, включая отрицательный B01

```bash
python3 scripts/run_local.py .venv/bin/python scripts/smoke_stage_a.py --out /tmp/q1-smoke-2.json
```

```json
{
  "status": "pass",
  "checked_at": "2026-10-21T10:33:32.295674+00:00",
  "base_url": "https://85-137-26-131.sslip.io",
  "checks": [
    "https_health_ok",
    "openapi_exact",
    "three_review_logins_ok",
    "Q1_navigation_reload_server_draft_owner_expiry",
    "Q2_live_bank_2_1_rounding_hint",
    "Q1_failed_PUT_leave_cancel_accept_reload_close_reopen_retry_server_ack",
    "Q3_direct_API_without_confirm_409_active_draft_unchanged",
    "Q3_cancel_keeps_active_accept_completes",
    "Q4_verified_published_hidden_empty_invitations_and_overview_CTA",
    "Q5_anonymous_label_selection_invitation_PDF_UI",
    "invite_accept_addressed_contacts_PDF_isolation",
    "FSP_does_not_change_grade_zero_without_FSP",
    "old_snapshot_preserved",
    "Q5_two_visible_score_sums_unique_labels_changed_banner_scroll",
    "Q5_filters_snapshot_and_score_UI",
    "Q6_live_7day_resume_no_duplicate_UI_date_equals_API",
    "Q4_hidden_overview_revoked_chat_snapshot_PDF",
    "mobile_no_horizontal_overflow"
  ],
  "page_errors": [],
  "scope": "Live HTTPS API and Chromium; 4 newly bootstrapped fictional accounts, review logins read-only; no SMTP or real-person testing; own smoke candidate hidden, own plan closed."
}
```

Все assertions исполнены на развернутом HTTPS. Отрицательный сценарий:

1. Успешный PUT `90,63`, серверный GET, Обзор/назад/reload.
2. Контекст браузера обрывает только PUT answers. Новый `UNSAVED-123` остаётся локальным, сервер всё ещё содержит `90,63`; статус ошибки виден.
3. Отмена ухода оставляет тест видимым. Подтверждение → Обзор → назад: новый ответ и ошибка на месте, PUT повторяется.
4. Reload показывает beforeunload; после reload ответ и ошибка остаются. Закрытие с run_before_unload=True вызывает второй beforeunload; новая вкладка в том же контексте восстанавливает черновик при всё ещё оборванном PUT.
5. Маршрут разблокирован; уход/возврат без нового ввода отправляет черновик. Сервер получает `UNSAVED-123`, localStorage очищен только после ACK, reload сохраняет ответ. ID и expiry прежние.
6. Возвращаем один ответ `90,63`; Q3 напрямую отвергает submit без confirm, затем UI отменяет и подтверждает сдачу с 7 пропусками.

Остальные Q4–Q6 и REG проверены свежими шагами скрипта: CTA по состоянию, анонимы/фильтры/scroll/сумма компонентов, pause/resume с датой из API, адресное согласие и изоляция PDF, скрытие из старых снимков. Smoke не выдаёт созданные solver-результаты за человеческую валидацию.

## E3. Отдельная отрицательная контрпроба

[Код](../../scripts/probe_stage_a_q1.py) использует отдельные вымышленные аккаунты и другие отказы. В отличие от E2, отвечает HTTP503 и удерживает успешный запрос до следующего ввода. Выполнена отдельно после деплоя:

```bash
python3 scripts/run_local.py .venv/bin/python scripts/probe_stage_a_q1.py
```

```text
PASS independent HTTP503 / two dirty answers / cancel reload / manual flush
PASS independent delayed ACK / newer edit retained / ordered flush / stable id and expiry
```

Проверено: сервер содержит старый ответ, пока два новых не сохранены; отмена beforeunload сохраняет оба поля; кнопка повтора отправляет оба поля. При задержанном PUT 44 пользователь вводит 55; после ACK 44 UI всё ещё показывает 55 и несохранённость. Второй PUT подтверждает 55, очередь очищается. ID/expiry прежние. Не только совпадение текста в DOM: проверяется серверный GET и удаление localStorage после успеха.

## E4. Отдельные целевые удары по канону

```bash
COOKIE_SECURE=false python3 scripts/run_local.py .venv/bin/pytest -v tests/test_stage_a.py tests/test_bank.py::test_half_up_exact_boundaries tests/test_bank.py::test_conditional_rounding_new_and_historical_versions tests/test_matching.py tests/test_employer_tasks.py
```

```text
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-8.3.5, pluggy-1.6.0 -- /root/hakaton/.venv/bin/python
cachedir: .pytest_cache
rootdir: /root/hakaton
plugins: anyio-4.15.1, platformdirs-4.12.3
collecting ... collected 20 items

tests/test_stage_a.py::test_draft_answers_owner_lifecycle PASSED         [  5%]
tests/test_stage_a.py::test_draft_expired PASSED                         [ 10%]
tests/test_stage_a.py::test_anonymous_labels_distinct_and_stable PASSED  [ 15%]
tests/test_stage_a.py::test_incomplete_submit_requires_explicit_confirmation PASSED [ 20%]
tests/test_bank.py::test_half_up_exact_boundaries[2900-32-90.63] PASSED  [ 25%]
tests/test_bank.py::test_half_up_exact_boundaries[1005-1000-1.01] PASSED [ 30%]
tests/test_bank.py::test_half_up_exact_boundaries[625-1000-0.63] PASSED  [ 35%]
tests/test_bank.py::test_conditional_rounding_new_and_historical_versions PASSED [ 40%]
tests/test_matching.py::test_unknown_never_becomes_proof_and_sport_does_not_change_category PASSED [ 45%]
tests/test_matching.py::test_explicit_evidence_and_zero_experience_remain_distinct PASSED [ 50%]
tests/test_matching.py::test_required_skill_coverage_is_not_a_score_threshold PASSED [ 55%]
tests/test_matching.py::test_untrusted_achievement_does_not_satisfy_fsp_filter PASSED [ 60%]
tests/test_matching.py::test_stage_a_test_and_sport_change_within_category_order PASSED [ 65%]
tests/test_matching.py::test_production_matches_selected_weights_on_frozen_sample PASSED [ 70%]
tests/test_employer_tasks.py::test_task_complete_lifecycle_grade_and_contact_isolation PASSED [ 75%]
tests/test_employer_tasks.py::test_task_plan_idempotency_consent_and_schema PASSED [ 80%]
tests/test_employer_tasks.py::test_scheduler_periodic_delivery_deduplicates_and_does_not_burst PASSED [ 85%]
tests/test_employer_tasks.py::test_submitted_work_waits_for_review_and_pause_cancels_open_tasks PASSED [ 90%]
tests/test_employer_tasks.py::test_deadline_and_concurrent_answers PASSED [ 95%]
tests/test_employer_tasks.py::test_resume_keeps_cadence_after_review_and_legacy_pause PASSED [100%]

=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/fastapi/testclient.py:1
  /root/hakaton/.venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

.venv/lib/python3.12/site-packages/starlette/testclient.py:53
  /root/hakaton/.venv/lib/python3.12/site-packages/starlette/testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 20 passed, 2 warnings in 8.64s ========================
```

Q2: 90.625→90.63, 1.005, 0.625, точка/запятая; новый банк 2.1.0 согласован с подсказкой. Политика старых версий документирована: без массового пересчёта. Q3: отсутствующий/false confirm и whitespace →409, ответ/срок/active прежние, explicit true завершает. Q6: контролируемая временная граница, конкурентные ticks, resume и closed. Реальная неделя не ожидалась.

## E5. Q7 — свежие измерения, не старые числа

Оба main() выполнены в текущей сессии с перенаправлением только результата в /tmp, исходная fixture не изменялась:

```bash
PYTHONPATH=apps/api:. .venv/bin/python - <<'PYCODE'
from pathlib import Path
from unittest.mock import patch
from evaluation import stage_a_matching, bank_v2_audit
out=Path('/tmp/q1-evaluation'); out.mkdir(exist_ok=True)
original=Path.write_text
with patch.object(Path,'write_text',lambda self,data,*a,**kw:original(out/self.name,data,*a,**kw)):
    stage_a_matching.main()
    bank_v2_audit.main()
PYCODE
```

```json
{
  "old_weights": [
    60,
    15,
    20,
    5
  ],
  "selected_weights": [
    30,
    15,
    45,
    10
  ],
  "selection": "max dev P@5; tie: minimum L1 distance to old weights, then tuple order",
  "fixture_sha256": "0f4bb52e97a78d1326e6da2031303315dc6105461f59860fc3581402b3e50850"
}
```

| Набор | До | После |
|---|---:|---:|
| dev P@5 | 1.00 | 1.00 |
| test P@5 | 0.80 | 0.80 |

Свежий stdout банка: `oracle_checks: 36000`, `oracle_mismatches: []`, `simulated_attempts: 42000`.
[Полный результат matching](evidence/q1-recovery/stage_a_matching_results.json), [банка](evidence/q1-recovery/bank_v2_results.json).
Production VERSION matching-1.2.0 проверяется live smoke; совпадение весов с fixture — E4. Выбор на dev; holdout — 48 кандидатов / 8 запросов. Авторская синтетика, не внешняя экспертная разметка; рост P@5 не доказан. Эти ограничения и цифры присутствуют в VALIDATION/FOR_JURY.

## E6. Pck3 — хеши и health

```bash
npm --prefix apps/web run build
python3 docs/delivery/evidence/q1-recovery/check_deploy.py
```

```text

> fsp-reverse-hiring@1.0.0 build
> tsc -b && vite build

vite v6.4.4 building for production...
transforming...
✓ 55 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.44 kB │ gzip:  0.34 kB
dist/assets/index-x85TwcNR.css   19.36 kB │ gzip:  5.18 kB
dist/assets/index-DYn7UgI3.js   263.71 kB │ gzip: 79.67 kB
✓ built in 3.15s
```

```json
{
  "git_sha": "7f3dde4cbe5b17b0f16154e4ede90a91673428f8",
  "health": {
    "status": "ok",
    "demo": true,
    "version": "1.0.0"
  },
  "api_modules": 17,
  "worker_modules": 17,
  "web": [
    {
      "file": "assets/index-DYn7UgI3.js",
      "sha256": "8fc3107f9ef4386dae9f7684c86b091d9a0a41b105da4a3cd7149c935514b0ac",
      "container_equal": true,
      "https_equal": true
    },
    {
      "file": "assets/index-x85TwcNR.css",
      "sha256": "84e3e536817c07c4d727f5eb69d16b05a65f6d19b2886afb37730962853a8060",
      "container_equal": true,
      "https_equal": true
    },
    {
      "file": "index.html",
      "sha256": "60688c76c7276efdfc13774e9877f132fd3faf4ac626b4cda524b387ae2e2b48",
      "container_equal": true,
      "https_equal": true
    }
  ],
  "db_mount": [
    {
      "Type": "volume",
      "Name": "fsp-mvp_fsp_db",
      "Source": "/var/lib/docker/volumes/fsp-mvp_fsp_db/_data",
      "Destination": "/var/lib/postgresql/data",
      "Driver": "local",
      "Mode": "rw",
      "RW": true,
      "Propagation": ""
    }
  ]
}
```

Проверяющий скрипт assert-ит равенство каждого Python-файла workspace=git HEAD=container, каждого web-файла fresh build=container=public HTTPS и отсутствие diff apps/compose от HEAD. [Все SHA](evidence/q1-recovery/deploy.json). Последующие коммиты документов/проверок не изменяют runtime; проверенная версия приложения указана отдельно, без невозможного самоссылочного SHA протокола.

## E7. NOTTODO и границы изменений
- `demo/FSP_NIKITA_SUBMISSION.pptx` SHA256 `41e86f5eb8cc809facb6240f87c81fdb83f8d000a67cb80a4735eaa164e930f8`.
- `demo/FSP_MVP.pptx` SHA256 `8a88789e4e89e44c49bcf50c49086ac63d40301c025aa6ec5c6e216c6472cf9e`.

`git diff d4501b9 --name-only -- apps demo evaluation compose.yaml` вывел только `apps/web/src/App.tsx`. Презентация не редизайнилась, веса/банк не изменялись, новых IRT/функций продукта нет. Полное содержательное перечитывание архивных приложений и бинарных исходников не заявляется; целевое трёхпроходное ревью описано в [Q1_RECOVERY](../review/Q1_RECOVERY_2026-10-21.md).

## E8. Pck1/Pck2/Pck5 — честная упаковка

FOR_JURY содержательно проверен: URL стенда/ветки, три роли, 7 шагов маршрута, две воспроизведённые метрики, not_run и ссылка на аудит присутствуют. Три входа →200 в E2, общие аккаунты не менялись. Ссылки FOR_JURY/CHANGELOG/SUBMISSION_LINKS проверены через Path.exists: missing local links=[] для всех трёх.

CHANGELOG теперь описывает провал E3 из d4501b9 как историю, новый фикс, провал первого цикла и свежий результат второго; Q1–Q7 перечислены. Формулировка текущего закрытия ограничена техническими DoD, Pck2/Pck5 и человеческий протокол явно оставлены. SUBMISSION_LINKS не утверждает состоявшуюся отправку. Человеческие клетки не заполнены.

## E9. GitHub auth — реальный внешний блокер

```bash
GIT_TERMINAL_PROMPT=0 git push origin codex/fsp-mvp
```

```text
fatal: could not read Username for 'https://github.com': terminal prompts disabled
```

```text
git ls-remote origin refs/heads/codex/fsp-mvp
2e6d6daa5bfb59f6d5a7e7317aa41093c8f05980 refs/heads/codex/fsp-mvp
```

Push не выполнен, force-push не использовался. Pck2 PARTIAL только по этому внешнему шагу. Pck5 HUMAN_ONLY: на площадку ничего не отправлено.

## Матрица текущих вердиктов

| ID | Вердикт | Свежие доказательства |
|---|---|---|
| Q1 | PASS | E2; E3; E4 |
| Q2 | PASS | E2; E4 |
| Q3 | PASS | E2; E4 |
| Q4 | PASS | E2; E1 |
| Q5 | PASS | E2 |
| Q6 | PASS | E2; E4 |
| Q7 | PASS | E5; E4; E8 |
| Pck1 | PASS | E8 |
| Pck2 | PARTIAL | E2; E8; E9 |
| Pck3 | PASS | E6 |
| Pck4 | PASS | E2; E3 |
| Pck5 | HUMAN_ONLY | E8 |
| REG_FSP | PASS | E2; E4 |
| REG_ISO | PASS | E2; E1 |
| REG_OLD_SEL | PASS | E2 |
| NOTTODO | PASS | E7; E5; E8 |

14 PASS, 1 PARTIAL, 1 HUMAN_ONLY, **0 FAIL**. Цикл остановлен на второй итерации по условию пользователя.

## Чеклист §6 канона

| Пункт | Да/нет | Основание |
|---|---|---|
| Q1–Q3 закрыты или явно обоснован stop | ДА | Q1/Q2/Q3: свежие E2–E4 PASS. |
| Q7: новая VERSION + таблица на выборке в VALIDATION/for-jury | ДА | matching-1.2.0, dev 1→1 / holdout .8→.8, E5. |
| Q4–Q6: сделано или partial в changelog | ДА | Q4/Q5/Q6: E1/E2/E4 PASS. |
| Pck1–Pck3 | НЕТ | Pck1/Pck3 PASS; Pck2 PARTIAL только из-за отсутствия GitHub auth. |
| Pck4 smoke green | ДА | 18 групп PASS, включая отрицательный Q1; отдельная E3 PASS. |
| Pck5 ссылки ушли | НЕТ | Pck5 HUMAN_ONLY: человек не подтвердил отправку. |

Технические критерии закрыты; считать внешнюю сдачу состоявшейся нельзя. После публикации ветки и человеческого протокола остаётся отправка ссылок. SMTP, внешний ФСП, нагрузка, реальный недельный календарь, независимая экспертная разметка/человеческий пилот и полный аудит ACL не объявлены выполненными.

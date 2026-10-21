# Независимая проверка этапа A по объединённому канону

Дата (UTC): 2026-10-21T10:16:03.917754+00:00
Ветка: `codex/fsp-mvp` · проверенный HEAD: `feb67e508f83659cba60cf0c5de89cc16bf043cd`
Стенд: https://85-137-26-131.sslip.io/
Критерий: [COMPREHENSIVE_STAGE_A_2026-10-21.md](../final_backlog_2026-10-20/COMPREHENSIVE_STAGE_A_2026-10-21.md), SHA-256 `cd652c55e049b78e491ae682d5adbf3ebb208d0dc14a390e4b118179fc4827da`.

**STOP: критерии A не закрыты. Push + human сами по себе недостаточны.** Найден отрицательный сценарий Q1/B01. Pck4 FAIL по методике, даже при зелёном штатном smoke. Pck1 заявляет полное закрытие вопреки найденному сбою. Код продукта не изменялся; деплой и БД не пересоздавались. Требуется отдельный цикл исправления Q1 → повтор verify → актуальная упаковка → push → human → отправка.

## Основания и границы чтения

Порядок: рабочая версия COMPREHENSIVE → B01–B06/U01–U04 `findings.json` → BACKLOG → три обязательные методики контроля. Канон уже имел пользовательские изменения до начала; это **не** версия `git show HEAD`, её точный хеш указан выше. Старый PROMPT_ASTRA.md не открывался. Старые матрица и smoke-вердикты не использовались как доказательства. BACKLOG прочитан как исторические утверждения; его статусы не копировались. Изменены только три запрошенных документа проверки; BACKLOG и changelog сохранены, поэтому их прежние статусы не являются итогом этой сессии.

Содержательное чтение: критерии и accept; smoke; test_stage_a, test_bank, test_matching, conftest, test_employer_tasks; контактный lifecycle test_api; сохранение/submit в App.tsx; matching.py, tasks.py; оценочные скрипты и протоколы; FOR_JURY, CHANGELOG, SUBMISSION_LINKS, Stage A раздел VALIDATION, VERIFY_NOW, compose/Dockerfile. Три смысловых прохода проверки: требования → механизмы и границы существующих проверок → сопоставление свежего исполнения и контрпробы с accept. Это **не** заявление о полном трёхпроходном ревью первоначальных 8 тысяч файлов: разработка не выполнялась.

Автоматические проверки: pytest/PostgreSQL, браузер Chromium/HTTPS, численные симуляции, сборка, хеши. Бинарные PPTX проверены на неизменность, не просмотрены глазами. PDF в smoke разобран как текст для проверки контактов, не оценивалась вёрстка. Остальные исходные архивы/PDF задания/старые кадры аудита заново не рецензировались: заданный пользователем канон определяет объём текущей проверки. Хеширование не выдано за содержательное чтение.

Все PASS ниже относятся к указанному техническому DoD и данным, **не** означают, что human-шаг исполнен. Остатки SMTP, полного ACL-аудита, нагрузки, полного комплекта исходников и календарных семи дней не объявлены проверенными.

## E0. Окружение

Команды: `git branch --show-current`; `git rev-parse HEAD`; `git status --short`; `docker compose ps`; `curl -fsS https://85-137-26-131.sslip.io/api/health`.

```text
branch: codex/fsp-mvp
HEAD: feb67e508f83659cba60cf0c5de89cc16bf043cd
status: до проверки M docs/final_backlog_2026-10-20/COMPREHENSIVE_STAGE_A_2026-10-21.md; много пользовательских untracked docs/архивов и logs/; staged пуст.
api/db/web/edge: healthy; task-worker: Up
health: {"status":"ok","demo":true,"version":"1.0.0"}
```

Первоначальный `curl http://localhost:8000/health` завершился exit 7: этот порт не опубликован compose. Это ошибка адреса пробы, не падение стенда. Публичный правильный маршрут выше возвращает ok. Health `1.0.0` — версия приложения, не matching/bank и не git SHA.

Фиксация compose (без environment/секретов):

```json
{"Command":"\"sh -c 'alembic upgr…\"","CreatedAt":"2026-10-21 11:03:54 +0200 CEST","ExitCode":0,"Health":"healthy","ID":"94514e7c9bac","Image":"fsp-mvp-api","Labels":"com.docker.compose.config-hash=688647376cb13e02e257ac066b4e8200598cce832d992707679178b55713ec28,com.docker.compose.depends_on=,com.docker.compose.oneoff=False,com.docker.compose.project=fsp-mvp,com.docker.compose.project.working_dir=/root/hakaton,com.docker.compose.replace=api-1,com.docker.compose.service=api,com.docker.compose.version=2.40.3,com.docker.compose.container-number=1,com.docker.compose.image=sha256:2588633957d291e8eeb469ea772e507bab8ce5bfd01c08e0c9356f7748f18259,com.docker.compose.project.config_files=/root/hakaton/compose.yaml","LocalVolumes":"0","Mounts":"","Name":"fsp-mvp-api-1","Names":"fsp-mvp-api-1","Networks":"fsp-mvp_default","Ports":"","Project":"fsp-mvp","Publishers":[],"RunningFor":"About an hour ago","Service":"api","Size":"0B","State":"running","Status":"Up About an hour (healthy)"}
{"Command":"\"docker-entrypoint.s…\"","CreatedAt":"2026-10-07 22:42:58 +0200 CEST","ExitCode":0,"Health":"healthy","ID":"59f21df183b7","Image":"postgres:16-alpine@sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea","Labels":"com.docker.compose.config-hash=3bca2c73361f7055ca0a3bf65204956f97fb88d091f67c92d0ee1a2cd60c816d,com.docker.compose.container-number=1,com.docker.compose.oneoff=False,com.docker.compose.project=fsp-mvp,com.docker.compose.project.config_files=/root/hakaton/compose.yaml,com.docker.compose.version=2.40.3,com.docker.compose.depends_on=,com.docker.compose.image=sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea,com.docker.compose.project.working_dir=/root/hakaton,com.docker.compose.service=db","LocalVolumes":"1","Mounts":"fsp-mvp_fsp_db","Name":"fsp-mvp-db-1","Names":"fsp-mvp-db-1","Networks":"fsp-mvp_default","Ports":"127.0.0.1:5547-\u003e5432/tcp","Project":"fsp-mvp","Publishers":[{"URL":"127.0.0.1","TargetPort":5432,"PublishedPort":5547,"Protocol":"tcp"}],"RunningFor":"13 days ago","Service":"db","Size":"0B","State":"running","Status":"Up 9 days (healthy)"}
{"Command":"\"caddy run --config …\"","CreatedAt":"2026-10-11 21:17:18 +0200 CEST","ExitCode":0,"Health":"healthy","ID":"8051e4bdd372","Image":"caddy:2.11.7-alpine@sha256:d8542f48d34a9cf4e4c11a478865229840e87e4c96ea3f439101f31a5d35f75f","Labels":"com.docker.compose.project.config_files=/root/hakaton-fixes-20261011/compose.yaml,com.docker.compose.replace=edge-1,org.opencontainers.image.description=a powerful, enterprise-ready, open source web server with automatic HTTPS written in Go,org.opencontainers.image.licenses=Apache-2.0,org.opencontainers.image.source=https://github.com/caddyserver/caddy-docker,org.opencontainers.image.url=https://caddyserver.com,com.docker.compose.config-hash=55fbe568ac9fed665991290273fdb3766a4a8df6771e3b8471ae7e6fb915c368,com.docker.compose.container-number=1,com.docker.compose.project.working_dir=/root/hakaton-fixes-20261011,com.docker.compose.service=edge,com.docker.compose.version=2.40.3,org.opencontainers.image.documentation=https://caddyserver.com/docs,org.opencontainers.image.version=v2.11.7,org.opencontainers.image.title=Caddy,org.opencontainers.image.vendor=Light Code Labs,com.docker.compose.depends_on=,com.docker.compose.image=sha256:d8542f48d34a9cf4e4c11a478865229840e87e4c96ea3f439101f31a5d35f75f,com.docker.compose.oneoff=False,com.docker.compose.project=fsp-mvp","LocalVolumes":"2","Mounts":"/root/hakaton-…,fsp-mvp_fsp_tl…,fsp-mvp_fsp_tl…","Name":"fsp-mvp-edge-1","Names":"fsp-mvp-edge-1","Networks":"host","Ports":"","Project":"fsp-mvp","Publishers":[],"RunningFor":"9 days ago","Service":"edge","Size":"0B","State":"running","Status":"Up 9 days (healthy)"}
{"Command":"\"python -m fsp.task_…\"","CreatedAt":"2026-10-21 11:04:04 +0200 CEST","ExitCode":0,"Health":"","ID":"f281e32de7a7","Image":"fsp-mvp-task-worker","Labels":"com.docker.compose.config-hash=70f91d0293b15ec6b9c2fd5d3086ad3ab840578654939f9fd625ac357be38863,com.docker.compose.image=sha256:9df2e7e3c28439afb542d3189b2b0b52dde8dc2c3964f95ae57c66d9f4c829fc,com.docker.compose.project=fsp-mvp,com.docker.compose.replace=task-worker-1,com.docker.compose.service=task-worker,com.docker.compose.version=2.40.3,com.docker.compose.container-number=1,com.docker.compose.depends_on=api:service_healthy:false,com.docker.compose.oneoff=False,com.docker.compose.project.config_files=/root/hakaton/compose.yaml,com.docker.compose.project.working_dir=/root/hakaton","LocalVolumes":"0","Mounts":"","Name":"fsp-mvp-task-worker-1","Names":"fsp-mvp-task-worker-1","Networks":"fsp-mvp_default","Ports":"","Project":"fsp-mvp","Publishers":[],"RunningFor":"About an hour ago","Service":"task-worker","Size":"0B","State":"running","Status":"Up About an hour"}
{"Command":"\"/docker-entrypoint.…\"","CreatedAt":"2026-10-21 11:28:13 +0200 CEST","ExitCode":0,"Health":"healthy","ID":"f949f3a7baa0","Image":"fsp-mvp-web","Labels":"maintainer=NGINX Docker Maintainers \u003cdocker-maint@nginx.com\u003e,com.docker.compose.config-hash=f1e57e53508f5f3af5294ed5421d0bcc67f5457abbc69279a8df9b05bdfd205a,com.docker.compose.image=sha256:2899f13a7b78bc6c48c8bf4899e9b3f618e9da2404321ae2c9e14b99e2bc09bd,com.docker.compose.oneoff=False,com.docker.compose.project.config_files=/root/hakaton/compose.yaml,com.docker.compose.project.working_dir=/root/hakaton,com.docker.compose.service=web,com.docker.compose.container-number=1,com.docker.compose.depends_on=,com.docker.compose.project=fsp-mvp,com.docker.compose.replace=web-1,com.docker.compose.version=2.40.3","LocalVolumes":"0","Mounts":"","Name":"fsp-mvp-web-1","Names":"fsp-mvp-web-1","Networks":"fsp-mvp_default","Ports":"127.0.0.1:3080-\u003e80/tcp","Project":"fsp-mvp","Publishers":[{"URL":"127.0.0.1","TargetPort":80,"PublishedPort":3080,"Protocol":"tcp"}],"RunningFor":"43 minutes ago","Service":"web","Size":"0B","State":"running","Status":"Up 43 minutes (healthy)"}

```

Исходный полный status сохранён локально `/tmp/stage-a-independent/status-before.txt`; пользовательские файлы не включались в staging. Проверка использует изолированную `fsp_test`: существующая fixture очищает **тестовые** таблицы перед тестами. База продукта `fsp` и том `fsp-mvp_fsp_db` не удалялись. Live smoke и отдельная контрпроба создали по четыре вымышленные учётки; после выполнения их кандидаты скрыты, собственные grants сняты; чужие профили не менялись. Это не тест SMTP и не реальных людей.

## E1. Полный pytest — оба результата

```bash
python3 scripts/run_local.py .venv/bin/pytest -q tests
# exit 1: 40 failed, 57 passed, 2 warnings in 20.37s
# representative: profile PUT -> 401 {"detail":"Войдите в личный кабинет"}
COOKIE_SECURE=false python3 scripts/run_local.py .venv/bin/pytest -q tests
```

Причина первого прогона: run_local наследует COOKIE_SECURE=true HTTPS-стенда, а TestClient использует HTTP; secure cookie после login не посылается. Повтор задаёт флаг **только процессу тестов**, не меняет конфиг/код/деплой. Это ограничение команды README в данном окружении, а не основание скрыть первый красный результат.

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
97 passed, 2 warnings in 28.92s

```

## E2. Свежий live smoke

До запуска прочитан скрипт, чтобы понять его реальные assertions и побочные эффекты. Команда:

```bash
python3 scripts/run_local.py .venv/bin/python scripts/smoke_stage_a.py --out /tmp/stage-a-independent/smoke.json
```

Exit 0. Фактический вывод:

```json
{
  "status": "pass",
  "checked_at": "2026-10-21T10:10:42.839491+00:00",
  "base_url": "https://85-137-26-131.sslip.io",
  "checks": [
    "https_health_ok",
    "openapi_exact",
    "three_review_logins_ok",
    "Q1_navigation_reload_server_draft_owner_expiry",
    "Q2_live_bank_2_1_rounding_hint",
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

Включает API без confirm=409, браузер cancel/accept, expiry/owner/draft, банк 2.1.0, review-login 200, видимые суммы баллов, согласие/контакты/PDF, ФСП/грейд, снимки и resume. Но **не включает** провал сохранения и обязательное подтверждение ухода; поэтому 17 зелёных групп недостаточно для всего B01.

## E3. Независимая контрпроба Q1/B01 — воспроизведённый дефект

Сценарий в новом вымышленном аккаунте (на том же HTTPS, без изменения backend):

1. Сохранить `90,63` в первом ответе; убедиться в серверном сохранении.
2. Только для PUT `/api/me/attempts/*/answers` оборвать сеть средствами Playwright `route.abort()`; заменить ответ на `UNSAVED-123`.
3. Видно «Не удалось сохранить на сервере. Не закрывайте вкладку…»; на сервере остался `90,63`.
4. Обзор → Подтверждение навыков. Локально показан `UNSAVED-123`, но status пустой; уход не потребовал подтверждения.
5. Закрыть вкладку с `run_before_unload=True`; открыть новую в том же авторизованном browser context. Показан старый `90,63`, подтверждения не было.

Exit 0 контрпробы означает успешное воспроизведение **дефекта**, не PASS продукта:

```text
INDEPENDENT normal Q1 id/expiry stable: True
INDEPENDENT failed PUT: error visible; server answer: 90,63
INDEPENDENT after roundtrip: status= '' dialogs= []
INDEPENDENT reopen tab: answer reverted to 90,63 dialogs= []

```

Это не повтор исходного happy path B01: он теперь проходит. FAIL обусловлен уточнённым `accept[1]` из findings: «Неподтверждённое сохранение явно видно; уход с несохранёнными изменениями требует подтверждения». Предупреждение сначала есть, но исчезает после навигации, хотя сервер всё ещё не сохранил ответ. Поэтому базовый узкий DoD «ответ → Обзор → назад» выполнен, **полный** DoD с обязательным уточнением — нет. Ошибку нельзя закрыть одним human PASS обычного пути.

Воспроизведение без изменения tracked файлов: взять исходный `scripts/smoke_stage_a.py`, в его копии заменить участок от `rejected=c.request.post` до `dialogs=[]` следующим кодом (остальные bootstrap/cleanup оригинала сохранены):

```python
        print('INDEPENDENT normal Q1 id/expiry stable:', started['id']==call(c,'/me/attempts')[0]['id'], flush=True)
        page.route('**/api/me/attempts/*/answers', lambda route: route.abort())
        answer.fill('UNSAVED-123')
        expect(page.get_by_role('status')).to_contain_text('Не удалось сохранить на сервере')
        print('INDEPENDENT failed PUT: error visible; server answer:',call(c,'/me/attempts')[0]['answers']['1'],flush=True)
        prompted=[]
        page.on('dialog',lambda d:(prompted.append(d.message),d.dismiss()))
        nav(page,'Обзор');nav(page,'Подтверждение навыков')
        expect(answer).to_have_value('UNSAVED-123')
        print('INDEPENDENT after roundtrip: status=',repr(page.get_by_role('status').inner_text()),'dialogs=',prompted,flush=True)
        page.close(run_before_unload=True)
        page=c.new_page();page.goto(a.base_url);nav(page,'Подтверждение навыков')
        answer=page.get_by_label('Ответ на задание 1',exact=True)
        expect(answer).to_have_value('90,63')
        print('INDEPENDENT reopen tab: answer reverted to',answer.input_value(),'dialogs=',prompted,flush=True)
        browser.close()
        raise SystemExit(0)

```

Запуск копии: `python3 scripts/run_local.py .venv/bin/python /tmp/stage-a-independent/probe_draft.py`. Cleanup оригинального smoke выполняется через finally и при SystemExit. Для независимого ручного повторения есть H-Q1-network.

## E4. Отдельные целевые удары Q1–Q3, matching и периодичность

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
======================== 20 passed, 2 warnings in 7.92s ========================

```

Q2: сгенерирован именно 29/32 SQL Middle; 90.63 и 90,63 принимаются, 90.62 отклоняется новым банком, legacy 2.0.0 воспроизводит старый эталон. B02 допускает documented policy: старые попытки не пересчитывались (CHANGELOG Q2 и FOR_JURY). Q3: без/false confirm и whitespace →409, ответы/срок/active сохранены; explicit true завершает. UI `window.confirm` содержит число пропусков, их последствия и 24 часа. Идемпотентность сдачи проверяется в полном test_api. Q6: до границы выдачи нет; на границе четыре worker ticks не плодят дубли; после закрытия +100 дней не создаёт новую выдачу. Реальная неделя не ожидалась.

## E5. Q7 matching: новая VERSION и повторная выборка

Документированная процедура: `PYTHONPATH=apps/api:. .venv/bin/python evaluation/stage_a_matching.py`. В этой сессии `main()` запущен с перенаправлением только записи результата в `/tmp`, чтобы не менять evaluation. То же сделано для E6:

```python
from pathlib import Path
from unittest.mock import patch
from evaluation import stage_a_matching as m  # для E6: bank_v2_audit
original = Path.write_text
with patch.object(Path, 'write_text', lambda self, data, *a, **kw:
    original(Path('/tmp/stage-a-independent') / self.name, data, *a, **kw)):
    m.main()
```

Окружение: `PYTHONPATH=apps/api:. .venv/bin/python`. Свежий вывод и дополнительная sanity-проверка production:

```text
{"old_weights": [60, 15, 20, 5], "selected_weights": [30, 15, 45, 10], "selection": "max dev P@5; tie: minimum L1 distance to old weights, then tuple order"}
dev 1.0 -> 1.0
test 0.8 -> 0.8
VERSION matching-1.2.0 dev/test candidate ID overlap [] sizes 16 48
fixture sha256 0f4bb52e97a78d1326e6da2031303315dc6105461f59860fc3581402b3e50850
rank sanity 63.75 66.0 no sport 60.0
checkbox delta 0.0

```

Fixture содержит явные relevant_ids: 16 кандидатов/2 запроса dev, 48/8 holdout; ID не пересекаются. `git diff 2e6d6da HEAD -- evaluation/matching_fixtures.json` пуст. Сетка выбирается по dev; holdout используется только в последующем measure. Метки авторские/синтетические и давно известны проекту, поэтому нельзя называть набор новой слепой внешней валидацией. Отсутствие пересечения ID не доказывает независимость шаблонов. На текущем прогоне коэффициенты не подбирались вручную.

| Набор | До matching-1.1.0 | После matching-1.2.0 |
|---|---:|---:|
| dev P@5 | 1.00 | 1.00 |
| holdout P@5 | 0.80 | 0.80 |

VERSION bump независимо проверен `git diff 2e6d6da HEAD -- apps/api/fsp/matching.py`; живая API-выдача smoke требует methodology=matching-1.2.0. Production scoring сверяется с вычислителем выбранных весов на fixture в E4. Сильный тест+ФСП 66 > полное skill coverage с тестом 75% (63.75), без ФСП 60; непроверенный второй навык остаётся unknown. Чекбоксы самодекларации дают delta=0. Это соответствует направлению канона, **не** доказательство роста качества найма.

## E6. Качество банка на моделях ответов

Запущен `evaluation.bank_v2_audit.main()` с перенаправлением файла, как описано E5. Exit 0:

```text
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

36 000 независимых вычислений эталонов без расхождений; 42 000 синтетических попыток. Числа FOR_JURY воспроизведены. Человеческий пилот и реалистичность профессиональных грейдов этим не подтверждаются.

## E7. Pck3: совпадение деплоя с кодом

Свежая сборка: в `apps/web` выполнено `npm run build -- --outDir /tmp/stage-a-independent/web-dist`, exit 0:

```text

> fsp-reverse-hiring@1.0.0 build
> tsc -b && vite build --outDir /tmp/stage-a-independent/web-dist

vite v6.4.4 building for production...

(!) outDir /tmp/stage-a-independent/web-dist is not inside project root and will not be emptied.
Use --emptyOutDir to override.

transforming...
✓ 55 modules transformed.
rendering chunks...
computing gzip size...
../../../../tmp/stage-a-independent/web-dist/index.html                   0.44 kB │ gzip:  0.33 kB
../../../../tmp/stage-a-independent/web-dist/assets/index-x85TwcNR.css   19.36 kB │ gzip:  5.18 kB
../../../../tmp/stage-a-independent/web-dist/assets/index-CiUyEab4.js   261.76 kB │ gzip: 79.03 kB
✓ built in 2.30s

```

Проверка сравнивает содержимое, а не возраст контейнера: все `apps/api/fsp/*.py` и Python миграции с git HEAD и `/app/` в обоих api/worker; три свежесобранных web-файла с nginx-контейнером и публичным HTTPS. Исходники продукта не имеют diff относительно HEAD; documentation-only commit проверки не изменит этот факт. Runtime dependencies не выданы за побайтовое совпадение всех слоёв образа.

Воспроизводимый проверяющий код (`python3 /tmp/stage-a-independent/deploy.py`):

```python
import subprocess,json,hashlib,urllib.request
from pathlib import Path
h=lambda b:hashlib.sha256(b).hexdigest()
run=lambda *a:subprocess.check_output(a)
root=Path.cwd(); result={}
for service in ['api','task-worker']:
 files=sorted(Path('apps/api/fsp').glob('*.py'))+sorted(Path('apps/api/migrations').rglob('*.py'))
 rows=[]
 for f in files:
  deployed=run('docker','compose','exec','-T',service,'cat','/app/'+str(f.relative_to('apps/api')))
  committed=run('git','show','HEAD:'+str(f))
  rows.append({'file':str(f),'sha256':h(f.read_bytes()),'workspace_equals_HEAD':f.read_bytes()==committed,'deployed_equals_workspace':deployed==f.read_bytes()})
 result[service]=rows
assets=[]
for f in sorted(Path('/tmp/stage-a-independent/web-dist').rglob('*')):
 if not f.is_file():continue
 rel=str(f.relative_to('/tmp/stage-a-independent/web-dist'))
 deployed=run('docker','compose','exec','-T','web','cat','/usr/share/nginx/html/'+rel)
 public=urllib.request.urlopen('https://85-137-26-131.sslip.io/'+('' if rel=='index.html' else rel)).read()
 assets.append(dict(file=rel,sha256=h(f.read_bytes()),container_equal=f.read_bytes()==deployed,https_equal=f.read_bytes()==public))
result['web']=assets
result['product_diff_HEAD']=run('git','diff','HEAD','--','apps','compose.yaml').decode()
result['health']=json.load(urllib.request.urlopen('https://85-137-26-131.sslip.io/api/health'))
result['db_mount']=json.loads(run('docker','inspect','fsp-mvp-db-1','--format','{{json .Mounts}}'))
print(json.dumps(result,ensure_ascii=False,indent=2))
assert all(x['workspace_equals_HEAD'] and x['deployed_equals_workspace'] for s in ['api','task-worker'] for x in result[s])
assert all(x['container_equal'] and x['https_equal'] for x in assets)
assert result['product_diff_HEAD']==''
print('PASS deployed api/worker sources = HEAD; fresh build = container = public HTTPS assets')

```

Фактический вывод:

```text
{
  "api": [
    {
      "file": "apps/api/fsp/__init__.py",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/assessment.py",
      "sha256": "d5b30eab36bfdda4d978584be30b42fea6c0cea537dd55f1ee91da0a2e369b58",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/bank.py",
      "sha256": "d4bd2697d15a30f742be50d07faa1e4124fc2fec584337939105ebb90c5a5d16",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/formatting.py",
      "sha256": "8be015724ca30d94c9082bf7dac31e858e3880fab559de9ddee7dc775c789501",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/fsp_provider.py",
      "sha256": "5b119010cf47324fc619228204ad12763b8cb7cfefb8ad39336a204fe5b11b64",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/main.py",
      "sha256": "6e9e297743689b3018e8ee8d540a12325baee117e050cb6c49647c817d1a335b",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/matching.py",
      "sha256": "6f4b042f1d438eaefceae3c92717b3426c89913143c1d80dddaedf3b4b39ad43",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/models.py",
      "sha256": "5040873b582b60ac9729c5f1459555684a5e9ad6131ab54a8f391dac8d5491cd",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/outputs.py",
      "sha256": "2ec9c8e367979ccbf195a4223fc98510028fdf0178c8337d4e4ef5eec07871a6",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/pdf.py",
      "sha256": "b7b3148f019176c1ee9704eb3ccb49c809a36612ae0eed21482bef74ac69a68d",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/schemas.py",
      "sha256": "f8cd2f8fe464e3d3407ef07f1bbc12508fb84b4ad873d78825bd31baac573912",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/seed.py",
      "sha256": "9db892cab8be235b22f636d016c8d96a6f16c74395da8c9cfa8c2681aa8c60fc",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/task_worker.py",
      "sha256": "9dc4d9b97a9fec495ff08af98efc25428f3e7f92baf395f392a28bac661ee85f",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/tasks.py",
      "sha256": "258134a8ea6e3a126a2a365e790775db8fcf1e99df20f5ed3f7ebee186082b6e",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/migrations/env.py",
      "sha256": "d55c8957e9757b69f0eeb50ed59561d08e3ed2e01450dfbf4eaec99bcdd969e1",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/migrations/versions/b9e1c4d7a201_employer_tasks.py",
      "sha256": "99a5e43eb5c0ecc1e138c6bc2c0bc9bee6f29a8c07ba47b688322d5b4c43a80b",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/migrations/versions/f8a2ba6fc338_initial_schema.py",
      "sha256": "330315ddc103ceb0e3a497faf22d1207d9ee8b66bce5f05d2b81fb332bc3fdff",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    }
  ],
  "task-worker": [
    {
      "file": "apps/api/fsp/__init__.py",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/assessment.py",
      "sha256": "d5b30eab36bfdda4d978584be30b42fea6c0cea537dd55f1ee91da0a2e369b58",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/bank.py",
      "sha256": "d4bd2697d15a30f742be50d07faa1e4124fc2fec584337939105ebb90c5a5d16",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/formatting.py",
      "sha256": "8be015724ca30d94c9082bf7dac31e858e3880fab559de9ddee7dc775c789501",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/fsp_provider.py",
      "sha256": "5b119010cf47324fc619228204ad12763b8cb7cfefb8ad39336a204fe5b11b64",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/main.py",
      "sha256": "6e9e297743689b3018e8ee8d540a12325baee117e050cb6c49647c817d1a335b",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/matching.py",
      "sha256": "6f4b042f1d438eaefceae3c92717b3426c89913143c1d80dddaedf3b4b39ad43",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/models.py",
      "sha256": "5040873b582b60ac9729c5f1459555684a5e9ad6131ab54a8f391dac8d5491cd",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/outputs.py",
      "sha256": "2ec9c8e367979ccbf195a4223fc98510028fdf0178c8337d4e4ef5eec07871a6",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/pdf.py",
      "sha256": "b7b3148f019176c1ee9704eb3ccb49c809a36612ae0eed21482bef74ac69a68d",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/schemas.py",
      "sha256": "f8cd2f8fe464e3d3407ef07f1bbc12508fb84b4ad873d78825bd31baac573912",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/seed.py",
      "sha256": "9db892cab8be235b22f636d016c8d96a6f16c74395da8c9cfa8c2681aa8c60fc",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/task_worker.py",
      "sha256": "9dc4d9b97a9fec495ff08af98efc25428f3e7f92baf395f392a28bac661ee85f",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/fsp/tasks.py",
      "sha256": "258134a8ea6e3a126a2a365e790775db8fcf1e99df20f5ed3f7ebee186082b6e",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/migrations/env.py",
      "sha256": "d55c8957e9757b69f0eeb50ed59561d08e3ed2e01450dfbf4eaec99bcdd969e1",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/migrations/versions/b9e1c4d7a201_employer_tasks.py",
      "sha256": "99a5e43eb5c0ecc1e138c6bc2c0bc9bee6f29a8c07ba47b688322d5b4c43a80b",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    },
    {
      "file": "apps/api/migrations/versions/f8a2ba6fc338_initial_schema.py",
      "sha256": "330315ddc103ceb0e3a497faf22d1207d9ee8b66bce5f05d2b81fb332bc3fdff",
      "workspace_equals_HEAD": true,
      "deployed_equals_workspace": true
    }
  ],
  "web": [
    {
      "file": "assets/index-CiUyEab4.js",
      "sha256": "23fedeb2b2986c3b5c4e1b7df33a0a946156bfa3fecfb44b9dd9f0e1829794dc",
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
      "sha256": "d989c5ff9d1f4c42e822d100065b8d20559f7c6e42ca008c5fa743220c0a4bf1",
      "container_equal": true,
      "https_equal": true
    }
  ],
  "product_diff_HEAD": "",
  "health": {
    "status": "ok",
    "demo": true,
    "version": "1.0.0"
  },
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
PASS deployed api/worker sources = HEAD; fresh build = container = public HTTPS assets

```

## E8–E10. Упаковка, публикация, NOTTODO

E8: FOR_JURY прочитан целиком: URL стенда, ветка, 3 review-роли, две метрики, not_run, ссылка на findings, 7 шагов маршрута присутствуют. Все относительные ссылки из FOR_JURY/CHANGELOG существуют локально. Логины проверены E2 без изменения общих профилей. Содержательная проверка changelog видит Q1–Q7, ограничения реестра/почты и архив старого STOP. Но актуальная строка «Q1–Q7 и Pck3–Pck4: закрыты кодом и свежими автопроверками» теперь опровергнута E3. В delivery/SUBMISSION_LINKS также написано «Закрыты Q1–Q7». Эти файлы не исправлены в verify-only сессии; отправлять этот текст сейчас нельзя. PASS по структуре changelog не равен PASS честной упаковке.

E9, свежий read-only запрос:

```bash
git ls-remote https://github.com/ImmortalDR/CV_hakaton.git refs/heads/codex/fsp-mvp
```

```text
2e6d6daa5bfb59f6d5a7e7317aa41093c8f05980 refs/heads/codex/fsp-mvp
```

Ветка GitHub отстаёт от проверенного HEAD. Доступность push-auth в этой сессии не проверялась; старые заявления об отсутствии credentials не приняты как новый факт. Пользователь просил commit документов, push не выполнялся. Текст отправки проверен локально; внешняя форма/чат не отправлялись.

E10:

```bash
git diff --name-only 2e6d6da HEAD -- demo '*.pptx'
# пусто
sha256sum demo/*.pptx
```

```text
8a88789e4e89e44c49bcf50c49086ac63d40301c025aa6ec5c6e216c6472cf9e  demo/FSP_MVP.pptx
41e86f5eb8cc809facb6240f87c81fdb83f8d000a67cb80a4735eaa164e930f8  demo/FSP_NIKITA_SUBMISSION.pptx
```

Состав Stage A diff и прочитанные bank/matching/evaluation показывают текущий численный банк и перебор весов, не новый IRT pipeline. Дополнение tasks продолжает существующий стенд (предусмотрено Q6); не трактуется как новый вау-функционал. Новых продуктовых правок в этой сессии нет. Вместо питча выполнялась проверка Q; VPN/SSH не менялись, Amik-действий не было. SMTP/боевой ФСП не заявляются готовыми.

## Матрица решений

| ID | Вердикт | Основание |
|---|---|---|
| Q1 | FAIL | E2; E3; E4 |
| Q2 | PASS | E4; E2; docs/delivery/CHANGELOG_STAGE_A.md |
| Q3 | PASS | E2; E4; apps/web/src/App.tsx:1180 |
| Q4 | PASS | E2; E1 |
| Q5 | PASS | E2; E4 |
| Q6 | PASS | E2; E4 |
| Q7 | PASS | E5; E4; E6; docs/delivery/VALIDATION.md:147 |
| Pck1 | FAIL | E8; docs/delivery/CHANGELOG_STAGE_A.md |
| Pck2 | PARTIAL | E2; E8; E9 |
| Pck3 | PASS | E7; E0 |
| Pck4 | FAIL | E2; E3 |
| Pck5 | HUMAN_ONLY | docs/delivery/SUBMISSION_LINKS.md |
| REG_FSP | PASS | E2; E4 |
| REG_ISO | PASS | E2; E1 |
| REG_OLD_SEL | PASS | E2 |
| NOTTODO | PASS | E10; E5; E8 |

Полные DoD, уточнения, доказательства и остатки — [VERIFY_STAGE_A_MATRIX.json](VERIFY_STAGE_A_MATRIX.json). Итог: {'FAIL': 3, 'PASS': 11, 'PARTIAL': 1, 'HUMAN_ONLY': 1}.

## §6 канона: можно отправлять

| Пункт | Да/нет | Причина |
|---|---|---|
| Q1–Q3 закрыты или явно обоснован stop | НЕТ | Q1 FAIL; в changelog нет актуального STOP. Этот протокол вводит запрет отправки, а не заменяет закрытие Q1. |
| Q7: новая VERSION + таблица на выборке в VALIDATION/for-jury | ДА | matching-1.2.0; таблица 1→1/.8→.8 воспроизведена. |
| Q4–Q6: сделано или partial в changelog | ДА | Технические DoD PASS; человеческое прочтение UX и решение по календарному наблюдению остаются в протоколе. |
| Pck1–Pck3 | НЕТ | Pck1 FAIL, Pck2 PARTIAL; Pck3 PASS. |
| Pck4 smoke green | НЕТ | Штатный скрипт зелёный, но acceptance Pck4 FAIL из-за Q1. |
| Pck5 ссылки ушли | НЕТ | Подтверждения человека нет; отправки не было. |

«Явно обоснован stop» из §6 трактуется как честный запрет продолжения, а не разрешение отправлять известный дефект. Сам по себе STOP в этом отчёте не делает Q1 закрытым и не обновляет changelog. Итог отправки — НЕТ.

## Не выполнено / передача человеку

P-01…P-05: N/A, только этап B. SMTP registration email: NOT_RUN; полный server ACL: NOT_RUN вне перечисленных тестов; нагрузка: NOT_RUN; полный архив исходников сдачи: NOT_RUN; реальные 7 дней: HUMAN_ONLY. Human-протокол не заполнен за человека. Проверка доступности с ноутбука жюри и зрительной понятности UI ещё нужна, но не подменяет исправление Q1. Никакие старые «14 PASS» не переносятся.

Изменяются и коммитятся только VERIFY_STAGE_A_MATRIX.json, VERIFY_STAGE_A_PROTOCOL.md и HUMAN_VERIFY_PROTOCOL_STAGE_A.md. Сообщение коммита: `docs(verify): independent audit against comprehensive Stage A canon`. Проверенный продукт остаётся на указанном HEAD; новый commit содержит только документацию этой проверки.

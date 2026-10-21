# Независимый контроль этапа A
Дата UTC: 2026-10-21T08:50:21.295611+00:00
Проверенный HEAD: 84e697abeeac3cca21ae225fb1746ea02b1a46ff; ветка codex/fsp-mvp.
Сравнение Stage A: 2e6d6da..84e697abeeac3cca21ae225fb1746ea02b1a46ff. Итог: **STOP, отправлять нельзя**.
Вердикты: {"PASS": 9, "FAIL": 3, "PARTIAL": 3, "HUMAN_ONLY": 1}.

## Решение
Q3 FAIL: UI подтверждение работает, но прямой API submit без confirm завершает неполную попытку.
Это обязательный шаг Q3.B.2 из ASTRA_VERIFY_BY_TASK, более строгий, чем краткое описание UI в каноне.
Не называем это регрессией браузерной отмены: она подтверждена.
Pck4 FAIL по правилу Pck4.D: даже зелёный smoke не закрывает Q3 FAIL.
Pck2 PARTIAL: remote не содержит Stage A. Q4 FAIL (B05 повторён); Q5–Q6 PARTIAL с точными границами в матрице.
Код продукта и исходный smoke не менялись. Деплой/миграции/перезапуски не выполнялись. Pck5 не отправлялся.

## Область чтения и честные границы
Содержательно прочитаны канон (включая пользовательскую рабочую редакцию), B01–B06/U01–U04 findings,
backlog, оба актуальных verify/human промпта, GIT_WORKFLOW, STAGE_A_SMOKE, CHANGELOG,
FOR_JURY, VALIDATION, SUBMISSION_LINKS, весь smoke, stage_a_matching.py,
test_stage_a.py, test_employer_tasks.py, test_matching.py, conftest.py, assessment.py;
целевые участки main.py (draft/submit), App.tsx (submit/потребность), test_bank.py, tasks.py.
Порядок анализа: требования → реальные запросы/поведение → сопоставление DoD/пробелов.
Это узкая verify-сессия, не новый полный трёхпроходный аудит 8141 исходника и не разработка.
WORKSPACE_MAP/REVIEW_PROTOCOL прочитаны как контекст. Старый PROMPT_ASTRA.md не использован.
Оригиналы ТЗ/созвона, весь архив, полные остальные модули не перечитывались.
Хеши/regex/списки файлов — автоматические проверки, не содержательное чтение.
Бинарные PDF проверены извлечением текста в smoke; PPTX только хешом/диффом, визуально не просмотрен.
Кадры не снимались; визуальная оценка вынесена человеку.
Новая внешняя разметка, нагрузка, SMTP, официальный ФСП, семь реальных дней: NOT_RUN / вне сдачи A.

## Среда и сохранность
Начальная команда: git branch --show-current; git rev-parse HEAD; git status -sb;
curl -fsS https://85-137-26-131.sslip.io/api/health; docker compose ps.
Ветка codex/fsp-mvp, HEAD выше, origin ahead 11 до коммита проверки.
Health: {"status":"ok","demo":true,"version":"1.0.0"}.
Исходно уже изменён COMPREHENSIVE_STAGE_A_2026-10-21.md и множество untracked материалов.
Они не добавляются в коммит. Точный git status получен ниже до финальной записи документов.
Smoke, Q3 probe и Q4 probe создали по 4 вымышленных аккаунта; свои профили скрыты finally, записи не удалялись.
Общие review-аккаунты только логинились. Пароли новых аккаунтов остались в памяти.
Pytest использует отдельную fsp_test и очищает её таблицы штатной fixture TRUNCATE;
рабочая fsp и её volume не очищались. Это не доказательство отсутствия старых потерь данных.

## Воспроизведение и выводы
Все команды из /root/hakaton. Логи ниже вставлены целиком; старые логи не выдаются за свежие.

<a id="e-smoke"></a>
### smoke

Команда: python3 scripts/run_local.py .venv/bin/python scripts/smoke_stage_a.py --out /tmp/stage-a-verify/smoke.json

```text
{"status": "pass", "checked_at": "2026-10-21T08:46:07.686744+00:00", "base_url": "https://85-137-26-131.sslip.io", "checks": ["https_health_ok", "openapi_exact", "three_review_logins_ok", "Q1_navigation_reload_server_draft_owner_expiry", "Q2_live_bank_2_1_rounding_hint", "Q3_cancel_keeps_active_accept_completes", "invite_accept_addressed_contacts_PDF_isolation", "FSP_does_not_change_grade_zero_without_FSP", "old_snapshot_preserved", "Q5_filters_snapshot_and_score_UI", "Q6_live_7day_resume_no_duplicate", "Q4_hidden_overview_revoked_chat_snapshot_PDF", "mobile_no_horizontal_overflow"], "page_errors": [], "scope": "Live HTTPS API and Chromium; 4 newly bootstrapped fictional accounts, review logins read-only; no SMTP or real-person testing; own smoke candidate hidden, own plan closed."}

```

<a id="e-tests"></a>
### tests

Команда: COOKIE_SECURE=false python3 scripts/run_local.py .venv/bin/pytest tests -q

```text
........................................................................ [ 75%]
........................                                                 [100%]
=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/fastapi/testclient.py:1
  /root/hakaton/.venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

.venv/lib/python3.12/site-packages/starlette/testclient.py:53
  /root/hakaton/.venv/lib/python3.12/site-packages/starlette/testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
96 passed, 2 warnings in 39.21s

```

<a id="e-matching"></a>
### matching

Команда: PYTHONPATH=apps/api:. .venv/bin/python evaluation/stage_a_matching.py

```text
{"old_weights": [60, 15, 20, 5], "selected_weights": [30, 15, 45, 10], "selection": "max dev P@5; tie: minimum L1 distance to old weights, then tuple order"}
dev 1.0 -> 1.0
test 0.8 -> 0.8

```

<a id="e-bank"></a>
### bank

Команда: PYTHONPATH=apps/api:. .venv/bin/python evaluation/bank_v2_audit.py

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

<a id="e-build"></a>
### build

Команда: npm run build --prefix apps/web

```text

> fsp-reverse-hiring@1.0.0 build
> tsc -b && vite build

vite v6.4.4 building for production...
transforming...
✓ 55 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.44 kB │ gzip:  0.33 kB
dist/assets/index-x85TwcNR.css   19.36 kB │ gzip:  5.18 kB
dist/assets/index-D-5XLkcs.js   260.01 kB │ gzip: 78.61 kB
✓ built in 2.85s

```

<a id="e-q3"></a>
### q3

Команда: python3 scripts/run_local.py .venv/bin/python /tmp/stage-a-verify/q3_probe.py

```text
{"check": "Q3_submit_without_confirmation", "http_status": 200, "before_status": "active", "after_status": "completed", "answers_after_cancel": {"1": "90,63"}, "dialog": "Не заполнено 7 из 8 заданий. Завершить тест? Пропуски будут засчитаны как неверные ответы. Пересдача этого уровня — через 24 часа.", "same_attempt": true, "same_expiry": true}

```

<a id="e-deploy"></a>
### deploy

Команда: python3 /tmp/stage-a-verify/deploy_probe.py

```text
{
  "git_sha": "84e697abeeac3cca21ae225fb1746ea02b1a46ff",
  "health": {
    "status": "ok",
    "demo": true,
    "version": "1.0.0"
  },
  "api": {
    "hashes": {
      "fsp/schemas.py": "e775b1fd8db7e06aef0c9d8afd05db725a21f31df3cb4c8730c4d33378d3e6e8",
      "fsp/seed.py": "9db892cab8be235b22f636d016c8d96a6f16c74395da8c9cfa8c2681aa8c60fc",
      "fsp/formatting.py": "8be015724ca30d94c9082bf7dac31e858e3880fab559de9ddee7dc775c789501",
      "fsp/tasks.py": "258134a8ea6e3a126a2a365e790775db8fcf1e99df20f5ed3f7ebee186082b6e",
      "fsp/models.py": "5040873b582b60ac9729c5f1459555684a5e9ad6131ab54a8f391dac8d5491cd",
      "fsp/matching.py": "6f4b042f1d438eaefceae3c92717b3426c89913143c1d80dddaedf3b4b39ad43",
      "fsp/pdf.py": "b7b3148f019176c1ee9704eb3ccb49c809a36612ae0eed21482bef74ac69a68d",
      "fsp/assessment.py": "d5b30eab36bfdda4d978584be30b42fea6c0cea537dd55f1ee91da0a2e369b58",
      "fsp/outputs.py": "2ec9c8e367979ccbf195a4223fc98510028fdf0178c8337d4e4ef5eec07871a6",
      "fsp/task_worker.py": "9dc4d9b97a9fec495ff08af98efc25428f3e7f92baf395f392a28bac661ee85f",
      "fsp/bank.py": "d4bd2697d15a30f742be50d07faa1e4124fc2fec584337939105ebb90c5a5d16",
      "fsp/main.py": "56f0c20adf9050484e1c693bcc9cec3940e448ecbf1f3ed613f1589702728b3a",
      "fsp/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "fsp/fsp_provider.py": "5b119010cf47324fc619228204ad12763b8cb7cfefb8ad39336a204fe5b11b64"
    },
    "workspace_equal": true,
    "head_equal": true
  },
  "task-worker": {
    "hashes": {
      "fsp/schemas.py": "e775b1fd8db7e06aef0c9d8afd05db725a21f31df3cb4c8730c4d33378d3e6e8",
      "fsp/seed.py": "9db892cab8be235b22f636d016c8d96a6f16c74395da8c9cfa8c2681aa8c60fc",
      "fsp/formatting.py": "8be015724ca30d94c9082bf7dac31e858e3880fab559de9ddee7dc775c789501",
      "fsp/tasks.py": "258134a8ea6e3a126a2a365e790775db8fcf1e99df20f5ed3f7ebee186082b6e",
      "fsp/models.py": "5040873b582b60ac9729c5f1459555684a5e9ad6131ab54a8f391dac8d5491cd",
      "fsp/matching.py": "6f4b042f1d438eaefceae3c92717b3426c89913143c1d80dddaedf3b4b39ad43",
      "fsp/pdf.py": "b7b3148f019176c1ee9704eb3ccb49c809a36612ae0eed21482bef74ac69a68d",
      "fsp/assessment.py": "d5b30eab36bfdda4d978584be30b42fea6c0cea537dd55f1ee91da0a2e369b58",
      "fsp/outputs.py": "2ec9c8e367979ccbf195a4223fc98510028fdf0178c8337d4e4ef5eec07871a6",
      "fsp/task_worker.py": "9dc4d9b97a9fec495ff08af98efc25428f3e7f92baf395f392a28bac661ee85f",
      "fsp/bank.py": "d4bd2697d15a30f742be50d07faa1e4124fc2fec584337939105ebb90c5a5d16",
      "fsp/main.py": "56f0c20adf9050484e1c693bcc9cec3940e448ecbf1f3ed613f1589702728b3a",
      "fsp/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "fsp/fsp_provider.py": "5b119010cf47324fc619228204ad12763b8cb7cfefb8ad39336a204fe5b11b64"
    },
    "workspace_equal": true,
    "head_equal": true
  },
  "web": {
    "index.html": {
      "workspace": "d9b3c69dec8ea56ae0aa978a596031a169db5afe4ec995d11227b93c119711a3",
      "container": "d9b3c69dec8ea56ae0aa978a596031a169db5afe4ec995d11227b93c119711a3",
      "https": "d9b3c69dec8ea56ae0aa978a596031a169db5afe4ec995d11227b93c119711a3"
    },
    "assets/index-D-5XLkcs.js": {
      "workspace": "ab7bf4457cecd603a22eca7f90b76c7647bea0e72103195bfea70eb3c67ac71b",
      "container": "ab7bf4457cecd603a22eca7f90b76c7647bea0e72103195bfea70eb3c67ac71b",
      "https": "ab7bf4457cecd603a22eca7f90b76c7647bea0e72103195bfea70eb3c67ac71b"
    },
    "assets/index-x85TwcNR.css": {
      "workspace": "84e3e536817c07c4d727f5eb69d16b05a65f6d19b2886afb37730962853a8060",
      "container": "84e3e536817c07c4d727f5eb69d16b05a65f6d19b2886afb37730962853a8060",
      "https": "84e3e536817c07c4d727f5eb69d16b05a65f6d19b2886afb37730962853a8060"
    }
  },
  "web_all_equal": true,
  "db_mount": "[{\"Type\":\"volume\",\"Name\":\"fsp-mvp_fsp_db\",\"Source\":\"/var/lib/docker/volumes/fsp-mvp_fsp_db/_data\",\"Destination\":\"/var/lib/postgresql/data\",\"Driver\":\"local\",\"Mode\":\"rw\",\"RW\":true,\"Propagation\":\"\"}]",
  "source_diff_from_head": ""
}

```

<a id="e-remote"></a>
### remote

Команда: git ls-remote origin refs/heads/codex/fsp-mvp

```text
2e6d6daa5bfb59f6d5a7e7317aa41093c8f05980	refs/heads/codex/fsp-mvp

```

<a id="e-compose"></a>
### compose

Команда: docker compose ps

```text
NAME                    IMAGE                                                                                         COMMAND                  SERVICE       CREATED          STATUS                    PORTS
fsp-mvp-api-1           fsp-mvp-api                                                                                   "sh -c 'alembic upgr…"   api           35 minutes ago   Up 34 minutes (healthy)
fsp-mvp-db-1            postgres:16-alpine@sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea    "docker-entrypoint.s…"   db            13 days ago      Up 9 days (healthy)       127.0.0.1:5547->5432/tcp
fsp-mvp-edge-1          caddy:2.11.7-alpine@sha256:d8542f48d34a9cf4e4c11a478865229840e87e4c96ea3f439101f31a5d35f75f   "caddy run --config …"   edge          9 days ago       Up 9 days (healthy)
fsp-mvp-task-worker-1   fsp-mvp-task-worker                                                                           "python -m fsp.task_…"   task-worker   35 minutes ago   Up 34 minutes
fsp-mvp-web-1           fsp-mvp-web                                                                                   "/docker-entrypoint.…"   web           35 minutes ago   Up 34 minutes (healthy)   127.0.0.1:3080->80/tcp

```

<a id="e-docs"></a>
### docs

Команда: Проверка полей документов + git diff 2e6d6da..HEAD -- demo/ docs/presentation/ + SHA256 PPTX

```text
CHANGELOG Q1..Q7: {'Q1': True, 'Q2': True, 'Q3': True, 'Q4': True, 'Q5': True, 'Q6': True, 'Q7': True}
FOR_JURY required fields: {'https://85-137-26-131.sslip.io/': True, 'codex/fsp-mvp': True, 'review.candidate': True, 'review.employer': True, '0,80': True, '36 000': True, 'not_run': True, 'findings.json': True, 'CHANGELOG_STAGE_A.md': True}
Old attempts policy: - Q2: банк 2.1.0 использует явное округление половины вверх: 90,625 → 90,63. Старые попытки сохраняют исходные версии; массового пересчёта не было.
NOT TODO presentation diff bytes: 0
demo/FSP_NIKITA_SUBMISSION.pptx 41e86f5eb8cc809facb6240f87c81fdb83f8d000a67cb80a4735eaa164e930f8 base_equal True
demo/FSP_MVP.pptx 8a88789e4e89e44c49bcf50c49086ac63d40301c025aa6ec5c6e216c6472cf9e base_equal True
New code files in Stage A:
apps/api/fsp/assessment.py
apps/api/fsp/formatting.py
apps/api/fsp/task_worker.py
apps/api/fsp/tasks.py
apps/api/migrations/versions/b9e1c4d7a201_employer_tasks.py
apps/web/src/Tasks.tsx
apps/web/src/formatting.ts
apps/web/tests/formatting.test.mjs
evaluation/stage_a_matching.py
evaluation/stage_a_matching_results.json

Matching formula diff:
diff --git a/apps/api/fsp/matching.py b/apps/api/fsp/matching.py
index 818a4ac..9d15d62 100644
--- a/apps/api/fsp/matching.py
+++ b/apps/api/fsp/matching.py
@@ -2,7 +2,7 @@

 from .bank import GRADES

-VERSION = "matching-1.1.0"
+VERSION = "matching-1.2.0"


 def skill_coverage(facts):
@@ -31,7 +31,7 @@ def rank_candidate(candidate, criteria):
     facts = []
     evidence = {e["skill"]: e for e in candidate.get("evidence", [])}
     points = {}
-    for kind, weight in [("required_skills", 60), ("desired_skills", 15)]:
+    for kind, weight in [("required_skills", 30), ("desired_skills", 15)]:
         skills = criteria.get(kind, [])
         met = 0
         for s in skills:
@@ -72,8 +72,8 @@ def rank_candidate(candidate, criteria):
                 "evidence": None,
             }
         )
-    test = 0.2 * candidate.get("test_score", 0)
-    fsp = min(
+    test = 0.45 * candidate.get("test_score", 0)
+    fsp = 2 * min(
         5,
         sum(
             a.get("points", 0)

Runtime modified files vs HEAD: (none)

```

<a id="e-commits"></a>
### commits

Команда: git log -12 --oneline

```text
84e697a docs(handoff): record push authentication blocker before external submission
3e3c672 test(delivery): verify live Stage A flows and publish smoke evidence (Pck4)
f02b36d docs(deploy): record Stage A Compose rollout and source verification (Pck3)
ba34108 docs(delivery): package Stage A changelog and jury review path (Pck1-2)
555d69d fix(tasks): preserve schedule on resume and retain deployed platform (Q6)
9432225 feat(employer): preserve search context and explain candidate scores (Q5)
d9368d2 fix(privacy): align overview and chat with current consent (Q4)
3b7b230 feat(matching): validate evidence-focused weights on frozen labels (Q7)
e877ad7 fix(assessment): confirm submission with unanswered questions (Q3)
21dc314 fix(bank): version explicit half-up rounding rules (Q2)
8caf794 fix(assessment): persist active answers and restore drafts (Q1)
2e6d6da Report enriched-data experiments, limits and verified private model handoff

```

<a id="e-status"></a>
### status

Команда: git status -sb

```text
## codex/fsp-mvp...origin/codex/fsp-mvp [ahead 11]
 M docs/final_backlog_2026-10-20/COMPREHENSIVE_STAGE_A_2026-10-21.md
?? docs/00_START_HERE_TEAM_AND_AGENTS.md
?? docs/ASTRA_CODEX_RUNBOOK_STAGE_A.md
?? docs/BACKLOG_TASK2.md
?? docs/COMPREHENSIVE_STAGE_A_2026-10-21.md
?? docs/CONTROL_CHECKLIST.md
?? docs/FINALIST_PREP_PACK_2026-10-20.tgz
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
?? docs/delivery/VERIFY_STAGE_A_MATRIX.json
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

```

## Q3 probe: полный воспроизводимый исходник
Сохранить блок в /tmp/stage-a-verify/q3_probe.py. Исходный smoke не изменять.
```python
"""Live Stage A smoke. Adds isolated fictional users; never resets existing data.

Run through scripts/run_local.py for the deployment's DATABASE_URL. Credentials
stay in memory. Bootstrap verified demo users directly (SMTP is not tested),
then exercise deployed HTTPS API and browser. Only own smoke profile is hidden.
"""
import argparse
import json
import os
import secrets
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
import pymupdf
from playwright.sync_api import sync_playwright, expect
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session
from fsp.main import PASSWORDS
from fsp.models import User, Profile, Company, CompanyMember, Consent, Attempt, ContactGrant
from evaluation.oracles import solve

parser=argparse.ArgumentParser()
parser.add_argument('--base-url', default='https://85-137-26-131.sslip.io')
parser.add_argument('--out', default='docs/delivery/stage-a-smoke.json')
a=parser.parse_args(); engine=create_engine(os.environ['DATABASE_URL'])
checks=[]; errors=[]; run=uuid4().hex[:12]; accounts=[]
with Session(engine) as db:
    for role in ['candidate','employer','employer','candidate']:
        password=secrets.token_urlsafe(24)
        u=User(email=f'stage-a-{run}-{len(accounts)}@example.org',password_hash=PASSWORDS.hash(password),role=role,verified=True,demo=True)
        db.add(u);db.flush();db.add(Consent(user_id=u.id,processing=True,publication=role=='candidate'))
        if role=='candidate':
            db.add(Profile(user_id=u.id,name='Проверка этапа A · демо',processing=True,published=True,specialization='data',claimed_grade='Middle',skills=['sql','statistics'],phone='+7 000 000-00-00'))
        else:
            co=Company(name='Этап A · демо '+str(len(accounts)),description='Вымышленная компания для smoke этапа A',sector='ИТ',contact='smoke@example.org')
            db.add(co);db.flush();db.add(CompanyMember(user_id=u.id,company_id=co.id))
        accounts.append(dict(email=u.email,password=password,id=u.id))
    db.commit()

def pdf(response):
    assert response.status==200
    with pymupdf.open(stream=response.body(),filetype='pdf') as d: return ''.join(p.get_text() for p in d)

try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        actors=[]
        for creds in accounts:
            ctx=browser.new_context(base_url=a.base_url,locale='ru-RU',viewport={'width':1365,'height':1000},extra_http_headers={'X-Requested-With':'fsp-web'})
            r=ctx.request.post('/api/auth/login',data={k:creds[k] for k in ['email','password']});assert r.status==200
            page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));actors.append((ctx,page))
        (c,page),(e,hr),(other,_),(outsider,_)=actors
        def call(ctx,path,data=None,method=None):
            r=ctx.request.fetch('/api'+path,method=method or ('GET' if data is None else 'POST'),data=data)
            assert r.ok, (path,r.status,r.text()[:250])
            return r.json()
        def nav(p,name): p.locator('nav').get_by_role('button',name=name,exact=True).click()
        assert call(c,'/health')['status']=='ok'
        live=call(c,'/openapi.json'); assert live==json.loads(Path('docs/delivery/openapi.json').read_text())
        checks += ['https_health_ok','openapi_exact']
        # Published review credentials: read-only login check, no mutations.
        review=browser.new_context(base_url=a.base_url,extra_http_headers={'X-Requested-With':'fsp-web'})
        for email,password in [('review.candidate.fsp@example.org','Review-Cand-2026!'),('review.employer.fsp@example.org','Review-Emp-2026!'),('review.employer2.fsp@example.org','Review-Emp2-2026!')]:
            r=review.request.post('/api/auth/login',data=dict(email=email,password=password));assert r.status==200
        review.close();checks.append('three_review_logins_ok')
        page.goto(a.base_url);nav(page,'Подтверждение навыков')
        page.get_by_label('Уровень теста').select_option('Middle')
        page.get_by_role('button',name='Начать тест',exact=True).click()
        answer=page.get_by_label('Ответ на задание 1',exact=True);expect(answer).to_be_visible()
        answer.fill('90,63');expect(page.get_by_role('status').filter(has_text='Ответы сохранены')).to_be_visible()
        started=call(c,'/me/attempts')[0];assert started['version']=='2.1.0'
        assert any('90,625 → 90,63' in q['text'] for q in started['questions'])
        assert started['answers']['1']=='90,63' and started['result'] is None
        nav(page,'Обзор');nav(page,'Подтверждение навыков');expect(answer).to_have_value('90,63')
        page.reload();expect(answer).to_have_value('90,63')
        assert call(c,'/me/attempts')[0]['expires_at']==started['expires_at']
        assert outsider.request.put('/api/me/attempts/'+started['id']+'/answers',data={'answers':{'1':'999'}}).status==404
        checks+=['Q1_navigation_reload_server_draft_owner_expiry','Q2_live_bank_2_1_rounding_hint']
        dialogs=[]
        def dismiss(d): dialogs.append(d.message);d.dismiss()
        page.once('dialog',dismiss);page.get_by_role('button',name='Завершить и узнать результат').click()
        assert '7 из 8' in dialogs[0]
        assert call(c,'/me/attempts')[0]['status']=='active'
        before=call(c,'/me/attempts')[0]
        r=c.request.post('/api/me/attempts/'+started['id']+'/submit',data={'answers':{'1':'90,63'}})
        after=call(c,'/me/attempts')[0]
        print(json.dumps(dict(check='Q3_submit_without_confirmation',http_status=r.status,before_status=before['status'],after_status=after['status'],answers_after_cancel=before['answers'],dialog=dialogs[0],same_attempt=after['id']==before['id'],same_expiry=after['expires_at']==started['expires_at']),ensure_ascii=False))
        raise SystemExit(0)
finally:
    # Hide only the candidates created by this invocation, even on smoke failure.
    from fsp.tasks import suspend
    with Session(engine) as db:
        for item in accounts:
            profile=db.get(Profile,item['id'])
            if profile:
                profile.published=False
                db.add(Consent(user_id=item['id'],processing=True,publication=False))
                db.execute(delete(ContactGrant).where(ContactGrant.candidate_id==item['id']))
                suspend(db,item['id'])
        db.commit()
assert not errors,errors
report=dict(status='pass',checked_at=datetime.now(timezone.utc).isoformat(),base_url=a.base_url,checks=checks,page_errors=errors,
            scope='Live HTTPS API and Chromium; 4 newly bootstrapped fictional accounts, review logins read-only; no SMTP or real-person testing; own smoke candidate hidden, own plan closed.')
Path(a.out).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))

```

## Проверка деплоя: полный исходник
Сохранить в /tmp/stage-a-verify/deploy_probe.py.
```python
import subprocess,json,hashlib,pathlib,urllib.request
def cmd(*a): return subprocess.check_output(a,text=True).strip()
def sha(b): return hashlib.sha256(b).hexdigest()
out={'git_sha':cmd('git','rev-parse','HEAD'),'health':json.load(urllib.request.urlopen('https://85-137-26-131.sslip.io/api/health'))}
for service in ['api','task-worker']:
    code="import pathlib,hashlib,json;print(json.dumps({str(p.relative_to('/app')):hashlib.sha256(p.read_bytes()).hexdigest() for p in pathlib.Path('/app/fsp').glob('*.py')}))"
    remote=json.loads(cmd('docker','compose','exec','-T',service,'python','-c',code))
    local={p:sha(pathlib.Path('apps/api',p).read_bytes()) for p in remote}
    head={p:sha(subprocess.check_output(['git','show','HEAD:apps/api/'+p])) for p in remote}
    out[service]={'hashes':remote,'workspace_equal':remote==local,'head_equal':remote==head}
web={}
for p in pathlib.Path('apps/web/dist').rglob('*'):
    if p.is_file():
        rel=str(p.relative_to('apps/web/dist'))
        deployed=subprocess.check_output(['docker','compose','exec','-T','web','cat','/usr/share/nginx/html/'+rel])
        live=urllib.request.urlopen('https://85-137-26-131.sslip.io/'+('' if rel=='index.html' else rel)).read()
        web[rel]={'workspace':sha(p.read_bytes()),'container':sha(deployed),'https':sha(live)}
out['web']=web
out['web_all_equal']=all(len(set(x.values()))==1 for x in web.values())
out['db_mount']=cmd('docker','inspect','fsp-mvp-db-1','--format','{{json .Mounts}}')
out['source_diff_from_head']=cmd('git','diff','HEAD','--','apps','compose.yaml')
print(json.dumps(out,ensure_ascii=False,indent=2))

```

## Разбор по ID

### Q1 — PASS
Ответ → Обзор → назад → reload: ответы и исходная попытка/срок сохранены; состояние сохранения видно.

- Q1_navigation_reload_server_draft_owner_expiry
- same_attempt: true; same_expiry: true; answers_after_cancel: {"1":"90,63"}
- 96 passed; test_draft_answers_owner_lifecycle входит в прогон
Остаток: DoD в проверенном объёме закрыт; человеческие шаги не подменяются автоматикой.

### Q2 — PASS
Единое явное half-up; 90,625 → 90,63; версия и политика старых попыток.

- Q2_live_bank_2_1_rounding_hint
- 96 passed; test_half_up_exact_boundaries и test_conditional_rounding_new_and_historical_versions
- Банк 2.1.0; старые попытки сохраняют исходные версии; массового пересчёта не было.
- oracle_checks: 36000; oracle_mismatches: []
Остаток: DoD в проверенном объёме закрыт; человеческие шаги не подменяются автоматикой.

### Q3 — FAIL
N пустых из M, отмена сохраняет ответы, без подтверждения попытка не закрывается. Шаг B.2 требует API отказ/no-op без confirm.

- {"check": "Q3_submit_without_confirmation", "http_status": 200, "before_status": "active", "after_status": "completed", "answers_after_cancel": {"1": "90,63"}, "dialog": "Не заполнено 7 из 8 заданий. Завершить тест? Пропуски будут засчитаны как неверные ответы. Пересдача этого уровня — через 24 часа.", "same_attempt": true, "same_expiry": true}
- Q3_cancel_keeps_active_accept_completes
Остаток: Прямой POST submit с одним ответом и без confirm возвращает 200/completed. UI отмена работает; это невыполнение серверного пункта B.2, не потеря при UI отмене.

### Q4 — FAIL
Обзор согласован с публикацией; после отзыва нет активного диалога и ложной кнопки.

- Q4_hidden_overview_revoked_chat_snapshot_PDF
- 96 passed; проверки revoke/republication входят в прогон
Остаток: B05 воспроизведён: опубликованному подтверждённому Junior при 0 приглашений показывается «Подтвердите навыки и опубликуйте профиль». Дополнительно нет полного свежего UI-прогона четырёх состояний: новый/подтверждённый/скрытый/опубликованный; новой выдачи согласия после отзыва и оценки смысла кнопки.

### Q5 — PARTIAL
U01–U04: различимые анонимы, контекст фильтров, компактная форма, видимые вклады.

- Q5_filters_snapshot_and_score_UI
- 96 passed; test_anonymous_labels_distinct_and_stable; test_production_matches_selected_weights_on_frozen_sample
Остаток: Smoke не проверяет одинаковость ярлыка в приглашении/PDF, статус приглашения на карточке, scroll restoration, баннер изменённых параметров и арифметику видимой строки двух карточек. Форму прочитали, но не оценили глазами.

### Q6 — PARTIAL
7 дней: pause/resume не создаёт выдачу до срока, показанная дата соответствует логике.

- Q6_live_7day_resume_no_duplicate
- 96 passed; 6 тестов test_employer_tasks, включая 4 concurrent ticks, границу периода и закрытый план
Остаток: Живая API дата и число выдач проверены; текст даты в UI отдельно не сопоставлен. Реальные 7 календарных дней не ожидались.

### Q7 — PASS
Веса выбраны на размеченной выборке; VERSION bump; до/после в VALIDATION; test+ФСП сильнее чекбоксов.

- {"old_weights": [60, 15, 20, 5], "selected_weights": [30, 15, 45, 10], "selection": "max dev P@5; tie: minimum L1 distance to old weights, then tuple order"}
dev 1.0 -> 1.0
test 0.8 -> 0.8
- matching-1.1.0 → matching-1.2.0
- Live methodology == matching-1.2.0; FSP bonus +6, grade unchanged
- 96 passed; production scores checked on frozen sample
Остаток: DoD в проверенном объёме закрыт; человеческие шаги не подменяются автоматикой.

### Pck1 — PASS
Changelog узнаваемо перечисляет Q1–Q7 и ограничения.

- CHANGELOG Q1..Q7: all True; FOR_JURY links CHANGELOG_STAGE_A.md
Остаток: DoD в проверенном объёме закрыт; человеческие шаги не подменяются автоматикой.

### Pck2 — PARTIAL
For-jury: стенд, ветка, рабочие review-логины, 2 цифры, not_run, аудит, путь 10–15 минут.

- FOR_JURY required fields: all True
- three_review_logins_ok
- 2e6d6daa5bfb59f6d5a7e7317aa41093c8f05980	refs/heads/codex/fsp-mvp
Остаток: Remote ещё на 2e6d6da, новых документов/кода этапа A там нет; push не выполнен. Маршрут общих аккаунтов может упираться в cooldown.

### Pck3 — PASS
Health ok; api/web/worker соответствуют текущему прикладному HEAD.

- health ok; api/task-worker workspace_equal=head_equal=true; web_all_equal=true; source_diff_from_head=""
- NAME                    IMAGE                                                                                         COMMAND                  SERVICE       CREATED          STATUS                    PORTS
fsp-mvp-api-1           fsp-mvp-api                                                                                   "sh -c 'alembic upgr…"   api           35 minutes ago   Up 34 minutes (healthy)
fsp-mvp-db-1            postgres:16-alpine@sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea    "docker-entrypoint.s…"   db            13 days ago      Up 9 days (healthy)       127.0.0.1:5547->5432/tcp
fsp-mvp-edge-1          caddy:2.11.7-alpine@sha256:d8542f48d34a9cf4e4c11a478865229840e87e4c96ea3f439101f31a5d35f75f   "caddy run --config …"   edge          9 days ago       Up 9 days (healthy)
fsp-mvp-task-worker-1   fsp-mvp-task-worker                                                                           "python -m fsp.task_…"   task-worker   35 minutes ago   Up 34 minutes
fsp-mvp-web-1           fsp-mvp-web                                                                                   "/docker-entrypoint.…"   web           35 minutes ago   Up 34 minutes (healthy)   127.0.0.1:3080->80/tcp
Остаток: DoD в проверенном объёме закрыт; человеческие шаги не подменяются автоматикой.

### Pck4 — FAIL
Свежий smoke плюс Q1–Q3 без FAIL, адресное согласие, ФСП и изоляция.

- {"status": "pass", "checked_at": "2026-10-21T08:46:07.686744+00:00", "base_url": "https://85-137-26-131.sslip.io", "checks": ["https_health_ok", "openapi_exact", "three_review_logins_ok", "Q1_navigation_reload_server_draft_owner_expiry", "Q2_live_bank_2_1_rounding_hint", "Q3_cancel_keeps_active_accept_completes", "invite_accept_addressed_contacts_PDF_isolation", "FSP_does_not_change_grade_zero_without_FSP", "old_snapshot_preserved", "Q5_filters_snapshot_and_score_UI", "Q6_live_7day_resume_no_duplicate", "Q4_hidden_overview_revoked_chat_snapshot_PDF", "mobile_no_horizontal_overflow"], "page_errors": [], "scope": "Live HTTPS API and Chromium; 4 newly bootstrapped fictional accounts, review logins read-only; no SMTP or real-person testing; own smoke candidate hidden, own plan closed."}
- POST без confirm: 200 active → completed
Остаток: Скрипт зелёный (13 групп), но не проверяет серверный confirm. По правилу Pck4.D при Q3 FAIL итог Pck4 не может быть PASS.

### Pck5 — HUMAN_ONLY
Человек отправил ссылки на прежнюю площадку.

- SUBMISSION_LINKS.md: Pck5 — текст для человека (не отправлено)
Остаток: Факт отправки отсутствует. До исправления must-блокера отправлять нельзя.

### REG_FSP — PASS
Без ФСП категория сохраняется, бонус не меняет грейд.

- FSP_does_not_change_grade_zero_without_FSP
- 96 passed; test_unknown_never_becomes_proof_and_sport_does_not_change_category
Остаток: DoD в проверенном объёме закрыт; человеческие шаги не подменяются автоматикой.

### REG_ISO — PASS
Контакты/PDF только конкретной компании после согласия; чужой кандидат denied.

- invite_accept_addressed_contacts_PDF_isolation; чужой кандидат 403; другая компания PDF без email
Остаток: DoD в проверенном объёме закрыт; человеческие шаги не подменяются автоматикой.

### REG_OLD_SEL — PASS
После нового запроса старый snapshot существует; текущая приватность соблюдается.

- old_snapshot_preserved; Q4_hidden_overview_revoked_chat_snapshot_PDF
Остаток: DoD в проверенном объёме закрыт; человеческие шаги не подменяются автоматикой.

### NOTTODO — PASS
Нет редизайна презентации, нового IRT pipeline или обещаний боевого ФСП/SMTP.

- CHANGELOG Q1..Q7: {'Q1': True, 'Q2': True, 'Q3': True, 'Q4': True, 'Q5': True, 'Q6': True, 'Q7': True}
FOR_JURY required fields: {'https://85-137-26-131.sslip.io/': True, 'codex/fsp-mvp': True, 'review.candidate': True, 'review.employer': True, '0,80': True, '36 000': True, 'not_run': True, 'findings.json': True, 'CHANGELOG_STAGE_A.md': True}
Old attempts policy: - Q2: банк 2.1.0 использует явное округление половины вверх: 90,625 → 90,63. Старые попытки сохраняют исходные версии; массового пересчёта не было.
NOT TODO presentation diff bytes: 0
demo/FSP_NIKITA_SUBMISSION.pptx 41e86f5eb8cc809facb6240f87c81fdb83f8d000a67cb80a4735eaa164e930f8 base_equal True
demo/FSP_MVP.pptx 8a88789e4e89e44c49bcf50c49086ac63d40301c025aa6ec5c6e216c6472cf9e base_equal True
New code files in Stage A:
apps/api/fsp/assessment.py
apps/api/fsp/formatting.py
apps/api/fsp/task_worker.py
apps/api/fsp/tasks.py
apps/api/migrations/versions/b9e1c4d7a201_employer_tasks.py
apps/web/src/Tasks.tsx
apps/web/src/formatting.ts
apps/web/tests/formatting.test.mjs
evaluation/stage_a_matching.py
evaluation/stage_a_matching_results.json

Matching formula diff:
diff --git a/apps/api/fsp/matching.py b/apps/api/fsp/matching.py
index 818a4ac..9d15d62 100644
--- a/apps/api/fsp/matching.py
+++ b/apps/api/fsp/matching.py
@@ -2,7 +2,7 @@

 from .bank import GRADES

-VERSION = "matching-1.1.0"
+VERSION = "matching-1.2.0"


 def skill_coverage(facts):
@@ -31,7 +31,7 @@ def rank_candidate(candidate, criteria):
     facts = []
     evidence = {e["skill"]: e for e in candidate.get("evidence", [])}
     points = {}
-    for kind, weight in [("required_skills", 60), ("desired_skills", 15)]:
+    for kind, weight in [("required_skills", 30), ("desired_skills", 15)]:
         skills = criteria.get(kind, [])
         met = 0
         for s in skills:
@@ -72,8 +72,8 @@ def rank_candidate(candidate, criteria):
                 "evidence": None,
             }
         )
-    test = 0.2 * candidate.get("test_score", 0)
-    fsp = min(
+    test = 0.45 * candidate.get("test_score", 0)
+    fsp = 2 * min(
         5,
         sum(
             a.get("points", 0)

Runtime modified files vs HEAD: (none)
Остаток: DoD в проверенном объёме закрыт; человеческие шаги не подменяются автоматикой.

## Интерпретация Q7
Dev: 16 профилей/2 запроса; holdout: 48/8, другие ID. Авторские синтетические labels, внешних экспертов 0.
Скрипт выбирает только по dev с фиксированной сеткой и tie-break; test измеряется после выбора.
Свежий запуск подтверждает процедуру, но не может доказать, что автор никогда прежде не видел holdout.
P@5 dev 1 → 1, test 0.8 → 0.8; улучшение не заявляем.
Тест production_matches_selected_weights проверяет production формулу на fixture.
Исторический 90.62 не переписан: новые задания 2.1.0 half-up, старые попытки со своей версией.

## Передача
[Матрица](VERIFY_STAGE_A_MATRIX.json) · [Человеческий протокол](HUMAN_VERIFY_PROTOCOL_STAGE_A.md).
Нужен отдельный разрешённый цикл исправления Q3 и повтор проверки Q3/Pck4; затем push и проверка ссылок,
заполнение протокола человеком и только после этого Pck5.
Коммит проверки меняет лишь документацию/JSON; прикладной SHA остаётся указанным выше.

<a id="e-q4"></a>
## Дополнительное воспроизведение B05: FAIL Q4
Команда: python3 scripts/run_local.py .venv/bin/python /tmp/stage-a-verify/q4_probe.py

```json
{"check": "B05_confirmed_published_empty_invitations", "verified_grade": "Junior", "published": true, "invitation_count": 0, "stale_hint": true, "text": "Демонстрационный стенд. Данные примеров и достижения ФСП — синтетические.\nОТ ПРЕДЛОЖЕНИЯ К ЗНАКОМСТВУ\nПриглашения\n\nИзучите условия до начала общения. При принятии контакты получит только пригласившая компания.\n\nПока нет приглашений\n\nПодтвердите навыки и опубликуйте профиль, чтобы работодатели могли вас найти."}
```
Полный исходник воспроизведения (копия smoke, не изменение продукта):
```python
"""Live Stage A smoke. Adds isolated fictional users; never resets existing data.

Run through scripts/run_local.py for the deployment's DATABASE_URL. Credentials
stay in memory. Bootstrap verified demo users directly (SMTP is not tested),
then exercise deployed HTTPS API and browser. Only own smoke profile is hidden.
"""
import argparse
import json
import os
import secrets
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
import pymupdf
from playwright.sync_api import sync_playwright, expect
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session
from fsp.main import PASSWORDS
from fsp.models import User, Profile, Company, CompanyMember, Consent, Attempt, ContactGrant
from evaluation.oracles import solve

parser=argparse.ArgumentParser()
parser.add_argument('--base-url', default='https://85-137-26-131.sslip.io')
parser.add_argument('--out', default='docs/delivery/stage-a-smoke.json')
a=parser.parse_args(); engine=create_engine(os.environ['DATABASE_URL'])
checks=[]; errors=[]; run=uuid4().hex[:12]; accounts=[]
with Session(engine) as db:
    for role in ['candidate','employer','employer','candidate']:
        password=secrets.token_urlsafe(24)
        u=User(email=f'stage-a-{run}-{len(accounts)}@example.org',password_hash=PASSWORDS.hash(password),role=role,verified=True,demo=True)
        db.add(u);db.flush();db.add(Consent(user_id=u.id,processing=True,publication=role=='candidate'))
        if role=='candidate':
            db.add(Profile(user_id=u.id,name='Проверка этапа A · демо',processing=True,published=True,specialization='data',claimed_grade='Middle',skills=['sql','statistics'],phone='+7 000 000-00-00'))
        else:
            co=Company(name='Этап A · демо '+str(len(accounts)),description='Вымышленная компания для smoke этапа A',sector='ИТ',contact='smoke@example.org')
            db.add(co);db.flush();db.add(CompanyMember(user_id=u.id,company_id=co.id))
        accounts.append(dict(email=u.email,password=password,id=u.id))
    db.commit()

def pdf(response):
    assert response.status==200
    with pymupdf.open(stream=response.body(),filetype='pdf') as d: return ''.join(p.get_text() for p in d)

try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        actors=[]
        for creds in accounts:
            ctx=browser.new_context(base_url=a.base_url,locale='ru-RU',viewport={'width':1365,'height':1000},extra_http_headers={'X-Requested-With':'fsp-web'})
            r=ctx.request.post('/api/auth/login',data={k:creds[k] for k in ['email','password']});assert r.status==200
            page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));actors.append((ctx,page))
        (c,page),(e,hr),(other,_),(outsider,_)=actors
        def call(ctx,path,data=None,method=None):
            r=ctx.request.fetch('/api'+path,method=method or ('GET' if data is None else 'POST'),data=data)
            assert r.ok, (path,r.status,r.text()[:250])
            return r.json()
        def nav(p,name): p.locator('nav').get_by_role('button',name=name,exact=True).click()
        assert call(c,'/health')['status']=='ok'
        live=call(c,'/openapi.json'); assert live==json.loads(Path('docs/delivery/openapi.json').read_text())
        checks += ['https_health_ok','openapi_exact']
        # Published review credentials: read-only login check, no mutations.
        review=browser.new_context(base_url=a.base_url,extra_http_headers={'X-Requested-With':'fsp-web'})
        for email,password in [('review.candidate.fsp@example.org','Review-Cand-2026!'),('review.employer.fsp@example.org','Review-Emp-2026!'),('review.employer2.fsp@example.org','Review-Emp2-2026!')]:
            r=review.request.post('/api/auth/login',data=dict(email=email,password=password));assert r.status==200
        review.close();checks.append('three_review_logins_ok')
        page.goto(a.base_url);nav(page,'Подтверждение навыков')
        page.get_by_label('Уровень теста').select_option('Middle')
        page.get_by_role('button',name='Начать тест',exact=True).click()
        answer=page.get_by_label('Ответ на задание 1',exact=True);expect(answer).to_be_visible()
        answer.fill('90,63');expect(page.get_by_role('status').filter(has_text='Ответы сохранены')).to_be_visible()
        started=call(c,'/me/attempts')[0];assert started['version']=='2.1.0'
        assert any('90,625 → 90,63' in q['text'] for q in started['questions'])
        assert started['answers']['1']=='90,63' and started['result'] is None
        nav(page,'Обзор');nav(page,'Подтверждение навыков');expect(answer).to_have_value('90,63')
        page.reload();expect(answer).to_have_value('90,63')
        assert call(c,'/me/attempts')[0]['expires_at']==started['expires_at']
        assert outsider.request.put('/api/me/attempts/'+started['id']+'/answers',data={'answers':{'1':'999'}}).status==404
        checks+=['Q1_navigation_reload_server_draft_owner_expiry','Q2_live_bank_2_1_rounding_hint']
        dialogs=[]
        def dismiss(d): dialogs.append(d.message);d.dismiss()
        page.once('dialog',dismiss);page.get_by_role('button',name='Завершить и узнать результат').click()
        assert '7 из 8' in dialogs[0]
        assert call(c,'/me/attempts')[0]['status']=='active'
        page.once('dialog',lambda d:d.accept());page.get_by_role('button',name='Завершить и узнать результат').click()
        expect(page.get_by_role('button',name='К выбору уровня')).to_be_visible()
        assert call(c,'/me/attempts')[0]['status']=='completed'
        checks.append('Q3_cancel_keeps_active_accept_completes')
        # New lower-level attempt, answers from an independent solver (not human skill).
        attempt=call(c,'/me/attempts',{'grade':'Junior'})
        with Session(engine) as db: qs=db.get(Attempt,attempt['id']).questions
        result=call(c,'/me/attempts/'+attempt['id']+'/submit',{'answers':{q['id']:str(solve(q)) for q in qs}})
        assert result['result']['passed']
        before=call(c,'/me/profile');cid=accounts[0]['id']
        page.reload();nav(page,'Приглашения')
        expect(page.get_by_text('Пока нет приглашений',exact=True)).to_be_visible()
        text=page.locator('main').inner_text()
        print(json.dumps(dict(check='B05_confirmed_published_empty_invitations',verified_grade=before['verified_grade'],published=before['published'],invitation_count=len(call(c,'/invitations')),stale_hint='Подтвердите навыки и опубликуйте профиль' in text,text=text),ensure_ascii=False))
        raise SystemExit(0)
finally:
    # Hide only the candidates created by this invocation, even on smoke failure.
    from fsp.tasks import suspend
    with Session(engine) as db:
        for item in accounts:
            profile=db.get(Profile,item['id'])
            if profile:
                profile.published=False
                db.add(Consent(user_id=item['id'],processing=True,publication=False))
                db.execute(delete(ContactGrant).where(ContactGrant.candidate_id==item['id']))
                suspend(db,item['id'])
        db.commit()
assert not errors,errors
report=dict(status='pass',checked_at=datetime.now(timezone.utc).isoformat(),base_url=a.base_url,checks=checks,page_errors=errors,
            scope='Live HTTPS API and Chromium; 4 newly bootstrapped fictional accounts, review logins read-only; no SMTP or real-person testing; own smoke candidate hidden, own plan closed.')
Path(a.out).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))

```

## Завершение процессов проверки
Все шесть фоновых процессов завершились с exit_code=0:
smoke (96327), pytest (6837), matching+bank (99120), build (33683),
Q3 probe (63881), Q4 probe (42853).
Exit 0 у probe означает успешное воспроизведение и запись наблюдения; это НЕ PASS продукта.
Проверка структуры: 16 уникальных ID; все human_checks_required представлены полными шагами;
все ссылки evidence ведут к существующим якорям этого протокола.
git diff --check: exit 0. git diff --name-only -- apps scripts evaluation: пусто.
Не выполнены push и отправка формы. Оригинальные пользовательские изменения не включены.

Staged diff обнаружил конечные пробелы Markdown и вывода Compose; они убраны при оформлении. Содержимое доказательств не менялось.

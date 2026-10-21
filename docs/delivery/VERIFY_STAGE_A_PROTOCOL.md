# Контроль цикла Stage A — 21.10.2026

Исправление и проверка одним агентом по явному поручению пользователя; это не независимая экспертная оценка. Предыдущий протокол сохранён в git (ceb37df).

## Iteration 1

SHA: 839930f. Сборка и deploy api/web/task-worker, без пересоздания БД.

```text
 Container fsp-mvp-api-1  Recreate
 Container fsp-mvp-api-1  Recreated
 Container fsp-mvp-web-1  Recreate
 Container fsp-mvp-task-worker-1  Recreate
 Container fsp-mvp-web-1  Recreated
 Container fsp-mvp-task-worker-1  Recreated
 Container fsp-mvp-api-1  Starting
 Container fsp-mvp-api-1  Started
 Container fsp-mvp-api-1  Waiting
 Container fsp-mvp-api-1  Waiting
 Container fsp-mvp-api-1  Healthy
 Container fsp-mvp-web-1  Starting
 Container fsp-mvp-api-1  Healthy
 Container fsp-mvp-task-worker-1  Starting
 Container fsp-mvp-task-worker-1  Started
 Container fsp-mvp-web-1  Started
 Container fsp-mvp-api-1  Waiting
 Container fsp-mvp-task-worker-1  Waiting
 Container fsp-mvp-web-1  Waiting
 Container fsp-mvp-api-1  Healthy
 Container fsp-mvp-task-worker-1  Healthy
 Container fsp-mvp-web-1  Healthy

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
97 passed, 2 warnings in 31.74s

{"status": "pass", "checked_at": "2026-10-21T09:02:17.804910+00:00", "base_url": "https://85-137-26-131.sslip.io", "checks": ["https_health_ok", "openapi_exact", "three_review_logins_ok", "Q1_navigation_reload_server_draft_owner_expiry", "Q2_live_bank_2_1_rounding_hint", "Q3_direct_API_without_confirm_409_active_draft_unchanged", "Q3_cancel_keeps_active_accept_completes", "Q4_verified_published_hidden_empty_invitations_and_overview_CTA", "Q5_anonymous_label_selection_invitation_PDF_UI", "invite_accept_addressed_contacts_PDF_isolation", "FSP_does_not_change_grade_zero_without_FSP", "old_snapshot_preserved", "Q5_two_visible_score_sums_unique_labels_changed_banner_scroll", "Q5_filters_snapshot_and_score_UI", "Q6_live_7day_resume_no_duplicate_UI_date_equals_API", "Q4_hidden_overview_revoked_chat_snapshot_PDF", "mobile_no_horizontal_overflow"], "page_errors": [], "scope": "Live HTTPS API and Chromium; 4 newly bootstrapped fictional accounts, review logins read-only; no SMTP or real-person testing; own smoke candidate hidden, own plan closed."}
```

Q3/Q4/Q6 закрыты свежим прогоном. Q5 FAIL: содержательная сверка U01 выявила отсутствие статуса приглашения в карточке. Следующая итерация исправляет его.

## Iteration 2 — итог

Два полных цикла build/deploy; во втором три запуска smoke (первые два остановились на SQL-локаторе). Продукт исправлен в 839930f и 8af82c4. Финальный smoke-локатор ограничен полем формы SQL; проверки не удалены. Итог: 14 PASS, 0 FAIL, 1 PARTIAL (Pck2, только push), 1 HUMAN_ONLY (Pck5).

Q5/U01: карточка показывает последний статус и дату приглашения, переход к приглашениям; после закрытия формы отправки список статусов обновляется. Live-проверка видит «Отправлено» до принятия и «Принято» после него. Ярлык до раскрытия совпадает в подборке, приглашении, PDF и UI. Q4: новый профиль без имени, неподтверждённый, подтверждённый скрытый и опубликованный; публикация через UI обновляет CTA и пустое приглашение без повторного входа. Q5: один список навыков, контекст свёрнут, два видимых балла арифметически согласованы, уникальные обозначения, баннер изменения параметров, восстановление scroll. Q6: строка следующей даты совпала с API с московским часовым поясом; pytest включает границы управляемого времени и конкурентные тики.

Смена контракта Q3 обнаружила шесть старых тестов, намеренно пропускавших вопрос; в них добавлено явное подтверждение. Проверки оценок 75/87.5 и прежних версий сохранены. Отдельный новый тест проверяет отказ без флага/с false, whitespace, сохранность draft/result/expiry и завершение с true. Первый промежуточный pytest: 6 failed, 91 passed; два последующих полных прогона: 97 passed.

Проверенный прикладной SHA: `8af82c45184c4c5821137ebc02b2b2f7f12e24b4`. Последующий коммит evidence/локатора не меняет apps.

## e-build

```sh
docker compose build api web task-worker; docker compose up -d --no-deps --wait api web task-worker
```

```text
85TwcNR.css   19.36 kB │ gzip:  5.15 kB
#34 12.04 dist/assets/index-B9FXyoib.js   261.54 kB │ gzip: 79.29 kB
#34 12.04 ✓ built in 3.21s
#34 12.08 npm notice
#34 12.08 npm notice New major version of npm available! 10.9.9 -> 12.2.0
#34 12.08 npm notice Changelog: https://github.com/npm/cli/releases/tag/v12.2.0
#34 12.08 npm notice To update run: npm install -g npm@12.2.0
#34 12.08 npm notice
#34 DONE 12.1s

#35 [web stage-1 2/3] COPY nginx.conf /etc/nginx/conf.d/default.conf
#35 CACHED

#36 [web stage-1 3/3] COPY --from=build /app/dist /usr/share/nginx/html
#36 DONE 0.0s

#37 [web] exporting to image
#37 exporting layers 0.1s done
#37 exporting manifest sha256:dc618cbb2541983754cbdc8ed014743aa522617d2a1ca8e8cc1f46377bf84ff4 done
#37 exporting config sha256:a0258125d9be4d9c0c40f5dc492c3b9047792847faf748bdd8ca630aa83424d5 done
#37 exporting attestation manifest sha256:221229026d2c81ba1f0f3972bca6bfb7fdaff6f7900b56103b6b50ee1877be5a 0.0s done
#37 exporting manifest list sha256:e58da9ae8ec03d7463c9905dadf622f0268d95e410ca23c5dc88f1ea11c1da53 done
#37 naming to docker.io/library/fsp-mvp-web:latest done
#37 unpacking to docker.io/library/fsp-mvp-web:latest 0.0s done
#37 DONE 0.2s

#38 [web] resolving provenance for metadata file
#38 DONE 0.0s
 api  Built
 task-worker  Built
 web  Built

 Container fsp-mvp-api-1  Recreate
 Container fsp-mvp-api-1  Recreated
 Container fsp-mvp-web-1  Recreate
 Container fsp-mvp-task-worker-1  Recreate
 Container fsp-mvp-web-1  Recreated
 Container fsp-mvp-task-worker-1  Recreated
 Container fsp-mvp-api-1  Starting
 Container fsp-mvp-api-1  Started
 Container fsp-mvp-api-1  Waiting
 Container fsp-mvp-api-1  Waiting
 Container fsp-mvp-api-1  Healthy
 Container fsp-mvp-api-1  Healthy
 Container fsp-mvp-web-1  Starting
 Container fsp-mvp-task-worker-1  Starting
 Container fsp-mvp-web-1  Started
 Container fsp-mvp-task-worker-1  Started
 Container fsp-mvp-api-1  Waiting
 Container fsp-mvp-task-worker-1  Waiting
 Container fsp-mvp-web-1  Waiting
 Container fsp-mvp-api-1  Healthy
 Container fsp-mvp-task-worker-1  Healthy
 Container fsp-mvp-web-1  Healthy
```

## e-tests

```sh
COOKIE_SECURE=false python3 scripts/run_local.py .venv/bin/pytest tests -q
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
97 passed, 2 warnings in 29.20s
```

## e-web

```sh
npm run build --prefix apps/web; node apps/web/tests/formatting.test.mjs
```

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
dist/assets/index-B9FXyoib.js   261.54 kB │ gzip: 79.00 kB
✓ built in 2.19s
55 Russian numeral assertions passed
```

## e-smoke

```sh
python3 scripts/run_local.py .venv/bin/python scripts/smoke_stage_a.py
```

```text
{"status": "pass", "checked_at": "2026-10-21T09:06:35.443189+00:00", "base_url": "https://85-137-26-131.sslip.io", "checks": ["https_health_ok", "openapi_exact", "three_review_logins_ok", "Q1_navigation_reload_server_draft_owner_expiry", "Q2_live_bank_2_1_rounding_hint", "Q3_direct_API_without_confirm_409_active_draft_unchanged", "Q3_cancel_keeps_active_accept_completes", "Q4_verified_published_hidden_empty_invitations_and_overview_CTA", "Q5_anonymous_label_selection_invitation_PDF_UI", "invite_accept_addressed_contacts_PDF_isolation", "FSP_does_not_change_grade_zero_without_FSP", "old_snapshot_preserved", "Q5_two_visible_score_sums_unique_labels_changed_banner_scroll", "Q5_filters_snapshot_and_score_UI", "Q6_live_7day_resume_no_duplicate_UI_date_equals_API", "Q4_hidden_overview_revoked_chat_snapshot_PDF", "mobile_no_horizontal_overflow"], "page_errors": [], "scope": "Live HTTPS API and Chromium; 4 newly bootstrapped fictional accounts, review logins read-only; no SMTP or real-person testing; own smoke candidate hidden, own plan closed."}
```

## e-deploy

```sh
python3 /tmp/verify_deploy.py (алгоритм ниже)
```

```text
{"checked_at": "2026-10-21T09:04:44.697489+00:00", "git_sha": "8af82c45184c4c5821137ebc02b2b2f7f12e24b4", "api": {"module_count": 14, "workspace_equal": true, "head_equal": true}, "task-worker": {"module_count": 14, "workspace_equal": true, "head_equal": true}, "web": {"file_count": 3, "all_equal": true}, "health": {"status": "ok", "demo": true, "version": "1.0.0"}, "services": [{"Service": "api", "ID": "94514e7c9bac", "State": "running", "Health": "healthy", "Mounts": "", "CreatedAt": "2026-10-21 11:03:54 +0200 CEST"}, {"Service": "db", "ID": "59f21df183b7", "State": "running", "Health": "healthy", "Mounts": "fsp-mvp_fsp_db", "CreatedAt": "2026-10-07 22:42:58 +0200 CEST"}, {"Service": "edge", "ID": "8051e4bdd372", "State": "running", "Health": "healthy", "Mounts": "fsp-mvp_fsp_tl…,/root/hakaton-…,fsp-mvp_fsp_tl…", "CreatedAt": "2026-10-11 21:17:18 +0200 CEST"}, {"Service": "task-worker", "ID": "f281e32de7a7", "State": "running", "Health": "", "Mounts": "", "CreatedAt": "2026-10-21 11:04:04 +0200 CEST"}, {"Service": "web", "ID": "8dc983d594a0", "State": "running", "Health": "healthy", "Mounts": "", "CreatedAt": "2026-10-21 11:04:04 +0200 CEST"}], "presentation_unchanged": true, "source_diff_from_head": ""}
```

## e-matching

```sh
python3 scripts/run_local.py .venv/bin/python evaluation/stage_a_matching.py
```

```text
{"old_weights": [60, 15, 20, 5], "selected_weights": [30, 15, 45, 10], "selection": "max dev P@5; tie: minimum L1 distance to old weights, then tuple order"}
dev 1.0 -> 1.0
test 0.8 -> 0.8
```

## e-docs

```sh
python3 /tmp/check_stage_docs.py (проверка наличия полей, не оценка смысла)
```

```text
{
  "changelog": {
    "Q1": true,
    "Q2": true,
    "Q3": true,
    "Q4": true,
    "Q5": true,
    "Q6": true,
    "Q7": true
  },
  "for_jury": {
    "https://85-137-26-131.sslip.io/": true,
    "codex/fsp-mvp": true,
    "review.candidate": true,
    "review.employer": true,
    "0,80": true,
    "36 000": true,
    "not_run": true,
    "findings.json": true,
    "CHANGELOG_STAGE_A.md": true
  },
  "old_attempt_policy": "- Q2: банк 2.1.0 использует явное округление половины вверх: 90,625 → 90,63. Старые попытки сохраняют исходные версии; массового пересчёта не было.",
  "presentation_changed": ""
}
```

## e-push

```sh
GIT_TERMINAL_PROMPT=0 git push origin codex/fsp-mvp; git ls-remote origin refs/heads/codex/fsp-mvp
```

```text
fatal: could not read Username for 'https://github.com': terminal prompts disabled
2e6d6daa5bfb59f6d5a7e7317aa41093c8f05980	refs/heads/codex/fsp-mvp
```

Сверка деплоя: SHA256 каждого apps/api/fsp/*.py сравнен с git show и с fsp/*.py через docker compose exec -T api/task-worker python; 14 модулей у каждого. Каждый файл apps/web/dist сравнен sha256sum с /usr/share/nginx/html через web; 3 файла. Машинный результат — stage-a-loop-deploy.json. БД: тот же ID 59f21df183b7 и том fsp-mvp_fsp_db, created 7 октября. В командах deploy нет db/down/reset. Pytest использует отдельную fsp_test, рабочую fsp не очищает.

## Промежуточные неуспешные smoke

```text
Traceback (most recent call last):
  File "/root/hakaton/scripts/smoke_stage_a.py", line 161, in <module>
    expect(hr.get_by_label('SQL',exact=True)).to_have_count(1)
  File "/root/hakaton/.venv/lib/python3.12/site-packages/playwright/sync_api/_generated.py", line 19493, in to_have_count
    self._sync(self._impl_obj.to_have_count(count=count, timeout=timeout))
  File "/root/hakaton/.venv/lib/python3.12/site-packages/playwright/_impl/_sync_base.py", line 115, in _sync
    return task.result()
           ^^^^^^^^^^^^^
  File "/root/hakaton/.venv/lib/python3.12/site-packages/playwright/_impl/_assertions.py", line 348, in to_have_count
    await self._expect_impl(
  File "/root/hakaton/.venv/lib/python3.12/site-packages/playwright/_impl/_assertions.py", line 74, in _expect_impl
    raise AssertionError(
AssertionError: Locator expected to have count '1'
Actual value: 0
Call log:
  - LocatorAssertions.to_have_count with timeout 5000ms
  - waiting for get_by_label("SQL", exact=True)
    9 × locator resolved to 0 elements
      - unexpected value "0"

```
```text
Traceback (most recent call last):
  File "/root/hakaton/scripts/smoke_stage_a.py", line 161, in <module>
    expect(hr.get_by_label('SQL',exact=False)).to_have_count(1)
  File "/root/hakaton/.venv/lib/python3.12/site-packages/playwright/sync_api/_generated.py", line 19493, in to_have_count
    self._sync(self._impl_obj.to_have_count(count=count, timeout=timeout))
  File "/root/hakaton/.venv/lib/python3.12/site-packages/playwright/_impl/_sync_base.py", line 115, in _sync
    return task.result()
           ^^^^^^^^^^^^^
  File "/root/hakaton/.venv/lib/python3.12/site-packages/playwright/_impl/_assertions.py", line 348, in to_have_count
    await self._expect_impl(
  File "/root/hakaton/.venv/lib/python3.12/site-packages/playwright/_impl/_assertions.py", line 74, in _expect_impl
    raise AssertionError(
AssertionError: Locator expected to have count '1'
Actual value: 2
Call log:
  - LocatorAssertions.to_have_count with timeout 5000ms
  - waiting for get_by_label("SQL")
    9 × locator resolved to 2 elements
      - unexpected value "2"

```

## Границы и отправка

Условие остановки пользователя выполнено: в must нет FAIL, только разрешённый push-PARTIAL Pck2. Этап A технически проверен; опубликованной сдачей считать нельзя до push, проверки ссылок и отправки человеком. H-PUSH = HUMAN_ONLY, Pck5 = HUMAN_ONLY. Боевые SMTP/ФСП, человеческий пилот и реальные 7 дней не проверялись; человеческий протокол сохраняет выбор принятия управляемого времени или отложенного наблюдения.

Содержательное ревью отделено от автоматических asserts: docs/review/STAGE_A_LOOP_2026-10-21.md. Презентация не менялась (git diff demo/*.pptx пуст); SMTP-WIP не переносился; пользовательский канон и untracked материалы не включены. Полного нового аудита исходных архивов/бинарных материалов не заявляем. Финальные human-галочки остаются незаполненными.

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

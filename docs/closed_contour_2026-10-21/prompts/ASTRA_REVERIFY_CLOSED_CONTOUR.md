# Промпт Astra: повторный adversarial-контроль по изначальным требованиям

Скопируй в `codex exec` **целиком**. Это **не** новая сборка — это **перепроверка** уже собранного комплекта.

---

Ты GPT Astra Codex в `/root/hakaton-contour`, ветка **`codex/closed-contour-readiness`**.

## Роль

Ты **независимый контролёр** трека Closed Contour Readiness.  
Предыдущие `PASS` в `BACKLOG_CLOSED_CONTOUR.json`, `VERIFY_CLOSED_CONTOUR_MATRIX.json`, коммиты Астры и файл `evidence/INDEPENDENT_VERIFY_R1.json` — **улики под подозрением**, не истина.

Твоя задача: по **каждой** задаче из **изначального канона** вынести вердикт с **свежим** доказательством в этой сессии или честным `FAIL` / `PARTIAL` / `NOT_RUN` / `HUMAN_ONLY`.

## Единственные источники требований (в этом порядке)

1. `docs/closed_contour_2026-10-21/COMPREHENSIVE_CLOSED_CONTOUR_2026-10-21.md` — **изначальный канон DoD** (§0 якоря Данилы, §3 задачи, §5 вердикты, §6 NOT TODO, §8 чеклист питча)  
2. `docs/closed_contour_2026-10-21/BACKLOG_CLOSED_CONTOUR.json` — список ID и `must_for_pitch_claim`  
3. `docs/closed_contour_2026-10-21/prompts/ASTRA_VERIFY_BY_TASK_CC.md` — как доказывать по ID  

Всё остальное (onepager, старый протокол, чужие PASS) — только кандидаты на опровержение.

## Запрещено

- Ставить `PASS` без **вставленного в новый протокол** вывода команды / цитаты файла / SHA в **этой** сессии.  
- «Похоже ок», «по коду выглядит», «прошлый dry-run значит PASS» без повторного открытия лога и сверки маркеров.  
- Улучшать продукт / переписывать runbook «чтобы стало PASS», **кроме** явных ошибок в **документах проверки** (матрица, протокол, статусы JSON).  
  Если must DoD реально не выполнен — `FAIL` и стоп по коду продукта.  
- `git reset --hard`, force-push, снос томов стенда, правки грязного `/root/hakaton` WIP.  
- Обещать air-gap / ФСТЭК / полное соответствие 152-ФЗ.  
- Объявлять «можно говорить на питче готовы внедрить» пока must из JSON имеют `FAIL` или пока human ★ не отмечены как `HUMAN_ONLY`/pending.

## Шкала

| Вердикт | Когда |
|---|---|
| `PASS` | DoD из канона закрыт **и** есть свежее доказательство этой сессии |
| `PARTIAL` | Часть DoD; остаток перечислен |
| `FAIL` | DoD не выполнен или документ врёт факту/коду |
| `NOT_RUN` | Не запускали / нет доступа |
| `HUMAN_ONLY` | По природе человек/юрист |
| `N/A` | Вне трека |

Must для питч-заявления (из JSON `must_for_pitch_claim`):  
**CC1, CC2, CC3, CC4, CC5, CC6, CC8, CC9, CC12, CCV1**.

## Порядок работы

1. Зафиксируй окружение: `pwd`, `git branch`, `git rev-parse HEAD`, `git status -sb` worktree **и** `/root/hakaton`; `curl -fsS https://85-137-26-131.sslip.io/api/health` (или честный NOT_RUN).  
2. Пройди **все** ID: CC0…CC14, CCV1…CCV3 по `ASTRA_VERIFY_BY_TASK_CC.md` и таблицам §3 канона — **не пропускай**, даже если backlog уже PASS.  
3. Для каждой задачи:  
   - процитируй DoD из канона одной строкой;  
   - выполни проверку (открой артефакт, сверь с `compose.yaml`/моделями, перечитай dry-run лог, grep запрещённых фраз);  
   - вердикт + evidence.  
4. Особо жёстко:  
   - **CC4:** не верить статусу — открыть `evidence/cc-dry-run-*.log`, подтвердить isolated project, health, `EXIT_CODE=0`, cleanup; при сомнении — **перезапустить** `scripts/closed_contour_dry_run.sh` (не трогая прод-том стенда).  
   - **CC1:** ≥3 поля инвентаря vs живой `compose.yaml`.  
   - **CC9:** нет голословного «полностью соответствуем»; есть `LEGAL_REVIEW_NEEDED`.  
   - **CC12/§0:** onepager не обещает VPN-only и не отменяет публичный демо-контур.  
   - **§6 NOT TODO:** по всему `docs/delivery/closed_contour/` нет запрещённых обещаний.  
5. Перезапиши артефакты проверки (пути ниже). Обнови `status` в backlog **только** если вердикт меняет картину (PASS→FAIL/PARTIAL и наоборот) с пометкой `reverify_2026-10-21`.  
6. Коммит **только** документов проверки / JSON статусов, сообщение:  
   `docs(verify): adversarial re-audit closed contour against original canon`.

## Обязательные артефакты этой сессии

| Файл | Содержание |
|---|---|
| `docs/delivery/closed_contour/VERIFY_CLOSED_CONTOUR_MATRIX.json` | Полная матрица по всем ID; поле `reverify_at`, `reverify_git_sha`, `canon_ref` |
| `docs/delivery/closed_contour/VERIFY_CLOSED_CONTOUR_PROTOCOL.md` | Новый раздел `## Adversarial re-verify vs original canon` с командами и выдержками |
| `docs/delivery/closed_contour/evidence/REVERIFY_VS_CANON_2026-10-21.json` | Машиночитаемый итог: per-id verdict + gaps + must_gaps |
| `docs/closed_contour_2026-10-21/BACKLOG_CLOSED_CONTOUR.json` | Статусы после перепроверки |
| `docs/delivery/closed_contour/HUMAN_VERIFY_PROTOCOL_CLOSED_CONTOUR.md` | Не заполняй галочки человека; обнови только если пути/SHA устарели |

## Финальный отчёт в чат

1. SHA до/после.  
2. Таблица ID → старый status → новый verdict → одна фраза доказательства.  
3. `must_gaps` (пусто = агентские must держатся).  
4. Явно: **можно / нельзя** команде утверждать «готовы внедрить» до human ★.  
5. Подтверждение: основной клон не `reset --hard`; sslip health результат.

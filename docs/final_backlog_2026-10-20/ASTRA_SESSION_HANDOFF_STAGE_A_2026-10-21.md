# Handoff: сессия Astra / этап A — 21.10.2026

**Для кого:** люди команды + любой ИИ-агент, который продолжает сдачу.\
**Один файл = карта «что уже сделано / какой ценой / где ошибались / что осталось человеку».**

| Поле | Значение |
|---|---|
| Команда | Нанотехнологический альянс |
| Репо | `ImmortalDR/CV_hakaton` |
| Ветка сдачи | `codex/fsp-mvp` |
| База до сессии (remote) | `2e6d6da` |
| HEAD на VPS после сессии | `889ebf3` (docs verify r2); прикладной код стенда ≈ `7f3dde4` / `ab915af` |
| Стенд | https://85-137-26-131.sslip.io/ |
| Канон плана | `COMPREHENSIVE_STAGE_A_2026-10-21.md` |
| VPS корень | `/root/hakaton` |
| SMTP-WIP (не в сдаче) | ветка `wip/smtp-demo-mode-20261021` @ `47d8769` |
| Push на GitHub | **не выполнен** (нет auth на сервере) |
| Pck5 (отправка на площадку) | **не выполнен** |

Локальная копия артефактов:\
`session_reviews/hackathons/fsp/server_delivery_2026-10-21/`\
Git-bundle всех коммитов сессии:\
`server_delivery_2026-10-21/codex-fsp-mvp-stage-a.bundle`

---

## 0. За 60 секунд (человек)

1. На стенде уже крутится доработанный этап A (Q1–Q7 + упаковка + деплой + расширенный smoke).\
2. Независимые проверки Astra по канону в конце: **14 PASS**, **Pck2 PARTIAL** (нет push), **Pck5 HUMAN_ONLY**.\
3. **Слать экспертам ещё нельзя**, пока: `git push origin codex/fsp-mvp` → глаза по human-протоколу → вставка `SUBMISSION_LINKS.md` на площадку.\
4. Протокол глазами: [`HUMAN_VERIFY_PROTOCOL_STAGE_A.md`](server_delivery_2026-10-21/HUMAN_VERIFY_PROTOCOL_STAGE_A.md) (полный текст также §9 ниже).

---

## 1. Карточка для ИИ-агента (не пересобирай MVP)

```yaml
task: stage_A_silent_submission_fsp
do_not_use: PROMPT_ASTRA.md   # greenfield MVP — запрещён
canon: docs/final_backlog_2026-10-20/COMPREHENSIVE_STAGE_A_2026-10-21.md
branch: codex/fsp-mvp
stand: https://85-137-26-131.sslip.io/
remote_behind: true   # origin ещё на 2e6d6da пока нет push
last_independent_verify: independent_r2 @ 889ebf3
matrix: docs/delivery/VERIFY_STAGE_A_MATRIX.json
human_protocol: docs/delivery/HUMAN_VERIFY_PROTOCOL_STAGE_A.md
remaining_must_human:
  - git push origin codex/fsp-mvp
  - fill HUMAN_VERIFY_PROTOCOL_STAGE_A.md checkboxes
  - Pck5 paste SUBMISSION_LINKS.md to platform
known_false_greens_history:
  - happy_path_Q1_missed_B01_failed_save
  - UI_confirm_Q3_without_API_confirm_incomplete
  - changelog_STOP_looked_current
  - static_orb_skills_confirmed_when_unverified
smtp_wip_branch: wip/smtp-demo-mode-20261021
not_todo: [presentation_redesign, IRT_from_scratch, pitch_stage_B_now]
```

Если агент продолжает работу: сначала прочитай этот handoff + матрицу + human-протокол. Не объявляй «готово к отправке» без push + human ★.

---

## 2. Цена сессии (что «стоило»)

| Измерение | Оценка / факт |
|---|---|
| Календарь | ~21.10.2026, утро–день (UTC+3), rough window ~10:55–13:50 |
| Коммиты на `codex/fsp-mvp` сверх `origin` | **25** (`2e6d6da`→`889ebf3`) |
| Diff (ориентир) | ~85 файлов, **+13k / −0.5k** строк (код + docs + evidence) |
| Волны Astra `codex exec` | сборка Stage A; fix-loop Q3/Q4; verify×несколько; fix Q1; canon audit ×2 |
| Автотесты на финише | **97** pytest passed |
| Live smoke на финише | **18** групп (было 13 → 17 → 18 по мере расширения negative paths) |
| Деплои | многократный `docker compose build/up` api+web(+worker); БД **не** сносили |
| GitHub push | 0 успешных; попытки → `could not read Username` |
| Внешняя форма хакатона | 0 отправок |

Отдельная ветка вне сдачи: SMTP-WIP сохранён с `codex/dataset-v4` → `wip/smtp-demo-mode-20261021` до переключения на `codex/fsp-mvp`.

---

## 3. Хронология волн (что делали и где ошибались)

### W0 — подготовка сервера
- Обнаружено: дерево часто на `codex/dataset-v4` + незакоммиченный SMTP.\
- Сделано: SMTP закоммичен в `wip/smtp-demo-mode-20261021`; checkout `codex/fsp-mvp`; канон/промпты залиты в `docs/final_backlog_2026-10-20/`.\
- Старый `PROMPT_ASTRA.md` **не** использовался.

### W1 — первая сборка этапа A (мастер-промпт)
Коммиты продукта `8caf794`…`555d69d` + упаковка/деплой/smoke `ba34108`…`84e697a`.

| ID | Что сделали (суть) |
|---|---|
| Q1 | Persist ответов active-попытки / restore draft (happy path) |
| Q2 | Банк **2.1.0**, half-up, подсказка в условии; legacy политика |
| Q3 | UI confirm при пропусках (+ позже выяснилось: API ещё дырявый) |
| Q7 | matching **1.2.0**, прогон на labeled sample; P@5 holdout **0.80→0.80** (без вранья «улучшили») |
| Q4 | Тексты/чат под согласие (первый проход) |
| Q5 | Анонимы, контекст поиска, breakdown балла, компактнее форма |
| Q6 | Pause/resume не плодит выдачу; перенос нужного с живого стенда modernization |
| Pck1–4 | Changelog, for-jury, compose deploy, live smoke |
| Pck5 | Только текст; не отправляли |

**Ошибка восприятия после W1:** «smoke green = этап закрыт». Позже adversarial это опроверг.

### W2 — первый adversarial verify
Нашёл: **Q3 FAIL** (API submit без confirm завершал попытку), **Q4 FAIL** (B05: «подтвердите и опубликуйтесь» у уже published), Pck4 FAIL по правилу, Pck2 без push.

### W3 — fix-loop до «0 FAIL» (но ещё не полный B01)
- `839930f`: серверный `confirm_incomplete`; state-aware подсказки приглашений.\
- `8af82c4`: статус приглашения на карточке; расширение smoke.\
- Матрица: 14 PASS + Pck2 PARTIAL.

### W4 — независимый re-audit (не доверял W3)
Нашёл: **Pck1 FAIL** (в changelog живой STOP рядом с «всё закрыто»), **Q4 PARTIAL** (статичный орб «навыки подтверждены» у неподтверждённого).

### W5 — точечный фикс
- `f86d733`: орб от `verified_grade`; STOP убран в **архив**.\
- Spot-verify: снова зелёный технически.

### W6 — независимый audit **по канону COMPREHENSIVE** (`d4501b9`)
Нашёл то, что пропускали happy-path проверки:

**Q1 FAIL (B01 negative):** после failed PUT предупреждение пропадало при round-trip; закрытие вкладки теряло ответ без confirm; dirty не retry.

Следствие: Pck4 FAIL, Pck1 FAIL (changelog снова врал).

### W7 — fix Q1 + расширенный smoke
- `e5f78dd`: dirty draft, leave protection, retry.\
- `7f3dde4`: не блокировать **возврат** в тест диалогом ухода.\
- `420b643` + probes: HTTP 503 / delayed ACK.\
- Smoke → **18** групп (failed-save path внутри).

### W8 — independent canon round 2 (`889ebf3`)
Свежие 97 pytest + 18 smoke + отдельный Q1 negative probe.\
Итог: **0 FAIL**; Pck2 PARTIAL; Pck5 HUMAN_ONLY.\
`submission_allowed_now: false` до push + human.

---

## 4. Карта коммитов сессии (новые → старые)

Прикладные / тесты (важные):

| SHA | Сообщение |
|---|---|
| `7f3dde4` | leave dialog не мешает возврату в dirty-тест |
| `e5f78dd` | dirty drafts + retry + leave protection |
| `f86d733` | орб overview + архив STOP |
| `8af82c4` | invitation status на карточке + live checks |
| `839930f` | API confirm_incomplete + state-aware guidance |
| `555d69d` | Q6 schedule + retain platform |
| `9432225` | Q5 employer UX / score line |
| `d9368d2` | Q4 privacy/consent UX |
| `3b7b230` | Q7 matching + labeled validation |
| `e877ad7` | Q3 incomplete submit confirm (UI-era) |
| `21dc314` | Q2 bank half-up |
| `8caf794` | Q1 persist drafts (happy path) |

Документы verify / delivery (важные): `889ebf3`, `ab915af`, `810627a`, `d4501b9`, `feb67e5`, `44c3fb0`, `6b965ac`, `ceb37df`, `3e3c672`, `f02b36d`, `ba34108`, `84e697a`…

Полный список: `git log --oneline 2e6d6da..889ebf3` на VPS.

---

## 5. Что считается «сделано» по плану (технически)

| ID | Статус после independent_r2 | Смысл для человека |
|---|---|---|
| Q1 | PASS | Черновик + failed-save + leave confirm |
| Q2 | PASS | Half-up + подсказка; банк 2.1.0 |
| Q3 | PASS | UI + API `confirm_incomplete` |
| Q4 | PASS | Подсказки/орб/чат по состоянию |
| Q5 | PASS | Анонимы, фильтры, breakdown, форма |
| Q6 | PASS | Pause/resume без дубля (календарная неделя — human/time-travel) |
| Q7 | PASS | VERSION 1.2.0; метрики без фейкового роста |
| Pck1 | PASS | Changelog согласован со статусом |
| Pck2 | **PARTIAL** | For-jury есть; **GitHub не обновлён** |
| Pck3 | PASS | Стенд = проверенный код |
| Pck4 | PASS | Smoke 18 групп + negative Q1 |
| Pck5 | **HUMAN_ONLY** | Текст готов, форма не трогалась |
| REG_* / NOTTODO | PASS | ФСП/изоляция/старые подборки; презу не редизайнили |

---

## 6. Уроки / антипаттерны этой сессии (обязательно читать агентам)

1. **Зелёный smoke ≠ закрытый accept аудита.** Сначала закрыли happy path Q1; B01 negative всплыл только на канон-аудите.\
2. **UI-модалка ≠ серверный контракт.** Q3: браузер отменял, API всё равно принимал submit.\
3. **Changelog может врать тишиной.** Старый STOP рядом с «всё закрыто» = Pck1 FAIL.\
4. **Декоративный текст врёт состоянию.** Орб «навыки подтверждены» при `verified_grade=null`.\
5. **Не копировать матрицу PASS.** Каждый independent round обязан перепрогонять команды.\
6. **Push/Pck5 никогда не «за агента».** Иначе ложная сдача.

---

## 7. Где лежат доказательства

На VPS (`/root/hakaton`):

| Артефакт | Путь |
|---|---|
| Матрица вердиктов | `docs/delivery/VERIFY_STAGE_A_MATRIX.json` |
| Протокол агента | `docs/delivery/VERIFY_STAGE_A_PROTOCOL.md` |
| **Протокол человека** | `docs/delivery/HUMAN_VERIFY_PROTOCOL_STAGE_A.md` |
| Changelog | `docs/delivery/CHANGELOG_STAGE_A.md` |
| For-jury | `docs/delivery/FOR_JURY.md` |
| Текст сдачи | `docs/delivery/SUBMISSION_LINKS.md` |
| Evidence r2 / q1-recovery | `docs/delivery/evidence/` |
| Smoke script | `scripts/smoke_stage_a.py` |
| Q1 probe | `scripts/probe_stage_a_q1.py` |
| Codex logs | `/root/hakaton/logs/astra_*` |
| Runbook / verify prompts | `docs/final_backlog_2026-10-20/prompts/` |

Локально (этот репозиторий Portfolio):\
`session_reviews/hackathons/fsp/server_delivery_2026-10-21/`\
и промпты контроля: `session_reviews/hackathons/fsp/prompts/ASTRA_VERIFY_*.md`

---

## 8. Как откатить / как опубликовать

**Откат прикладного кода к досессионной базе:**\
`git checkout 2e6d6da` (осторожно: только осознанно; стенд отдельно).\
Для отмены опубликованного изменения использовать отдельный проверенный revert; не сбрасывать чужую историю.

**Восстановить исторический этап A с bundle (машина с GitHub auth):**

Проверено 21 октября: bundle содержит ref `HEAD` на `889ebf3`, а не имя ветки. Требуется базовый коммит `2e6d6da`; это инкрементальный архив. Более поздние изменения в нём отсутствуют. Push в текущей сессии отложен пользователем.

```bash
git fetch origin
git checkout codex/fsp-mvp
git pull --ff-only   # если уже есть
git bundle verify path/to/codex-fsp-mvp-stage-a.bundle
git fetch path/to/codex-fsp-mvp-stage-a.bundle HEAD:refs/heads/review-stage-a-889ebf3
git merge --ff-only review-stage-a-889ebf3
# Если fast-forward невозможен, остановиться и изучить расхождение; не делать reset/force-push.
git push origin codex/fsp-mvp
```

На самом VPS после появления credentials:

```bash
cd /root/hakaton
git checkout codex/fsp-mvp
git push origin codex/fsp-mvp
```

---

## 9. Протокол проверки человеком (то, что Астра не закрывает на 100%)

Каноническая актуальная копия на стенде/репо:\
`docs/delivery/HUMAN_VERIFY_PROTOCOL_STAGE_A.md`\
Локальный снимок:\
[`docs/delivery/HUMAN_VERIFY_PROTOCOL_STAGE_A.md`](../delivery/HUMAN_VERIFY_PROTOCOL_STAGE_A.md)

Ниже — **полная копия снимка independent_r2** (клетки человеком ещё не заполнены). Если на VPS файл новее — верьте серверному.

---

# Протокол проверки человеком — этап A
Дата составления (ISO): 2026-10-21T10:48:31.092494+00:00\
Составил: Astra / verify session independent_r2\
Git SHA стенда/ветки: ab915af6eb771c9688d60f08dcf1bd9211f59d25\
Стенд: https://85-137-26-131.sslip.io/\
Ветка: codex/fsp-mvp\
Связанная матрица: VERIFY_STAGE_A_MATRIX.json\
Связанный протокол агента: VERIFY_STAGE_A_PROTOCOL.md\

## 0. Как пользоваться (30 секунд)

- Ставьте у каждого шага PASS / FAIL / SKIP. Сейчас клетки **не заполнены человеком**.\
- FAIL по must (★) = нельзя отправлять Pck5. SKIP обязательного шага тоже не закрывает его.\
- Не чините сами в этой сессии — только фиксируйте; баг верните команде.\
- Review-логины и пароли только из FOR_JURY; свои данные не вводить. Для ролей — отдельные браузерные профили.\
- 25–40 минут; маршрут FOR_JURY внутри — 10–15 минут.\
- Автопроверки прошли, но remote при составлении ещё на `2e6d6da`. До актуального push и человеческих must отправлять нельзя. Pck5 — последним.

## 1. Доступ и упаковка

| ID | Что сделать | Результат |
|---|---|---|
| H-ACC ★ | Открыть https://85-137-26-131.sslip.io/ из своего браузера — без TLS/DNS сюрприза | ☐ PASS ☐ FAIL ☐ SKIP |
| H-PUSH ★ | После push открыть GitHub-ссылки из SUBMISSION_LINKS — актуальный SHA/docs | ☐ PASS ☐ FAIL ☐ SKIP |
| H-Pck2-walk ★ | FOR_JURY шаги 1–6 за 10–15 мин без подсказок команды | ☐ PASS ☐ FAIL ☐ SKIP |
| H-Pck1 | Changelog за 2 мин: Q1–Q7 ясны, старые STOP исторические, P@5 без фейкового роста | ☐ PASS ☐ FAIL ☐ SKIP |

## 2. Must на экране (★)

| ID | Что сделать | Результат |
|---|---|---|
| H-Q1 ★ | Ответ → Обзор → назад → F5; затем offline/ошибка сохранения → предупреждение; уход с confirm; retry после сети | ☐ PASS ☐ FAIL ☐ SKIP |
| H-Q2 ★ | Новое SQL Middle: видно half-up 90,625→90,63 | ☐ PASS ☐ FAIL ☐ SKIP |
| H-Q3 ★ | 1 из 8 → Завершить → диалог 7 из 8 → Отмена сохраняет попытку | ☐ PASS ☐ FAIL ☐ SKIP |

## 3. UX, где авто не 100%

| ID | Что сделать | Результат |
|---|---|---|
| H-Q4a | Скрытый профиль: тексты не обещают «найдут»; у непроверенного орб «к проверке» | ☐ PASS ☐ FAIL ☐ SKIP |
| H-Q4b | После отзыва поле чата исчезает; повторная публикация сама не возвращает согласие | ☐ PASS ☐ FAIL ☐ SKIP |
| H-Q5a | Анонимы различимы за 5 сек; статус приглашения на карточке | ☐ PASS ☐ FAIL ☐ SKIP |
| H-Q5b | Соседи объяснимы строкой навыки/тест/ФСП | ☐ PASS ☐ FAIL ☐ SKIP |
| H-Q5c | Форма: стаж не маскируется под ранжирование; контекст поиска сохраняется | ☐ PASS ☐ FAIL ☐ SKIP |
| H-Q6-calendar | Pause/resume: одна выдача; отдельно решить: принимаем time-travel **или** отложенный чек | ☐ PASS ☐ FAIL ☐ SKIP |

Решение по календарю: ☐ time-travel+live OK; ☐ отложенный чек, дата ______

## 4. Принципиально не авто

| ID | Что сделать | Результат |
|---|---|---|
| H-Q7 | VALIDATION/for-jury: 1.2.0, P@5 без «улучшили»; лимиты синтетики приняты | ☐ PASS ☐ FAIL ☐ SKIP |
| H-Pck3-reach | Стенд с сети/устройства жюри | ☐ PASS ☐ FAIL ☐ SKIP |
| H-Pck4-spot | 3 шага FOR_JURY глазами поверх green smoke | ☐ PASS ☐ FAIL ☐ SKIP |
| H-PREZA | Преза — прежняя, без редизайна | ☐ PASS ☐ FAIL ☐ SKIP |
| H-SMTP | not_run; review-логин ≠ проверка почты | ☐ PASS ☐ FAIL ☐ SKIP |
| H-Pck5 ★ | Только после остальных ★ + push: вставить SUBMISSION_LINKS | ☐ PASS ☐ FAIL ☐ SKIP |

## 5. Регрессии

| ID | Что сделать | Результат |
|---|---|---|
| H-REG-ISO ★ | Своя компания видит контакты после accept; чужая/PDF — нет | ☐ PASS ☐ FAIL ☐ SKIP |
| H-REG-FSP ★ | Демо-ФСП не меняет грейд | ☐ PASS ☐ FAIL ☐ SKIP |
| H-REG-OLD | Старая подборка сохранена; скрытый не всплывает через снимок | ☐ PASS ☐ FAIL ☐ SKIP |

## 6. Итог человека

- Можно слать ссылки: ДА / НЕТ\
- FAIL / SKIP / блокеры: ____________________\
- Календарь Q6: ____________________\
- Pck5: отправлено / нет; время/канал ____________________\
- Подпись / дата: ____________________

**Агент не ставит галочки за человека.**

---

## 10. Текст Pck5 (после human PASS)

См. [`docs/delivery/SUBMISSION_LINKS.md`](../delivery/SUBMISSION_LINKS.md).\
Перед отправкой убедиться, что GitHub-ссылки уже ведут на запушенную ветку.

---

## 11. Этап B (не делали)

Питч P-01…P-05, редизайн презы, репетиция — **после** проверки экспертами. В эту сессию не входили.

---

## 12. Контакты файлов в Portfolio (этот репозиторий)

| Файл | Роль |
|---|---|
| Этот handoff | Карта сессии для людей и агентов |
| `COMPREHENSIVE_STAGE_A_2026-10-21.md` | Канон плана |
| `ASTRA_CODEX_RUNBOOK_STAGE_A.md` | Как гонять Astra на VPS |
| `prompts/ASTRA_VERIFY_*.md` | Контрольные промпты |
| `server_delivery_2026-10-21/*` | Снимок delivery/verify + bundle |
| `00_START_HERE_TEAM_AND_AGENTS.md` | Точка входа команды |

---

*Составлено 2026-10-21 по итогам сессии Codex Astra на VPS + локальной упаковке в Open_Portfolio_AI.*

# Промпт Astra: заготовка стандартного закрытого контура

Скопируй в `codex exec` **целиком**. Это **не** доработка Stage A (Q1–Q7) и **не** сборка MVP с нуля.

---

Ты GPT Astra Codex на сервере хакатона ФСП / ЛЦТ, команда «Нанотехнологический альянс».

## Роль

Собрать **проверяемый комплект готовности к внедрению** продукта во **типовой закрытый / корпоративный контур** заказчика в РФ — по канону ниже. Цель Данилы: **показать, что мы готовы внедрить продукт**, не превращая публичный демо-стенд в «только VPN».

## Источники правды (читай в этом порядке)

1. `docs/closed_contour_2026-10-21/COMPREHENSIVE_CLOSED_CONTOUR_2026-10-21.md` — **канон**  
2. `docs/closed_contour_2026-10-21/BACKLOG_CLOSED_CONTOUR.json` — статусы  
3. `docs/closed_contour_2026-10-21/prompts/ASTRA_VERIFY_BY_TASK_CC.md` — как доказывать  
4. Факт кода: `compose.yaml`, `.env.example`, `scripts/configure.py`, `apps/api/fsp/models.py`, `schemas.py`, `docs/GIT_WORKFLOW.md`, `AGENTS.md`  
5. Якоря Данилы из канона §0 (deps download allowed; ПДн+ТД; устройство заказчика неизвестно)

Созвоны / Stage A comprehensive — **контекст**. Не расширяй объём до Q1–Q7.

## Жёсткие запреты

- Править и «приводить в порядок» грязный WIP в `/root/hakaton` на чужой ветке (`fix/repeatable-jury-demo` и т.п.): **никакого** `reset --hard`, stash как отката чужого, force-push.  
- Ломать / пересобирать публичный стенд sslip «заодно», пока человек явно не сказал.  
- Обещать air-gap, ФСТЭК, enterprise WAF, «полное соответствие 152-ФЗ», замену 1С/ЗУП.  
- Старый `PROMPT_ASTRA.md` (MVP с нуля).  
- Коммит секретов `.env`.  
- Писать «готово» / PASS без доказательства по DoD.

## W0 — окружение (сделай первым)

```bash
# идея (адаптируй, если worktree уже есть):
cd /root/hakaton
git worktree add /root/hakaton-contour -b codex/closed-contour-readiness codex/fsp-mvp
# если ветка уже есть:
# git worktree add /root/hakaton-contour codex/closed-contour-readiness
```

Дальше **весь** код и коммиты только из `/root/hakaton-contour`.

Скопируй канон в worktree, если его ещё нет:

`docs/closed_contour_2026-10-21/` → тот же путь в worktree.

Зафиксируй в начале протокола: `pwd`, `git branch`, `git rev-parse HEAD`, `git status -sb` **обоих** деревьев (основной клон + worktree).

## Порядок волн

Иди **W1→W6** по канону. После каждой must-задачи:

1. артефакт на диске по пути из JSON;  
2. обновление `status` в `BACKLOG_CLOSED_CONTOUR.json`;  
3. осмысленный git commit в `codex/closed-contour-readiness` (сообщение = зачем);  
4. не начинай следующую волну, пока DoD текущей must не закрыт или не помечен честным PARTIAL с причиной.

### Must (питч-заявление «готовы внедрить»)

CC1, CC2, CC3, CC4, CC5, CC6, CC8, CC9, CC12, CCV1.

### Should

CC7, CC10, CC11, CC13, CC14, CCV2 (черновик), CCV3.

## Особые требования к содержанию

- **CC3:** два варианта доступа — (A) только внутренняя сеть / bind private; (B) за reverse-proxy заказчика. Явно: скачивание зависимостей **разрешено**.  
- **CC4:** dry-run **изолирован** (отдельное имя compose-проекта / каталог / порты), **не** трогает том прод-БД стенда. Лог в `docs/delivery/closed_contour/evidence/`.  
- **CC6/CC7:** таблица «угроза → есть → дыра → владелец»; anti-DDoS без фантазий.  
- **CC9:** каждое сильное утверждение → ссылка на код/док; иначе `LEGAL_REVIEW_NEEDED`.  
- **CC12:** onepager на 1–2 экрана, язык для жюри, не «контракт».  
- **CC13:** максимум короткий абзац-ссылка в FOR_JURY/CHANGELOG; не раздувать Stage A.

## Артефакты в конце сессии

| Файл | Содержание |
|---|---|
| `docs/delivery/closed_contour/*` | все md из DoD |
| `scripts/closed_contour_dry_run.sh` | dry-run |
| `docs/delivery/closed_contour/evidence/` | логи |
| `docs/delivery/closed_contour/VERIFY_CLOSED_CONTOUR_MATRIX.json` | вердикты |
| `docs/delivery/closed_contour/VERIFY_CLOSED_CONTOUR_PROTOCOL.md` | протокол агента с выводами команд |
| `docs/delivery/closed_contour/HUMAN_VERIFY_PROTOCOL_CLOSED_CONTOUR.md` | из шаблона |
| `BACKLOG_CLOSED_CONTOUR.json` | статусы |

## Финальный отчёт в чат (обязателен)

1. SHA ветки `codex/closed-contour-readiness` и список коммитов.  
2. Таблица ID → status → путь артефакта.  
3. Путь к логу dry-run + exit code.  
4. Что осталось HUMAN / LEGAL_REVIEW.  
5. Подтверждение: основной клон `/root/hakaton` не очищался силой; sslip health (если проверял) — результат.

Если W0 невозможен (нет `codex/fsp-mvp`, нет места) — **STOP** с причиной, без правок в чужом WIP.

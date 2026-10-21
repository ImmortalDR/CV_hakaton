# Что сделано по закрытому контуру — handoff для агентов и людей

**Дата снимка:** 2026-10-21 19:12 UTC  
**Ветка:** `codex/closed-contour-readiness`  
**Worktree на сервере:** `/root/hakaton-contour`  
**SHA снимка:** `1c28a04` (`1c28a043bd5fe2945a21425049137f18435ac453`)  
**Публичный демо-стенд (не ломать):** https://85-137-26-131.sslip.io/

Этот файл — **входная точка**. Сначала его, потом канон и проверки.

---

## 1. Зачем это вообще

Данила попросил не «переписать продукт только за VPN», а **показать готовность внедрить** платформу у заказчика в типовом корпоративном контуре:

- план внедрения + инфбез (в т.ч. анти-DDoS «на бумаге» / на edge заказчика);
- устройство сети заказчика **неизвестно** → готовим **стандартный** комплект;
- учесть законы РФ про **персональные данные** и границу с **трудовыми** темами;
- серверу установки **разрешено скачивать зависимости** (не полный офлайн);
- публичный хакатонный стенд **остаётся** в интернете.

Это **отдельный трек** от этапа A (баги теста Q1–Q7). Не смешивать.

Канон требований:  
`docs/closed_contour_2026-10-21/COMPREHENSIVE_CLOSED_CONTOUR_2026-10-21.md`

---

## 2. Где лежит комплект

| Что | Путь |
|---|---|
| Старт трека | `docs/closed_contour_2026-10-21/00_START_HERE.md` |
| Канон DoD | `docs/closed_contour_2026-10-21/COMPREHENSIVE_CLOSED_CONTOUR_2026-10-21.md` |
| Статусы задач | `docs/closed_contour_2026-10-21/BACKLOG_CLOSED_CONTOUR.json` |
| Артефакты поставки | `docs/delivery/closed_contour/` |
| Улики / логи | `docs/delivery/closed_contour/evidence/` |
| Промпт сборки (Astra) | `docs/closed_contour_2026-10-21/prompts/ASTRA_CLOSED_CONTOUR.md` |
| Промпт перепроверки | `docs/closed_contour_2026-10-21/prompts/ASTRA_REVERIFY_CLOSED_CONTOUR.md` |
| Как доказывать по ID | `docs/closed_contour_2026-10-21/prompts/ASTRA_VERIFY_BY_TASK_CC.md` |
| Runbook запуска Astra | `docs/closed_contour_2026-10-21/ASTRA_CODEX_RUNBOOK_CLOSED_CONTOUR.md` |
| Копия канона в основном клоне | `/root/hakaton/docs/closed_contour_2026-10-21/` (может отставать от worktree) |

**Важно:** рабочий код и коммиты этого трека — в `/root/hakaton-contour`.  
Основной клон `/root/hakaton` часто занят чужим WIP (другие ветки). **Не** делать там `reset --hard` и не «приводить в порядок» чужое дерево ради контура.

---

## 3. Что сделано (по смыслу)

Собран **комплект готовности к поставке** (документы + изолированный прогон установки), без переделки продукта в VPN-only и без правок Stage A Q*.

### 3.1 Документы для внедрения / ИБ / закона

| Файл | О чём |
|---|---|
| `01_INVENTORY.md` | Что крутится в compose: сервисы, порты, тома, health, секреты |
| `02_DATA_MAP.md` | Какие персональные / около-трудовые данные есть в моделях |
| `03_INSTALL_RUNBOOK.md` | Как ставить у заказчика (LAN / за его reverse-proxy); deps download allowed |
| `04_SECRETS_AND_CONFIG.md` | Секреты, `.env`, что нельзя коммитить |
| `05_THREAT_MODEL.md` | Угрозы → что уже есть → дыра → кто чинит (мы / заказчик) |
| `06_EDGE_AND_DDOS.md` | Честно: что не enterprise-WAF; что на edge заказчика |
| `07_HARDENING_CHECKLIST.md` | Чеклист укрепления для внутреннего контура |
| `08_PDN_152_NOTES.md` | Заметки по ПДн с пометками `LEGAL_REVIEW_NEEDED` |
| `09_LABOR_BOUNDARY.md` | Это не кадровый учёт / не замена 1С ЗУП |
| `READY_TO_DEPLOY_ONEPAGER.md` | 1–2 экрана для жюри/питча |
| `PITCH_CLOSED_CONTOUR_90S.md` | Короткий текст ~90 секунд |
| Указатель из Stage A | Абзац в `docs/delivery/FOR_JURY.md` → onepager |

### 3.2 Техническое доказательство установки

| Файл | О чём |
|---|---|
| `scripts/closed_contour_dry_run.sh` | Изолированный compose-проект `fsp-cc-dryrun-…` |
| `scripts/check_closed_contour_config.py` | Гигиена `.env` / example |
| `scripts/verify_closed_contour_artifacts.py` | Структурная сверка артефактов |
| `evidence/cc-dry-run-*.log` | Логи прогонов (`EXIT_CODE=0`, cleanup) |

Dry-run **не** должен трогать том БД публичного стенда.

### 3.3 Проверки, которые уже были

| Раунд | Кто | Артефакт |
|---|---|---|
| Сборка W0–W6 | Astra | коммиты `docs(contour)|security|privacy|pitch|test(contour)` |
| Независимая сверка | Cursor | `evidence/INDEPENDENT_VERIFY_R1.json` |
| Adversarial по канону | Astra | `evidence/REVERIFY_VS_CANON_2026-10-21.json` + коммит `112d5c6` |

На момент снимка в backlog: все агентские must = `PASS`; `CCV2` = `HUMAN_ONLY`; `pitch_claim_allowed_before_human` = **false**.

---

## 4. Чего это НЕ делает (чтобы не обещать лишнего)

- Не air-gap / не полный офлайн-бандл.  
- Не сертификация ФСТЭК / ГОСТ.  
- Не «мы полностью соответствуем 152-ФЗ» без юриста.  
- Не замена кадрового учёта / 1С ЗУП.  
- Не перевод публичного демо «только за корпоративный VPN».  
- Не закрытие человеческих ★ и не юр. акцепт заказчика.

---

## 5. Как проверять **агенту** (Astra / другой ИИ)

### 5.1 Быстрый путь (контроль, не сборка)

```bash
cd /root/hakaton-contour
codex exec -m gpt-6-astra --dangerously-bypass-approvals-and-sandbox \
  -C /root/hakaton-contour \
  - < docs/closed_contour_2026-10-21/prompts/ASTRA_REVERIFY_CLOSED_CONTOUR.md
```

Правила контролёра:

1. Источник правды — **канон** + `ASTRA_VERIFY_BY_TASK_CC.md`, не старые PASS.  
2. На каждый ID — свежее доказательство в протоколе (команда / цитата / SHA).  
3. Для CC4 при сомнении — **перезапустить** dry-run, не верить старому логу вслепую.  
4. Код продукта не «подкручивать под PASS»; при реальном провале DoD → `FAIL`.  
5. Не трогать WIP в `/root/hakaton` силой.

### 5.2 Must, без которых нельзя говорить «агентская готовность»

Из `BACKLOG_CLOSED_CONTOUR.json` → `must_for_pitch_claim`:

`CC1, CC2, CC3, CC4, CC5, CC6, CC8, CC9, CC12, CCV1`

### 5.3 Минимальные команды без полного Codex

```bash
cd /root/hakaton-contour
git branch --show-current   # ожидается codex/closed-contour-readiness
git rev-parse HEAD
python3 scripts/check_closed_contour_config.py
python3 scripts/verify_closed_contour_artifacts.py
# осторожно: долгий; изолированный проект
bash scripts/closed_contour_dry_run.sh
curl -fsS https://85-137-26-131.sslip.io/api/health
```

Сверить:

- матрица `docs/delivery/closed_contour/VERIFY_CLOSED_CONTOUR_MATRIX.json`;  
- `evidence/REVERIFY_VS_CANON_2026-10-21.json` → `must_gaps` должен быть `[]` после зелёной перепроверки;  
- в текстах нет запрещённых обещаний из §6 канона.

### 5.4 Куда писать результат агенту

| Файл | Назначение |
|---|---|
| `VERIFY_CLOSED_CONTOUR_MATRIX.json` | Вердикты по ID |
| `VERIFY_CLOSED_CONTOUR_PROTOCOL.md` | Протокол с выводами команд |
| `evidence/REVERIFY_*.json` или новый `evidence/…` | Машиночитаемый итог раунда |
| `BACKLOG_CLOSED_CONTOUR.json` | Обновить `status` только если вердикт изменился |

Коммит сообщением вида: `docs(verify): …` — только документы проверки, без force-push.

---

## 6. Как проверять **человеку** (команда / Данила)

Не нужно читать pytest и JSONL Codex. Откройте:

`docs/delivery/closed_contour/HUMAN_VERIFY_PROTOCOL_CLOSED_CONTOUR.md`

Там галочки ☐. Критичные со звездой ★:

1. **Рамка** — onepager обещает внедрение у заказчика, а не VPN-only продукт.  
2. **Deps** — в runbook явно разрешено скачивать зависимости.  
3. **Dry-run** — в свежем логе есть health и cleanup своего проекта, нет сноса прод-БД стенда.  
4. **ПДн** — в `08_PDN_152_NOTES.md` нет голословного «полностью соответствуем»; спорное помечено `LEGAL_REVIEW_NEEDED`.

Дополнительно глазами:

- публичный стенд открывается;  
- чужой WIP на основном клоне на месте (спросить владельца ветки).

**Правило:** пока ★ не PASS человеком, на питче можно говорить  
«есть комплект поставки и изолированный прогон»,  
но **не** «юр/ИБ заказчика приняты» и не безусловное «готовы внедрить».

Юридические хвосты — только с человеком/юристом по списку `LEGAL_REVIEW_NEEDED`.

---

## 7. Два контура (чтобы не путаться)

| Контур | Кто | Статус |
|---|---|---|
| Публичный демо | жюри / интернет | живой стенд sslip; в этом треке **не пересобирать** без явной просьбы |
| Корпоративная поставка | заказчик у себя | заготовка: runbook + dry-run + ИБ/ПДн доки |

Доступ «только из LAN / за VPN» — **выбор заказчика** через bind/proxy, не суть продукта найма.

---

## 8. Как откатить / не сломать соседей

- Вся работа трека — ветка `codex/closed-contour-readiness` в worktree.  
- Откат агентских коммитов: смотреть `git log` на этой ветке; **не** `reset --hard` на `main` и не на чужих ветках основного клона.  
- Не использовать `stash` как откат чужого WIP.  
- Push на GitHub этой ветки — только по явной просьбе человека (на момент снимка push мог быть не сделан).

---

## 9. Чеклист «можно упоминать на питче» (из канона)

- [ ] Инвентарь и карта данных свежие  
- [ ] Runbook читается человеком без Slack  
- [ ] Dry-run лог с `EXIT_CODE=0`  
- [ ] Threat model без пустых угроз  
- [ ] Hardening с честными ☐  
- [ ] ПДн без голословного «соответствуем»  
- [ ] Onepager согласован человеком (★)  
- [ ] Стенд жив; WIP соседей цел  

Агент может закрыть технические пункты. **Согласование onepager / ★ / юрист — человек.**

---

## 10. Кому что делать дальше

| Кто | Действие |
|---|---|
| Агент | При сомнении — снова `ASTRA_REVERIFY_CLOSED_CONTOUR.md`; не смешивать с Q1–Q7 |
| Никита / Тимофей | Пройти human-протокол ★; глянуть onepager и dry-run лог |
| Данила | Смысл рамки + `LEGAL_REVIEW_NEEDED`; ок на формулировку для питча |
| Вся команда | Push ветки и ссылка жюри — когда решите явно |

---

*Handoff closed contour · не путать с Stage A delivery · обновляйте SHA в шапке при новом раунде проверки*

# Ворота презентации (ЛЦТ / FSP) — до «готово»

Канон: `Open_Portfolio_AI/growth/ui-ux-verification-2026.md` → **SG-***.  
Правило агента: `Open_Portfolio_AI/.cursor/rules/pptx-presentation-gates.mdc`.  
Уроки сессии: [`LESSONS_LCT_2026-10-09.md`](LESSONS_LCT_2026-10-09.md).  
Канал судьи: **Microsoft PowerPoint** (не PDF / не LibreOffice).

Любой красный пункт = **не готово**.

## Ритуал после каждой правки

```bash
# Замок 7–11:
bash docs/presentation/run_round.sh
# fill → insert → gate_check → full_audit → capture_ppt_frames 8–11

# Свободные 12–14 (не трогает 7–11):
bash docs/presentation/run_round_outside.sh
# fill_outside → gate_check_outside → gate_check(7–11) → capture 12–14

# Файл для жюри (обязательно после правок сдачи):
bash docs/presentation/run_round_submission.sh
# draft gates → export SUBMISSION → GATE SUBMISSION → capture SUBMISSION (не DRAFT!)
```

Ожидание: `GATE PASS` / `GATE OUTSIDE PASS` / `GATE SUBMISSION PASS` + свежие кадры.  
**Анти-паттерн:** гейтить DRAFT, а жюри отдавать SUBMISSION без `run_round_submission.sh` (capture по умолчанию открывал DRAFT).
Вручную (если без скрипта):

```bash
.venv-pptx/bin/python docs/presentation/fill_slides_7_11.py
.venv-pptx/bin/python docs/presentation/insert_assets.py   # сам гоняет gate+audit
.venv-pptx/bin/python docs/presentation/gate_check.py
.venv-pptx/bin/python docs/presentation/full_audit.py
./docs/presentation/capture_ppt_frames.sh 8 11
```

## Принципы (CRAP + эталон)

| Принцип | На практике |
|---------|-------------|
| **Contrast** | Иерархия ясна; ramp Geoscan: 11 / 12 / 13 / 15 / 16 / 20 / 22 |
| **Repetition** | Маркеры шаблона; без своих «•» |
| **Alignment** | Карточки разнесены; одна левая кромка зоны |
| **Proximity** | Content-gap label→body ≥ 0.06″; многострочный label → тело ниже **низа коробки** |
| **Billboard** | Не влезает → режь текст, не кегль |
| **Density-ref** | Длина ≈ Geoscan в тех же боксах (не пустыня, не простыня) |
| **Whitespace** | Воздух ок; пустыня = короткий текст в огромном слоте эталона |

## Авто (обязательно ловит)

| ID | Что ловит |
|----|-----------|
| SG-overlap | Наезд label↔body (content); body→next-label в той же колонке |
| SG-density-ref | Слишком короткий текст vs эталон |
| SG-type-ramp / soup | Чужой pt |
| SG-overflow | Текст не влезает (FILL_MAX калиброван по Geoscan) |
| SG-vt | U+000B / soft-break |
| SG-copy-ru | «Invite» |
| SG-title-* | Пустой / тёмный на розовом / светлый на белом |
| SG-card-span | 3 карточки не разнесены |
| SG-photo-slot | Слайд 8: branded panel (не blank); слайд 9: ≥3 фото |
| SG-asset-search | Портреты ≥80KB из Geoscan extract |
| SG-density-ref (12–14) | `gate_check_outside`: chars + fill need/have — ловит пустыню |
| SG-aspect (14) | Картинка ≈ аспект слота; бан stand_*/ширина&lt;1000px — ловит плохой скрин |
## Глазами в PowerPoint (каждый изменённый слайд)

| ID | Вопрос | Слайды |
|----|--------|--------|
| SG-channel | Кадр из окна PowerPoint? | все |
| SG-placeholder | Нет «НАЗВАНИЕ / Имя Фамилия / Образец / дописать»? | 7–11 |
| SG-photo-slot | 8 — панель команды эталона (лица); 9 — живые фото | 8–9 |
| SG-asset-matte | Нет белых дыр в волосах/фоне? | 8–9 |
| SG-overlap | Нет наезда заголовок↔тело и тело↔следующий заголовок? | 8–11 |
| SG-density-ref | Поля не пустые относительно Geoscan? | 8–11 |
| SG-comp | 2–3 якоря за 3 с? | 8–11 |
| SG-grid | Сетка шаблона цела; лишние колонки удалены? | 9 |

## Ответ агента при сдаче

```text
Преза-сдача
Дыра: 0|1|2|чисто
run_round / gate_check: PASS / FAIL …
full_audit: PASS / FAIL …
Кадры PPT: preview_frames/ppt_verify_slide_N.png …
SG-overlap / density-ref / channel: ок / стоп на …
```

## Анти-паттерны

- Сдать по LibreOffice / Impress / `soffice` / PDF.  
- Игнор label×body «шаблон так гнездит».  
- Matte/нормализация портретов.  
- Забить пустоту мелким кеглем **или** оставить 2 фразы в боксе на ~290 символов эталона.  
- PASS без кадра PPT.  
- Кадры `fix_*.png` / `audit_*.png` из PDF ≠ SG-channel.

## Замок (человек)

**2026-10-09 — визуал слайдов 7–11 принят.**  
Воздух шаблона / Geoscan (низ карточек 9, правая зона 10, поля панелей 11) — **не баг**, дальше не уплотнять без новой ставки.  
Файл: `FSP_NIKITA_DRAFT.pptx` · авто на момент замка: `GATE PASS` + `FULL AUDIT PASS`.  
Вне замка (руки человека): город / телефоны / учёба; живые фото при появлении.

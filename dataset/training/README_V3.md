# Реальные профили с историей работы: V3 и V3-CV

Обучаем ранжирование **записанного принятия/отказа на отклик**. Исходные события
не размечают профессиональную пригодность, навыки или грейд. Сервис остаётся
на проверяемых правилах; эти модели используются офлайн.

Исходники: существующие CSV trudvsem; новые источники и внешние LLM не нужны.
Протоколы: [V3](EXPERIMENT_V3.md), [групповая кросс-валидация](EXPERIMENT_V3_CV.md).
Измерения: [RESULTS_V3.md](RESULTS_V3.md).

## Воспроизведение

Python 3.12, зависимости `dataset/training/requirements.lock.txt`. Команды
выполняются из корня репозитория. Выходные каталоги новые: готовые результаты
не перезаписываются. Многогигабайтные CSV читаются только на этапе index.
При прерывании index можно повторить команду: завершённые файлы проверяются
по SHA-256, частичный производный файл пересобирается. Raw-файлы не меняются.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python dataset/training/enrich.py index \
  --source dataset/raw_sources/trudvsem \
  --root dataset/builds/trudvsem-training-v1 \
  --out dataset/builds/trudvsem-enrichment-v3

OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python dataset/training/enrich.py pairs \
  --root dataset/builds/trudvsem-training-v1 \
  --enrichment dataset/builds/trudvsem-enrichment-v3 \
  --anchors dataset/builds/trudvsem-decisions-v2 \
  --out dataset/builds/trudvsem-decisions-v3-final

OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python dataset/training/experiment_v3.py run \
  --root dataset/builds/trudvsem-decisions-v3-final --out dataset/builds/trudvsem-model-v3

OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python dataset/training/cross_validate_v3.py \
  --root dataset/builds/trudvsem-decisions-v3-final --out dataset/builds/trudvsem-model-v3-cv

OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python dataset/training/experiment_v3.py replay \
  --root dataset/builds/trudvsem-decisions-v3-final --out dataset/builds/trudvsem-model-v3-cv

OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m pytest dataset/training/tests -q
```

Базовые index.sqlite/V2 строятся по прежнему [README](README.md).
Созданные ранее 10 октября каталоги уже существуют: для нового опыта выбирайте
другие `--out`. Первый черновик `trudvsem-decisions-v3` сохранён для аудита;
он не использован для обучения. Измеренный набор — `trudvsem-decisions-v3-final`.

## Предсказание

`candidates.jsonl`: одна строка JSON на кандидата. Например, вымышленные данные:

```json
{"candidate_id":"example-1","candidate_base_text":"Разработчик Python и SQL, серверные приложения","work_text":"Разработка API на Python, PostgreSQL и тестов pytest","education_text":"Программная инженерия"}
```

`need.txt` — профессиональный текст потребности, минимум 60 символов.
Модель выбирается по `winner` в локальном `selection.json`, а не по наибольшей
цифре test в таблице. В серии V3-CV выбран `base_pair`, но его тестовые
результаты не обосновали включение в продукт. Пример локального вызова:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python dataset/training/predict_v3.py \
  --model dataset/builds/trudvsem-model-v3-cv/base_pair.joblib \
  --candidates /path/candidates.jsonl --need-file /path/need.txt
```

Выход: порядок и относительный `observed_reply_score`. Это не процент
соответствия, не калиброванная вероятность и не подтверждение навыков. Короткий
пустой профиль возвращает `insufficient_professional_text` и score=null.
Загружайте только собственные проверенные joblib-файлы: этот формат исполняемый.

## Поставка и границы

В Git — код, методика, тесты, агрегаты. Тексты, построчные данные, OOF-прогнозы,
индексы и веса — только в `dataset/builds`, исключённом из Git.
Локальный архив создаётся явным allowlist:

```bash
.venv/bin/python dataset/training/package_v3.py \
  --out dataset/releases/trudvsem-training-2026-10-10-v3-local.zip
.venv/bin/python dataset/training/package_local.py \
  --verify dataset/releases/trudvsem-training-2026-10-10-v3-local.zip
```

Архив содержит реальный текст и **не предназначен для публичного GitHub**.
Внутри LOCAL_ONLY.txt — команды повторного обучения и проверки без raw CSV.
Исходный источник и лицензия: [карточка «Работы в России»](https://data.rcsi.science/data-catalog/datasets/186/).
MIT нашего кода не заменяет условия исходных данных. Сертификации и экспертных
меток профессиональной пригодности нет. Статусы ФСП и результаты тестов MVP
не выводятся из этих текстов и не меняются при запуске команд.

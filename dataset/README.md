# ФСП: воспроизводимый оценочный набор

Версия 1.0.0. Собственная программная разметка контрольных сценариев и отдельное
локальное дополнение с исходными внешними метками. Разметчиков нет; DeepSeek и
другие внешние модели не вызываются, `.env` не читается. Внешней сертификации нет.

## Проверка готового архива

Python 3.12. Распакуйте публичный ZIP в отдельную папку, перейдите в неё:

```bash
python3 -m venv ../fsp-eval-venv
../fsp-eval-venv/bin/python -m pip install -r requirements.lock.txt
../fsp-eval-venv/bin/python run.py validate --root .
../fsp-eval-venv/bin/python run.py evaluate --root . --out ../matching-rerun.json
../fsp-eval-venv/bin/python run.py evaluate-assessment --root . --out ../assessment-rerun.json
../fsp-eval-venv/bin/python run.py import-db --root . --dry-run
```

Виртуальное окружение создаётся **вне каталога замороженного пакета**.
Валидатор отвергает
дополнительные файлы внутри распакованного пакета.
На Debian/Ubuntu для создания venv может потребоваться пакет python3-venv.
На этом сервере среда `dataset/.venv` создана через существующий pip с `--python`.

## Сборка из репозитория

Из корня репозитория, после установки зависимостей в `dataset/.venv`:

```bash
dataset/.venv/bin/python dataset/run.py build --mode public --out dataset/builds/public-v1
dataset/.venv/bin/python dataset/run.py inventory --source-root dataset --out dataset/logs/input_inventory.json
dataset/.venv/bin/python dataset/run.py build --mode local --source-root dataset --inventory dataset/logs/input_inventory.json --out dataset/builds/local-v1
dataset/.venv/bin/python dataset/run.py release --root dataset/builds/public-v1 --mode public --out dataset/releases/fsp-eval-1.0.0-public.zip
dataset/.venv/bin/python dataset/run.py release --root dataset/builds/local-v1 --mode local --out dataset/releases/fsp-eval-1.0.0-local.zip
```

Существующие каталоги/архивы не перезаписываются. Для повторной сборки задайте
новый путь. Одинаковые входы, код, версия Python, seed и workflow-report дают
побайтно одинаковые файлы и ZIP. Манифест не включает сам себя; checksum
охватывает манифест, но не собственный файл. Проверка не меняет пакет.

`inventory` читает все байты raw-источников, включая большие архивы; это может
занять несколько минут. Local build использует первые 100000 записей основных
таблиц «Работы в России» и до 200 отобранных записей на тип. Лимит регулируется
`--scan-limit`. Это ограниченная выборка, не полный обзор рынка.

## Что лежит внутри

- `data/synthetic/`: 480 профилей, 48 потребностей, 48 пулов по 10 кандидатов;
  480 pair judgments отдельно в `labels/`. Это фикстуры, не реальные люди.
- `assessment/`: 480 симулированных попыток выбранного уровня, 1920 вопросов;
  эталоны вычисляются отдельными решателями. Реальных попыток людей 0.
- `scenarios/`: спецификации пяти обязательных сценариев; их API-проверки
  выполняются отдельно на тестовой БД, не во время сборки данных.
- `reports/`: реальные результаты вызова чистых функций MVP, повторного
  тестирования и дискриминативности; структурный PASS не означает идеальный MVP.
- Local-only: Tianchi, ограниченная русская выборка, TalentCLEF validation,
  CareerCorpus с исходными значениями оценок. Не смешиваются с synthetic gold.
- `sources.json`, `SOURCES.md`, `input_inventory.json` (локальный пакет):
  источники, версии, права, хеши. `source_refs` у каждой записи.

Исходные шаблоны/оценщик MVP включены в `snapshot/` с хешами. Для сборки нужен
репозиторий приложения (`--repo`), но проверка и повтор matching-оценки готового
публичного пакета не требуют приложения, БД, сети, LLM или исходных 40 ГБ.

## Импорт

По умолчанию только dry-run. Для реального импорта оператор отдельно создаёт
БД **fsp_dataset_eval**, устанавливает `requirements-import.txt`, передаёт DSN
через `FSP_DATASET_EVAL_DSN` и использует `--apply`. Разрешены только таблицы
схемы `fsp_evaluation`, одна транзакция, повтор идемпотентен по хешу релиза и ID.
Базы `fsp` и `fsp_test` отвергаются. Реальные профили не становятся аккаунтами,
приглашениями или подтверждёнными грейдами приложения. Рабочая БД сервиса не
изменяется. Пароли и DSN не передавайте в аргументах команд или Git.

После создания отдельной БД и настройки прав пользователя, из распакованного пакета:

```bash
../fsp-eval-venv/bin/python -m pip install -r requirements-import.txt
read -rsp 'DSN отдельной БД fsp_dataset_eval: ' FSP_DATASET_EVAL_DSN
export FSP_DATASET_EVAL_DSN
../fsp-eval-venv/bin/python run.py import-db --root . --apply
unset FSP_DATASET_EVAL_DSN
```

В `fsp_evaluation.records` сохраняются тип записи, split и полный JSONB-документ;
`release_sha256` связывает запись с манифестом в `fsp_evaluation.releases`.
Команда одинаково работает с публичным и локальным пакетами.

## Публикация

Публичный ZIP содержит только собственные синтетические данные, код и отчёты.
Локальное дополнение нельзя перепаковать с `--mode public`: команда откажет.
В Git не включаются `.env`, raw_sources, локальные builds/releases, исходные
входные документы. Публичный архив формируется по манифесту, не glob всей папки.
Лицензия собственного кода/синтетики MIT; права сторонних источников отдельны.

Назначение, методика, ограничения: `DATASET_CARD.md`, `ANNOTATION_GUIDE.md`,
`MVP_COMPATIBILITY.md`, `REQUIREMENTS_TRACEABILITY.md`, `AUDIT_PASSPORT.json`.

## Совместимость сборщика 1.0.1 с банком 2.0.0

Схема результатов теперь допускает дробный score (например, 87,5 за 7/8),
сохраняя диапазон 0–100. Старые целочисленные результаты остаются допустимыми.
Новые сборки снимают текущую версию банка. Опубликованные ZIP/метрики 1.0.0
не изменены и описывают прежний снимок, а не банк 2.0.0. Новые сравнения банка
находятся в `evaluation/bank_v2_results.json` основного репозитория.

## Обучение на реальных российских событиях

Отдельный воспроизводимый конвейер и его фактические результаты описаны в
[training/README.md](training/README.md). Он использует исходные связи Trudvsem,
а не синтетический eval ZIP и не искусственные пары из корпусов вакансий.
Обучение и проверка модели не означают автоматического включения её в MVP.

10 октября подготовлен [V3 с опытом работы и образованием](training/README_V3.md):
829 реальных пар, девять семейств моделей и групповая кросс-валидация.
[Результаты и ограничения](training/RESULTS_V3.md) показывают наблюдаемый прирост
AP при обогащении, но не подтверждают устойчивое улучшение персонального подбора.

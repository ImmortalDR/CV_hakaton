# Обучение на «Работе в России»

Основной предметный набор — **V2: принятие/отказ в ответ на отклик**.
V1 сохранён как первый диагностический эксперимент.

Этот каталог содержит отдельный воспроизводимый эксперимент на реальных
событиях. Он не изменяет БД или ранжирование работающего MVP.
Смысл задачи и фиксированные правила: [EXPERIMENT.md](EXPERIMENT.md).
Фактический результат запуска: [RESULTS.md](RESULTS.md).

Продолжение от 10 октября: [V3 — история работы, образование и групповая
кросс-валидация](README_V3.md). Исходные V1/V2 и их результаты сохранены.

## Команды

Из `/root/hakaton`, Python 3.12. На текущем сервере зависимости уже есть
в `.venv`. Для другого окружения установите `requirements.lock.txt`.
Нужны существующие четыре CSV в `dataset/raw_sources/trudvsem/`.
Ничего не скачивается и `.env` не читается.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 nice -n 10 .venv/bin/python dataset/training/prepare.py \
  --source dataset/raw_sources/trudvsem --out dataset/builds/trudvsem-training-v1
.venv/bin/python dataset/training/pairs.py --root dataset/builds/trudvsem-training-v1
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 nice -n 10 .venv/bin/python dataset/training/train.py train \
  --root dataset/builds/trudvsem-training-v1 --out dataset/builds/trudvsem-model-v1
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m pytest dataset/training/tests -q
```

Для основного набора V2 после этих команд:

```bash
OPENBLAS_NUM_THREADS=1 .venv/bin/python dataset/training/application_pairs.py \
  --root dataset/builds/trudvsem-training-v1 --source dataset/raw_sources/trudvsem \
  --out dataset/builds/trudvsem-decisions-v2
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python dataset/training/train.py train \
  --root dataset/builds/trudvsem-decisions-v2 --out dataset/builds/trudvsem-model-v2
```

V2 сверяет прямые ссылки на ответы и восстанавливает дату создания отклика;
поэтому ещё раз читает `invitations.csv`. Пары V1 нужны для честного отчёта
о пересечениях двух экспериментов. Первое чтение исходников занимает десятки
минут; повторное обучение использует уже собранный JSONL.

Каталоги результатов не перезаписываются: для повторного запуска используйте
другой `--out`. После прерывания первого этапа повторите его команду с `--resume`.
Завершённые этапы и хеши проверяются, частичная производная таблица
пересобирается. Готовая сборка с `scan.json` не перезаписывается.
Первый этап читает все записи четырёх файлов; SQLite хранит
события и необходимые версии документов. Потоковый отбор не требует загрузки
исходных десятков гигабайт в память. Результаты локальны, права по умолчанию 600/700.
У старого `dataset/run.py build --mode local` остаётся прежнее назначение —
упаковка оценочных сценариев; он не заменяет этот обучающий конвейер.

## Что получается

- `index.sqlite`, `scan.json`: локальный индекс, полные хеши и число записей входов.
- `pairs.jsonl`, `pairs-report.json`: реальные связанные пары, происхождение меток,
  даты версий, исключения и исходное разбиение. Строка `source_refs` — номер
  записи CSV после заголовка, с единицы; переносы внутри поля его не увеличивают.
- `split-manifest.json`: окончательные списки после удаления близких копий.
- `model.joblib`: словарь, IDF и реально обученные веса логистической регрессии.
  Основная версия лежит в `dataset/builds/trudvsem-model-v2/`.
- `training-report.json`: выбор по validation, test, baseline, контроль без
  резюме, интервалы, версии библиотек и хеши.
- `test-predictions.jsonl`: локальные предсказания для воспроизведения метрик.

Проверить собственные два текста можно так:

```bash
OPENBLAS_NUM_THREADS=1 .venv/bin/python dataset/training/train.py predict \
  --model dataset/builds/trudvsem-model-v2/model.joblib \
  --candidate-file /tmp/candidate.txt --need-file /tmp/need.txt
```

`joblib` загружайте только из собственного проверенного запуска: формат способен
выполнять код. Выход — некалиброванный score исторического события. Он не
означает процент соответствия или подтверждённый уровень специалиста.

## Происхождение и публикация

Основной источник: [ИНИД / РЦНИ, «Работа в России», версия 02.12.2021](https://data.rcsi.science/data-catalog/datasets/186/).
В карточке приведены период 2018–2021 и лицензия CC BY-SA. У события остаётся
конкретный файл/запись; `scan.json` фиксирует байтовый снимок. Данные исторические.
Тексты содержат самоописание и могут содержать персональные сведения; удаление
e-mail/телефонов/URL не превращает их в гарантированно анонимные данные.

В Git публикуются только собственный код, методика и агрегированные отчёты.
Реальные тексты, построчные метки, индекс и веса остаются в исключённом `builds/`.
Существующий публичный synthetic eval ZIP сохраняет свою роль и версию.
Сертификата, экспертной разметки или подтверждённой рыночной валидности нет.
Для защиты корректное название: «воспроизводимый исторический набор реальных
взаимодействий с аудитом происхождения и ограничений», не «сертифицированный
эталон профессиональной пригодности».

# V4 — данные и модель, отдельно от сервиса

Протокол: [EXPERIMENT_V4.md](EXPERIMENT_V4.md). Результаты: [RESULTS_V4.md](RESULTS_V4.md).
Карточка данных: [DATA_CARD_V4.md](DATA_CARD_V4.md). Реальные тексты, индексы, эмбеддинги и веса хранятся
только в игнорируемом `dataset/builds/`, не в GitHub. Старые V1–V3 сохранены.
Источник: [Trudvsem / RCSI](https://data.rcsi.science/data-catalog/datasets/186/).
E5: [исходная модель](https://huggingface.co/intfloat/multilingual-e5-small),
[зафиксированный ONNX-экспорт](https://huggingface.co/Xenova/multilingual-e5-small/tree/761b726dd34fb83930e26aab4e9ac3899aa1fa78).
Права на исходные данные и веса не заменяются лицензией нашего кода.

## Среда и подготовка

Python 3.12; отдельное окружение, две CPU-нити. Команды из корня репозитория.
Каталоги завершённых сборок не перезаписываются: для повторения используйте
новые `--out`. Прерванные index/enrichment имеют проверяемые checkpoint.

```bash
python3 -m venv dataset/builds/v4-env
dataset/builds/v4-env/bin/pip install -r dataset/training/requirements-v4.lock.txt
python3 dataset/training/fetch_e5_v4.py --out dataset/builds/e5-small-onnx
python3 dataset/training/expand_v4.py --base dataset/builds/trudvsem-training-v1 --source dataset/raw_sources/trudvsem --out dataset/builds/trudvsem-index-v4
python3 dataset/training/enrich.py index --source dataset/raw_sources/trudvsem --root dataset/builds/trudvsem-index-v4 --out dataset/builds/trudvsem-enrichment-v4
dataset/builds/v4-env/bin/python dataset/training/freeze_v4.py anchors --inputs dataset/builds/trudvsem-training-v1/pairs.jsonl dataset/builds/trudvsem-decisions-v2/pairs.jsonl dataset/builds/trudvsem-decisions-v3-final/pairs.jsonl --out dataset/builds/trudvsem-legacy-v4
python3 dataset/training/enrich.py pairs --root dataset/builds/trudvsem-index-v4 --enrichment dataset/builds/trudvsem-enrichment-v4 --anchors dataset/builds/trudvsem-legacy-v4 --out dataset/builds/trudvsem-pairs-v4-raw
dataset/builds/v4-env/bin/python dataset/training/freeze_v4.py freeze --raw dataset/builds/trudvsem-pairs-v4-raw/pairs.jsonl --legacy dataset/builds/trudvsem-legacy-v4/pairs.jsonl --out dataset/builds/trudvsem-decisions-v4
dataset/builds/v4-env/bin/python dataset/training/corpus_v4.py --index dataset/builds/trudvsem-index-v4/index.sqlite --pairs dataset/builds/trudvsem-decisions-v4/pairs.jsonl --out dataset/builds/trudvsem-corpus-v4
```

`enrich.py pairs` создаёт промежуточное разбиение старой процедурой; **обучение
разрешено только на следующем результате freeze_v4**, который учитывает все
legacy-компоненты и близкие копии. Старые наблюдения используются в train,
а не выдаются за новый контрольный набор. Прежние результаты не заменяются.

## Обучение, проверка, интерфейс

```bash
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 dataset/builds/v4-env/bin/python dataset/training/experiment_v4.py train --pairs dataset/builds/trudvsem-decisions-v4/pairs.jsonl --corpus dataset/builds/trudvsem-corpus-v4/corpus.jsonl --encoder dataset/builds/e5-small-onnx --cache dataset/builds/e5-cache-v4.sqlite --out dataset/builds/trudvsem-model-v4
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 dataset/builds/v4-env/bin/python dataset/training/experiment_v4.py replay --pairs dataset/builds/trudvsem-decisions-v4/pairs.jsonl --root dataset/builds/trudvsem-model-v4
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 dataset/builds/v4-env/bin/python -m pytest dataset/training/tests -q
```

Выбранное семейство — `winner` в `selection.json`, его артефакт —
`<winner>.joblib`. Загружать можно только собственные доверенные joblib-файлы.
Векторизация E5 локальная и замороженная; обучение классификатора/ранжировщика
поверх неё не означает дообучения трансформера. Словарь расширенного корпуса
обучается без меток; смысл этих текстов не превращается в экспертные суждения.

Потребность: UTF-8 TXT, минимум 60 символов. Кандидаты: UTF-8 JSONL:

```json
{"candidate_id":"demo-1","candidate_base_text":"Разработчик Python, REST API и PostgreSQL","work_text":"Разработка и сопровождение серверных приложений","education_text":"Прикладная информатика"}
```

```bash
dataset/builds/v4-env/bin/python dataset/training/rank_v4.py --root dataset/builds/trudvsem-model-v4 --need /path/need.txt --candidates /path/candidates.jsonl
```

`Ranker` загружает проверенный по SHA артефакт один раз, а нейросетевой encoder
только для нуждающихся в нём семейств. Текстовые варианты работают без ONNX-весов.
Для E5 добавьте `--encoder dataset/builds/e5-small-onnx --cache /private/cache.sqlite`.
При интеграции сохраняйте экземпляр Ranker и заранее кодируйте профили: полный
повторный прогон резюме через E5 на каждый HTTP-запрос не измерялся как приемлемый.
Для выбора конкретного исследовательского варианта предусмотрен `--family`.
Job-only намеренно недоступен в интерфейсе подбора: это диагностический контроль.

Ответ содержит версию, семейство, SHA/цель модели и список `candidate_id`, относительный
`score`, `status`. Недостаточный текст → `score=null`; одинаковые ID запрещены.
Баллы не калиброваны как вероятность найма. Входные категории, согласия,
подтверждённые навыки и правила ФСП проверяет приложение, **до и независимо
от вызова**. Модуль ничего не записывает в БД и не присваивает грейд.
Для адаптера второй задачи предусмотрена явная отметка
`production_promotion_allowed=false`; автоматического включения в сервис нет.

## Оценка и ограничения

Главная метрика NDCG@10 вычисляется только для достаточных смешанных групп.
`null` означает отсутствие подходящих групп, а не нулевое качество. Малые
группы и AP подписаны отдельно. Не выбирать test-победителя задним числом.
Recall@100 относится к ограниченному, датированному пулу: test плюс отдельная
фиксированная выборка реальных профилей. Это не все миллионы резюме.
Неизвестная релевантность посторонних кандидатов не
оценивается как отказ. При <=100 кандидатах такой запрос тривиален и считается
отдельно в отчёте. Это не доказательство профессиональной пригодности.

Новый test отделён от собственных V1–V3 экспериментов по сущностям и копиям.
Неизвестен полный предобучающий корпус E5: отсутствие пересечений с ним
не доказано. Наблюдения исторические, отбор закрытых взаимодействий смещён,
актор ответа не подтверждён издателем отдельно. Людей-разметчиков и
сертификации нет. Полное нейросетевое дообучение/проверка на людях не следуют
из успешного выполнения этого скрипта.

## Расширенный проверочный пул поиска

Чтобы top-100 не оказался тривиальным на малом test, до оценки отдельно
фиксируется выборочный пул до 2 000 дополнительных людей. Они не используются
как отрицательные метки. Исторические профили восстанавливаются на дату каждого
запроса; исключаются люди/CV train, validation, legacy и близкие копии их текстов.

```bash
OPENBLAS_NUM_THREADS=2 dataset/builds/v4-env/bin/python dataset/training/retrieval_v4.py prepare --index dataset/builds/trudvsem-index-v4/index.sqlite --history dataset/builds/trudvsem-enrichment-v4 --pairs dataset/builds/trudvsem-decisions-v4/pairs.jsonl --legacy dataset/builds/trudvsem-legacy-v4/pairs.jsonl --out dataset/builds/trudvsem-retrieval-v4
OPENBLAS_NUM_THREADS=2 dataset/builds/v4-env/bin/python dataset/training/retrieval_v4.py evaluate --root dataset/builds/trudvsem-retrieval-v4 --model dataset/builds/trudvsem-model-v4/word_cosine.joblib --encoder dataset/builds/e5-small-onnx
```

Word-artifact нужен для уже обученного на train словаря, а не для выбора по test.
Результат — `retrieval-report.json`. Документы/манифест запросов, известные
положительные и эмбеддинги остаются приватными. Изменять пул после просмотра
метрик для улучшения цифры нельзя. Это дополнительная оценка поиска; она не
устраняет нехватку больших групп с известными исходами для NDCG@10.

## Дополнительная V4-CV

[Протокол V4-CV](EXPERIMENT_V4_CV.md) введён после результатов первой серии.
Это адаптивное исследование на dev, **не новый слепой test**. Четыре групповых
fold, повторное обучение словарей/scaler, исключение fold-heldout из корпуса,
выбор по OOF внутри вакансий. Исходные V4 результаты сохранены.

```bash
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 dataset/builds/v4-env/bin/python dataset/training/cv_v4.py --pairs dataset/builds/trudvsem-decisions-v4/pairs.jsonl --corpus dataset/builds/trudvsem-corpus-v4/corpus.jsonl --base dataset/builds/trudvsem-model-v4 --out dataset/builds/trudvsem-model-v4-cv
OPENBLAS_NUM_THREADS=2 dataset/builds/v4-env/bin/python dataset/training/experiment_v4.py replay --pairs dataset/builds/trudvsem-decisions-v4/pairs.jsonl --root dataset/builds/trudvsem-model-v4-cv
```

Для CLI дополнительной серии передайте `--root dataset/builds/trudvsem-model-v4-cv`.
Это не разрешает производственное включение автоматически.

## Передача участнику команды

Приватный архив на сервере:
`dataset/releases/trudvsem-training-2026-10-10-v4-local.zip`.
Внутри подготовленные данные, 17 артефактов двух серий, фиксированный E5,
код, зависимости и отчёты. `LOCAL_ONLY.txt` содержит команды для распакованной
версии. Интернет при replay и inference не нужен; зависимости Python должны
быть установлены заранее. Архив с реальными текстами не загружать в публичный GitHub.

```bash
python3 dataset/training/package_v4.py --out /private/new-v4-local.zip
python3 dataset/training/package_local.py --verify /private/new-v4-local.zip
```

Второму участнику нужны `rank_v4.Ranker`, входной JSONL и SHA выбранного
артефакта. Основная серия по умолчанию использует word cosine, дополнительная
V4-CV — char cosine. Это исследовательские варианты: статистического основания
для автоматической замены ранжирования работающего сервиса пока нет.

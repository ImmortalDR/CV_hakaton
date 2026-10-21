# Разработка и проверка

[Назад к документации](README.md). Рабочая база — `main`; изменения ведите в коротких тематических ветках. [Правила Git](GIT_WORKFLOW.md).

## Зависимости

Python 3.12, PostgreSQL 16, Node.js 22, системные шрифты DejaVu Sans. Docker-запуск описан в [README](../README.md). Для локальной разработки из корня репозитория:

```bash
python3 scripts/configure.py
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.lock
docker compose up -d db
docker compose exec -T db createdb -U fsp fsp_test
```

`createdb` нужен один раз; `already exists` означает, что БД подготовлена. Секреты хранятся в игнорируемом `.env`. Не публикуйте его и не выполняйте `source .env`.

## Серверные тесты

```bash
COOKIE_SECURE=false python3 scripts/run_local.py .venv/bin/pytest -q tests
```

Тесты очищают только отдельную БД с точным именем `fsp_test`; рабочую БД `fsp` не использовать. SMTP заменён заглушкой — обычный pytest не отправляет письма. Тесты исследовательских инструментов входят в этот же набор. Результаты до и после объединения веток разделены в [отчёте](REPOSITORY.md).

## Frontend и разработка без контейнеров приложения

```bash
cd apps/web
npm ci
npm run build
```

Для режима разработки оставьте PostgreSQL, остановите только `web api` своего Compose-проекта. Из корня запустите:

```bash
python3 scripts/run_local.py .venv/bin/alembic -c apps/api/alembic.ini upgrade head
python3 scripts/run_local.py .venv/bin/python -m fsp.seed
python3 scripts/run_local.py .venv/bin/uvicorn fsp.main:app_factory --factory --host 127.0.0.1 --port 8007 --no-access-log
```

Во втором терминале выполните `npm run dev` в `apps/web`. Vite проксирует `/api` на порт 8007. `seed` добавляет отсутствующие демонстрационные данные; используйте отдельную среду разработки.

## Браузер и измерения

```bash
.venv/bin/playwright install --with-deps chromium
python3 scripts/run_local.py .venv/bin/python tests/browser_flow.py
python3 scripts/run_local.py .venv/bin/python tests/load_probe.py
PYTHONPATH=apps/api:. .venv/bin/python -m evaluation.bank_v2_audit
```

Браузерный сценарий создаёт вымышленные аккаунты в указанной среде; нагрузочный сценарий создаёт нагрузку. Выполняйте их на своём тестовом стенде. Эталонный решатель читает локальную БД, публичный API не выдаёт ответы до завершения теста.

`evaluation/run.py` и `evaluation/research_audit.py` сохраняют исторические эксперименты банков 1.1.0 и 1.2.0. Их результаты не заменяют проверку текущего банка 2.1.1. Подготовка исследований с людьми описана в [протоколах](delivery/VALIDATION_STUDIES.md); пустые шаблоны не являются результатами пилота. Исследование V4 использует отдельные [зависимости и данные](../dataset/training/README_V4.md).

## Документация

Markdown — редактируемый источник. Текущие PDF/DOCX собираются без перезаписи презентации:

```bash
.venv/bin/python scripts/build_delivery.py --docs-only
.venv/bin/python scripts/build_final_docs.py
.venv/bin/python scripts/build_stage_a_docs.py
mkdir -p audit/docx-render
libreoffice --headless --convert-to pdf --outdir audit/docx-render docs/delivery/FSP_MVP.docx docs/delivery/FINAL_REPORT_2026-10-21.docx docs/delivery/STAGE_A.docx
.venv/bin/python scripts/check_current_docs.py --rendered-docx audit/docx-render
```

Проверьте также внешний вид экспортов. `scripts/check_delivery.py` и `scripts/check_documentation.py` относятся к прежним комплектам: исторические критерии не являются проверкой текущего релиза. Снимки старых отчётов не перезаписывайте новыми измерениями.

## Структура проекта

| Каталог | Назначение |
|---|---|
| `apps/api`, `apps/web` | Приложение и миграции PostgreSQL |
| `tests`, `scripts` | Проверки, настройка и сборка материалов |
| `evaluation` | Оценка банка и подбора, инструменты исследований |
| `dataset` | Схемы, воспроизведение и опубликованные результаты; частные данные исключены |
| `docs`, `demo` | Документация, доказательства, презентация и сценарий |

Полный архив первоначальных сторонних проектов сохранён локально и не нужен для запуска. Происхождение заимствований — в [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md).

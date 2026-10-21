# Происхождение и лицензии

Собственная реализация приложения и банка задач: MIT, см. LICENSE.

В `apps/web/src/ui.tsx` адаптированы простые компоненты EmptyState,
ErrorState и StatCard из HireDesk (Abhinav Tarigoppula, 2026, MIT).
Исходная лицензия сохранена в `licenses/HireDesk-MIT.txt`. Источник:
локальная предоставленная подборка `github/hiredesk-mern/`, файл компонентов
UI. CSS и доменная логика нового приложения написаны заново.

Из PrairieLearn использован только общий принцип параметризованных задач
с серверным эталоном. Его код, сервисы и лицензированные материалы не перенесены.
ATS, Kaggle, OpenResume, Reqcore, Docling, Judge0, catsim и
sentence-transformers не являются runtime-зависимостями и не дают метрики
качества этому MVP. Их результаты не переиспользованы как наши измерения.

Дизайн презентации получен из предоставленного организаторами шаблона
«ЛЦТ_2026_Шаблон презентации ФСП(1).pptx». Логотипы и элементы шаблона
не объявляются собственностью авторов кода и не перелицензируются MIT.
Данные компании, кандидатов, достижений и разметки полностью синтетические.

Основные runtime-зависимости: React (MIT), Vite (MIT, сборка),
TypeScript (Apache-2.0, сборка), Lucide (ISC), FastAPI/Starlette (MIT),
SQLAlchemy/Alembic (MIT), Argon2-cffi (MIT), ReportLab (BSD),
Psycopg (LGPL-3.0, используется без изменения), PostgreSQL (PostgreSQL License),
Nginx (BSD-2-Clause). Точные версии и транзитивные пакеты — в lock-файлах.
Лицензии upstream остаются в установленных пакетах/образах.

PDF использует встроенный DejaVu Sans (лицензия DejaVu / Bitstream Vera,
поставляется пакетом fonts-dejavu-core). PyMuPDF применяется только в среде
разработки для чтения и проверки документов; его AGPL-компоненты не входят
в runtime-образ API. Генерация пользовательского PDF выполняется ReportLab.
python-pptx и python-docx (MIT) применяются для материалов сдачи.

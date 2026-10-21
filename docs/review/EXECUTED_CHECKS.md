# Реальные проверки текущей сессии

Дата: 7 октября 2026. Среда: Ubuntu24.04, Python3.12, Node установлен.
Приложение не создано: все его сборки, миграции, unit/integration/E2E,
права, нагрузка и оценка качества имеют статус **not_run**.

| Команда / проверка | Результат | Границы |
|---|---|---|
| `git ls-remote https://github.com/ImmortalDR/CV_hakaton.git` | pass, пустые refs | Начальное состояние удалённого репозитория |
| `python3 scripts/verify_workspace.py --root /root/hakaton/hakaton_astra_workspace/hakaton` | fail: 8162 файла проверены, 1 missing | Вложенная копия неполна; отсутствующий файл найден в оригинале и совпадает по SHA-256 |
| Сверка оригинальных входов с MANIFEST.sha256 с учётом fsp_mvp_bundle | pass: 8141/8141, failures=[] | Только целостность, не содержательное чтение |
| Первый запуск `scripts/reproduce_findings.py` с NumPy2.5.3 | fail: X86_V2 baseline несовместим с CPU | Ошибка окружения до завершения всего скрипта |
| Повтор с версиями `scripts/requirements-review.txt` | pass: exit0 | Точечные дефекты; JSON в reproduced_findings.json; это не тесты MVP |
| `libreoffice -env:UserInstallation=file:///root/hakaton/tmp/lo-review --headless --convert-to pdf --outdir audit/current 'ЛЦТ_2026_Шаблон презентации ФСП(1).pptx'` | pass: PDF37слайдов создан и осмотрен | Подстановка отсутствующих шрифтов LibreOffice возможна; оригинал не изменён |
| `python3 scripts/review_inventory.py` | pass | Собирает реальные записи чтения и точные SHA-дубли; сам ничего не объявляет прочитанным |
| `python3 -m py_compile scripts/review_inventory.py` | pass | Только синтаксис нового инструмента |
| `git diff --cached --check` на созданных файлах ревью | pass | Не заявляется форматирование всех исходных документов |
| `GIT_TERMINAL_PROMPT=0 git push -u origin codex/fsp-mvp` | fail: terminal prompts disabled, cannot read Username | Локальный git не имеет HTTPS-аутентификации. GitHub connector имеет доступ к репозиторию; публикация через него пока не выполнялась |

Локальный начальный коммит: `a28f287`, ветка `codex/fsp-mvp`.
После него внесены уточнения инструментов и этого отчёта; актуальный HEAD
смотреть через `git log -1 --oneline`.

Ни один Docker Compose-проект не запускался. Защищённые ресурсы «Интеллект»
не изменялись. При установке LibreOffice needrestart отложил перезапуск
Docker и сообщил, что перезапуск контейнеров не требуется.

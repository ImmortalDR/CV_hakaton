# CC5 · Секреты и конфигурация

DoD: checklist + исполняемая проверка [check_closed_contour_config.py](../../../scripts/check_closed_contour_config.py). Запуск: `python3 scripts/check_closed_contour_config.py`. Проверяет индекс git, ignore и допустимые placeholder-значения .env.example; не заменяет сканирование всей истории git.

| Проверка | Действие / владелец |
|---|---|
| ☐ Новый секрет БД | `python3 scripts/configure.py`, файл 0600; не переносить секрет демо. Админ |
| ☐ Существующий .env | configure сохраняет; сверить значения в защищённом редакторе. Не печатать в лог |
| ☐ DEMO_MODE=false | Чистая рабочая БД; false не удаляет синтетику из старой БД. Админ |
| ☐ PUBLIC_URL | Доступный пользователям HTTPS URL, без лишнего path; проверить ссылки в письмах |
| ☐ COOKIE_SECURE=true | После подключения TLS; HTTP проверка с реальными сессиями не принимается |
| ☐ SMTP | Внутренний relay, STARTTLS, отдельная учётка с минимальными правами; протестировать обе роли |
| ☐ .env не в git | Автоскрипт проверяет также вложенные runtime .env.*; example допускается только с placeholder |
| ☐ Ротация | Смену пароля существующей PostgreSQL БД проводить согласованно в БД и .env: одна правка POSTGRES_PASSWORD не меняет пароль уже инициализированного тома |
| ☐ Хранение | .env в защищённом каталоге, root/Docker admins доверенные; Docker inspect способен раскрыть env; secrets manager пока не интегрирован |
| ☐ Логи | Не включать shell xtrace, не публиковать compose config/inspect с env, SMTP links/cookies/dumps; перед передачей evidence просмотреть |
| ☐ Проверка утечки | При компрометации сменить SMTP/DB пароль, завершить сессии, расследовать; встроенного incident workflow нет |

Источники: [configure](../../../scripts/configure.py), [env](../../../.env.example), [gitignore](../../../.gitignore), [main session_cookie/send_auth_mail](../../../apps/api/fsp/main.py), [compose](../../../compose.yaml). DEMO defaults не являются настройками промышленной эксплуатации. Dry-run пишет разрешённый технический лог без дампа env; каталог временной установки и его секрет удаляются после down.

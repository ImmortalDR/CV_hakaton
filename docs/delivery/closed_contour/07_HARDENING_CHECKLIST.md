# CC8 · Приёмка внутреннего контура

DoD: ≥8 проверок, ≥2 выполненные автоматические. ☐ означает действие на инфраструктуре заказчика, не заранее поставленную приёмку. Доказательства локального прогона приведены отдельно.

| Проверка | Авто / человек | Свидетельство или действие |
|---|---|---|
| ☐ .env исключён из git | Авто | `python3 scripts/check_closed_contour_config.py`: [PASS](evidence/config-hygiene.txt) |
| ☐ Секреты случайные, файл 0600 | Авто + админ | [Повтор configure и права](evidence/config-negative-controls.txt): PASS; рабочую ротацию согласовать |
| ☐ Только loopback/private bind | Авто + сетевик | Dry-run loopback ephemeral, без DB publish: [лог](evidence/cc-dry-run-20261021T185211Z-233571.log); A/B на VM проверить `ss -lnt`, firewall и curl с недоверенной подсети |
| ☐ TLS/CA и secure cookies | Человек | Проверить сертификат, редирект HTTP, cookie Secure в браузере; NOT_RUN у заказчика |
| ☐ DEMO_MODE=false и чистая БД | Авто + админ | Dry-run health demo=false, demo endpoint 404; не переносить review accounts |
| ☐ SMTP только разрешённый relay | Человек | Доставка/STARTTLS, отзываемые credentials, ссылки PUBLIC_URL; NOT_RUN |
| ☐ API/worker/db недоступны снаружи | Авто + сетевик | Dry-run compose ps: только web 127.0.0.1; customer firewall и Docker rules проверить отдельно |
| ☐ Backup PostgreSQL и restore | Человек | Зашифрованный dump вне git, восстановление в другую БД, согласованные RPO/RTO; NOT_RUN |
| ☐ Контроль SSH/Docker/socket | Человек | Именные админы, минимальные права, нет mount docker.sock в приложении; журнал выдачи доступа |
| ☐ Обновления и image scan | Человек + CI заказчика | Сканировать образы/lockfiles, закрепить digest после теста, окно обновления и rollback; NOT_RUN полного скана |
| ☐ Логи и инциденты | Человек | Ограничить Docker log size/retention, не писать токены/query, установить контакты реагирования; NOT_RUN |
| ☐ Health/worker/disk/DB alerts | Человек | Настроить мониторинг; worker не имеет healthcheck, проверка процесса не доказывает выдачу по расписанию |
| ☐ CPU/RAM/connection limits | Человек | Dry-run 1 CPU/512m на сервис — для smoke; рабочие лимиты измерить; base compose их не задаёт |
| ☐ ACL/согласия и удаление | Мы + оператор | Повторить межорганизационные тесты, PDF, revoke; принять процедуру удаления/retention до рабочих ПДн |
| ☐ Выход в сеть | Человек | Build deps разрешены; runtime SMTP; лишние направления закрыть, mirrors/CA согласовать |

Никакая строка этого списка не подтверждает сертификацию или промышленный SLA. Автопроверки подтверждают конкретную изолированную установку; human отмечает реальный контур после его настройки.

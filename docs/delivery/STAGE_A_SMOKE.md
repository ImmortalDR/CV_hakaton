# Проверка этапа A после восстановления черновика

Дата: 2026-10-21T10:35:44.229363+00:00. Код стенда: `7f3dde4cbe5b17b0f16154e4ede90a91673428f8`. Канон: COMPREHENSIVE_STAGE_A_2026-10-21.md + accept B01.

97 pytest PASS; 20 отдельных целевых проверок PASS; [smoke](stage-a-smoke.json): 18 групп PASS, page_errors=[]; [контрпроба](evidence/q1-recovery/probe.log): HTTP503, два несохранённых ответа, отмена reload, ручной повтор, поздний ACK и более новый ввод PASS.

Команды и выводы: [VERIFY_STAGE_A_PROTOCOL](VERIFY_STAGE_A_PROTOCOL.md). [Хеши деплоя](evidence/q1-recovery/deploy.json): API/worker равны HEAD, web build равен контейнеру и HTTPS. DB volume сохранён.

Первый цикл поймал лишнее подтверждение при возврате в тест; исправлен во втором. Прежние журналы доступны в git, не являются текущим PASS. Текущая матрица: 14 PASS, 1 PARTIAL (GitHub auth), 1 HUMAN_ONLY (отправка), 0 FAIL. Это не человеческий UX-аудит и не подтверждение отправки на площадку.

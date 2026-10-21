# CC7 · Периметр и anti-DDoS

DoD: честно разделить код и меры заказчика. [main.py security](../../../apps/api/fsp/main.py) ограничивает перечисленные auth endpoints до 20 запросов за 60 секунд на request.client.host в памяти процесса. [nginx](../../../apps/web/nginx.conf) ограничивает тело 64k. Это защита от части злоупотреблений, а не anti-DDoS.

| Угроза | Уже есть | Дыра | Владелец |
|---|---|---|---|
| Auth brute force | Локальный лимит auth, Argon2 | Сброс при restart, нет общего backend счётчика; nginx-IP может объединить клиентов | Мы — учёт идентичности/распределённость; заказчик — edge limits |
| Истощение PDF/search | 64k body, PDF lock | Общего request/concurrency лимита нет, lock не экономит канал | Мы — квоты/пагинация; заказчик — timeout/connection limits |
| Переполнение внешнего канала | Внутренняя установка может не иметь публичного маршрута | Если сервис публичен, firewall приложения не остановит объёмный DDoS | Заказчик/оператор связи — upstream фильтрация и план инцидента |
| Подделка клиентского IP | Доверенный nginx как upstream | Real IP chain не подтверждён; X-Forwarded-* от клиента нельзя считать истиной | Заказчик + мы — доверенные proxy CIDR и проверка цепочки |

`not_implemented`: enterprise WAF, anti-DDoS scrubbing, distributed limiter, per-user quotas для всех API, fail2ban rules, SIEM/SOC integration, MFA, нагрузочное доказательство стойкости. Встроенный Caddy — TLS reverse-proxy, не WAF. Npm build report не является пентестом.

Заказчик выбирает существующий WAF/reverse-proxy, лимиты соединений/тела/времени, защиту SSH (возможен fail2ban) и upstream anti-DDoS при публичном доступе. Внешний CDN/WAF не включать автоматически: TLS termination и передача данных третьей стороне требуют отдельной схемы ПДн и LEGAL_REVIEW_NEEDED. Для LAN — ACL, сегментация, мониторинг и защита от внутреннего DoS всё равно нужны. Конкретный продукт и SLA в этом пакете не выбраны и не закуплены.

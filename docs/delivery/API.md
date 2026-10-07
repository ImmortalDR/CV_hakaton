# API 1.0.0

Источник истины — `openapi.json`, выгруженный из работающего FastAPI.
Все запросы/JSON-ответы имеют схемы. Даты — ISO 8601, UTC; интерфейс
отображает московское время. Неизвестные значения представлены null/unknown,
а не положительным совпадением. Cookie HttpOnly хранит сессию.

Для POST/PUT/PATCH нужен заголовок `X-Requested-With: fsp-web`.
Неизвестные поля входа отвергаются: нельзя добавить `verified_grade`,
`seed`, `score`, `company_id` или роль в обход нужного маршрута.

| Маршрут | Доступ и результат |
|---|---|
| GET /api/health | состояние БД, версия, режим |
| GET /api/catalog | направления, навыки, уровни, версия банка, интервалы |
| POST /api/auth/register | email, пароль 10…128, роль, processing=true; 201 |
| POST /api/auth/verify | одноразовый token; успех или 400 |
| POST /api/auth/login | подтверждённый email/пароль; устанавливает cookie |
| POST /api/auth/logout | аннулирует сессию и cookie |
| GET /api/auth/me | своя роль, ID, email, признак демо |
| POST /api/auth/demo | только DEMO_MODE; candidate/employer/other_employer |
| GET/PUT /api/me/profile | только кандидат, собственный профиль и согласия |
| POST /api/me/fsp | пример demo-winner/demo-participant или unlink |
| GET/POST /api/me/attempts | история / старт {grade}; сервер выбирает вариант |
| POST /api/me/attempts/{id}/submit | только владелец; {answers:{"1":"42",…}}; повтор неизменен |
| GET/PUT /api/me/company | только своя компания |
| GET /api/candidates | только работодатель; specialization, grade, skill, fsp_only |
| GET /api/candidates/{id} | опубликованная проекция с текущими правами |
| GET /api/profiles/{id}/pdf | собственный либо доступный работодателю PDF |
| POST /api/searches | подтверждённая NeedInput; создаёт потребность и снимок |
| GET /api/searches | до 50 последних снимков своей компании |
| GET /api/searches/{id} | только свой снимок; повторная проверка приватности |
| POST /api/invitations | положительная вилка RUB и UUID request_id; 201 |
| GET /api/invitations | только свои приглашения / приглашения своей компании |
| PATCH /api/invitations/{id} | только кандидат-адресат; viewed/accepted/rejected |
| GET/POST /api/invitations/{id}/messages | участники после принятия и при действующем согласии |

Пример структурированной потребности:

```json
{"title":"Разработчик API","description":"Разработка серверных API команды",
 "specialization":"python","grades":["Junior","Middle"],
 "required_skills":["python"],"desired_skills":["testing"],
 "min_years":null,"fsp_only":false,"confirmed":true}
```

Пример предложения (ID берутся из своих разрешённых ответов, request_id
создаётся один раз на попытку отправки и повторяется при сетевом повторе):

```json
{"candidate_id":"00000000-0000-4000-8000-000000000001",
 "request_id":"00000000-0000-4000-8000-000000000002",
 "description":"Приглашаем развивать API нашей команды",
 "salary_min":120000,"salary_max":180000,"currency":"RUB"}
```

Ошибки: `{ "detail": "Понятное сообщение", "fields": [...] }`.
fields есть при ошибке валидации, содержит только имя/тип ошибки, не исходное
значение (пароли и токены в ошибку не возвращаются). 401 — вход/срок сессии;
403 — роль/согласие/CSRF; 404 — недоступная или чужая запись; 409 — конфликт,
повтор ключа с другим payload, кулдаун, истечение теста; 422 — поля;
429 — частота; 503 — недоступная доставка почты/интеграция. 404 не обещает,
что записи нет физически: может отсутствовать право доступа.

`contacts=null` до адресного разрешения. Имя и произвольные поля не
возвращаются. После принятия выдача, PDF и карточка приглашения используют
одно право компании. У другой компании contacts остаётся null.

OpenAPI содержит модели ошибок, cookie security scheme, обязательный
заголовок изменения данных и application/pdf. `/api/docs` — локальная
страница со спецификацией; внешние Swagger CDN в runtime не используются.

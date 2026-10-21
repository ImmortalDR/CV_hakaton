# Независимая adversarial-перепроверка этапа A

Дата: 2026-10-21T09:22:32.651398+00:00. Проверяемый HEAD: `6b965aca20f70efe4e6430c30aaabc102c52581d`, ветка `codex/fsp-mvp`.
Это новая проверка, не перенос прежних «14 PASS». Код продукта и scripts/smoke_stage_a.py не изменялись.

**Нельзя отправлять даже после одного лишь push: Pck1 FAIL (противоречивый changelog).**
Q4 PARTIAL: статичная надпись о подтверждённых навыках у неподтверждённого кандидата.
Pck2 PARTIAL: GitHub отстаёт. Pck5 HUMAN_ONLY: никто ничего на площадку не отправлял.
Счёт: {"PASS": 12, "PARTIAL": 2, "FAIL": 1, "HUMAN_ONLY": 1}.

## Границы и источники

Прочитаны три заданных verify-промпта, WORKSPACE_MAP, REVIEW_PROTOCOL, GIT_WORKFLOW,
канон (включая пользовательские изменения, без перезаписи), backlog и предметные findings
B01–B06/U01–U04/M01–M02. Предыдущая матрица не использовалась при вынесении вердиктов.
Содержательно прочитаны smoke, профильные тесты, процедура matching, упаковка;
App.tsx/main.py/tasks.py просмотрены по относящимся к задачам участкам.
Три смысловых прохода этой проверки: критерии → трассировка проверок/API/UI → сопоставление свежих результатов с DoD.
Это не повторное полное ревью исходной подборки: оригинальные ТЗ/транскрипт, все архивные приложения,
все исходники и бинарные материалы не перечитаны. Разработки в этой сессии нет.
Презентация проверена хешем и git diff, визуальный просмотр не выполнялся.
Хеширование, поиск строк и машинные тесты не объявляются содержательным чтением.

Pytest использует отдельную `fsp_test`: стандартная фикстура очищает только её тестовые таблицы;
рабочая БД `fsp` не сбрасывалась. Live-проверки добавляют вымышленные demo-аккаунты,
после проверки их кандидаты скрыты. Общие review-аккаунты использованы только для login.
Новый seed/эталон читался проверочным кодом на сервере, не передавался UI активной попытки.

<a id="environment"></a>
## Окружение и публикация

Первая команда сессии: `pwd && git branch --show-current && git rev-parse HEAD && git status --short && docker compose ps`.
Получено `/root/hakaton`, `6b965aca20f70efe4e6430c30aaabc102c52581d`, `codex/fsp-mvp`; api/web/db/edge healthy, worker Up.
Уже были пользовательские untracked документы и изменение канона — они не включаются в commit.
Ниже повторная фиксация после тестов, тот же HEAD:

```text
2026-10-21T09:20:06.123454+00:00
$ git branch --show-current
codex/fsp-mvp

exit=0

$ git rev-parse HEAD
6b965aca20f70efe4e6430c30aaabc102c52581d

exit=0

$ git status -sb --untracked-files=no
## codex/fsp-mvp...origin/codex/fsp-mvp [ahead 15]
 M docs/final_backlog_2026-10-20/COMPREHENSIVE_STAGE_A_2026-10-21.md

exit=0

$ curl -fsS https://85-137-26-131.sslip.io/api/health
{"status":"ok","demo":true,"version":"1.0.0"}
exit=0

$ docker compose ps
NAME                    IMAGE                                                                                         COMMAND                  SERVICE       CREATED          STATUS                    PORTS
fsp-mvp-api-1           fsp-mvp-api                                                                                   "sh -c 'alembic upgr…"   api           16 minutes ago   Up 15 minutes (healthy)
fsp-mvp-db-1            postgres:16-alpine@sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea    "docker-entrypoint.s…"   db            13 days ago      Up 9 days (healthy)       127.0.0.1:5547->5432/tcp
fsp-mvp-edge-1          caddy:2.11.7-alpine@sha256:d8542f48d34a9cf4e4c11a478865229840e87e4c96ea3f439101f31a5d35f75f   "caddy run --config …"   edge          9 days ago       Up 9 days (healthy)
fsp-mvp-task-worker-1   fsp-mvp-task-worker                                                                           "python -m fsp.task_…"   task-worker   16 minutes ago   Up 15 minutes
fsp-mvp-web-1           fsp-mvp-web                                                                                   "/docker-entrypoint.…"   web           16 minutes ago   Up 15 minutes (healthy)   127.0.0.1:3080->80/tcp

exit=0

$ git ls-remote origin refs/heads/codex/fsp-mvp
2e6d6daa5bfb59f6d5a7e7317aa41093c8f05980	refs/heads/codex/fsp-mvp

exit=0

$ docker volume inspect fsp-mvp_fsp_db --format {{.Name}} {{.CreatedAt}}
fsp-mvp_fsp_db 2026-10-07T22:42:58+02:00

exit=0

$ git diff 2e6d6da..HEAD -- demo docs/presentation

exit=0
```

`GIT_TERMINAL_PROMPT=0 git push --dry-run origin codex/fsp-mvp` (exit 128):
```text
fatal: could not read Username for 'https://github.com': terminal prompts disabled

```
Это проверка возможности push, не успешная публикация. Реальный push после verify-коммита также должен быть подтверждён отдельно.

<a id="pytest"></a>
## Свежий pytest

Команда (exit 0):
```sh
COOKIE_SECURE=false python3 scripts/run_local.py .venv/bin/pytest tests -q
```
Полный вывод:
```text
........................................................................ [ 74%]
.........................                                                [100%]
=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/fastapi/testclient.py:1
  /root/hakaton/.venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

.venv/lib/python3.12/site-packages/starlette/testclient.py:53
  /root/hakaton/.venv/lib/python3.12/site-packages/starlette/testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
97 passed, 2 warnings in 34.41s

```
В частности: draft owner/expiry/lifecycle, неполный submit с отсутствующим/false flag и пробелами,
90.625/точка/запятая/старые версии, privacy/republication, 6 scheduler tests с управляемым временем
и конкурентными ticks, соответствие production формулы выбранным весам на dev и test.

<a id="fresh-smoke"></a>
## Свежий live smoke

Команда (exit 0):
```sh
python3 scripts/run_local.py .venv/bin/python scripts/smoke_stage_a.py --out /tmp/stage-a-independent/smoke.json
```
17 групп (не старые 13), Chromium + HTTPS API:
```json
{
  "status": "pass",
  "checked_at": "2026-10-21T09:18:21.766998+00:00",
  "base_url": "https://85-137-26-131.sslip.io",
  "checks": [
    "https_health_ok",
    "openapi_exact",
    "three_review_logins_ok",
    "Q1_navigation_reload_server_draft_owner_expiry",
    "Q2_live_bank_2_1_rounding_hint",
    "Q3_direct_API_without_confirm_409_active_draft_unchanged",
    "Q3_cancel_keeps_active_accept_completes",
    "Q4_verified_published_hidden_empty_invitations_and_overview_CTA",
    "Q5_anonymous_label_selection_invitation_PDF_UI",
    "invite_accept_addressed_contacts_PDF_isolation",
    "FSP_does_not_change_grade_zero_without_FSP",
    "old_snapshot_preserved",
    "Q5_two_visible_score_sums_unique_labels_changed_banner_scroll",
    "Q5_filters_snapshot_and_score_UI",
    "Q6_live_7day_resume_no_duplicate_UI_date_equals_API",
    "Q4_hidden_overview_revoked_chat_snapshot_PDF",
    "mobile_no_horizontal_overflow"
  ],
  "page_errors": [],
  "scope": "Live HTTPS API and Chromium; 4 newly bootstrapped fictional accounts, review logins read-only; no SMTP or real-person testing; own smoke candidate hidden, own plan closed."
}
```
Q1 проверяет видимое «Ответы сохранены», переход Обзор → тест → reload, ответ и expiry, чужую запись 404.
Q3: первое подтверждение dismiss с 7 из 8, active; следующий accept → completed.
Q5: одинаковая анонимная метка selection/invitation/PDF/UI; приглашение на карточке;
два видимых score breakdown сходятся до 0.02; уникальные ярлыки; фильтры/reload/scroll;
изменённый черновик помечен, контекст свёрнут. Субъективная ясность отдана человеку.
Q6: после ответа/оценки pause/resume сохраняет единственное задание и next_issue_at;
дата в браузере сопоставлена с API в МСК. Реальных 7 дней не ждали.

<a id="blockers"></a>
## Отдельный удар по бывшим блокерам и B05

Независимый probe вне репозитория: `/tmp/stage-a-independent/blockers.py`.
Повторно создаёт изолированные demo-аккаунты (bootstrap взят из smoke), далее собственные HTTP-запросы
и чтение DOM. Он не импортирует прежний report и не использует готовые smoke verdicts.
Команда (exit 0):
```sh
python3 scripts/run_local.py .venv/bin/python /tmp/stage-a-independent/blockers.py
```
Протокол запросов/экранных текстов:
```json
[
  {
    "case": "submit_without_confirmation",
    "http": 409,
    "body": {
      "detail": "Не заполнено 7 из 8 заданий. Подтвердите завершение теста с пропусками."
    },
    "status": "active",
    "answers": {
      "1": "42"
    },
    "same_expiry": true
  },
  {
    "case": "submit_without_confirmation",
    "http": 409,
    "body": {
      "detail": "Не заполнено 8 из 8 заданий. Подтвердите завершение теста с пропусками."
    },
    "status": "active",
    "answers": {
      "1": "42"
    },
    "same_expiry": true
  },
  {
    "case": "submit_without_confirmation",
    "http": 409,
    "body": {
      "detail": "Не заполнено 8 из 8 заданий. Подтвердите завершение теста с пропусками."
    },
    "status": "active",
    "answers": {
      "1": "42"
    },
    "same_expiry": true
  },
  {
    "case": "B05",
    "published": false,
    "verified": false,
    "overview": "Ваш профиль — больше, чем резюме\nПокажите, что вы умеете\n\nТест по основному и вспомогательному навыкам поможет подтвердить выбранный уровень. ФСП ID для этого не нужен.\n\nПерейти к тестированию\nнавыки\nподтверждены",
    "invitations": "Демонстрационный стенд. Данные примеров и достижения ФСП — синтетические.\nОТ ПРЕДЛОЖЕНИЯ К ЗНАКОМСТВУ\nПриглашения\n\nИзучите условия до начала общения. При принятии контакты получит только пригласившая компания.\n\nЗагружаем приглашения\n\nСекунда — подтягиваем актуальные статусы с сервера."
  },
  {
    "case": "B05",
    "published": true,
    "verified": false,
    "overview": "Ваш профиль — больше, чем резюме\nПокажите, что вы умеете\n\nТест по основному и вспомогательному навыкам поможет подтвердить выбранный уровень. ФСП ID для этого не нужен.\n\nПерейти к тестированию\nнавыки\nподтверждены",
    "invitations": "Демонстрационный стенд. Данные примеров и достижения ФСП — синтетические.\nОТ ПРЕДЛОЖЕНИЯ К ЗНАКОМСТВУ\nПриглашения\n\nИзучите условия до начала общения. При принятии контакты получит только пригласившая компания.\n\nПока нет приглашений\n\nПодтвердите навыки тестом, чтобы попасть в категорию кандидатов."
  },
  {
    "case": "B05",
    "published": false,
    "verified": true,
    "overview": "Ваш профиль — больше, чем резюме\nАналитика данных / SQL · Junior\n\nВаш уровень подтверждён, но профиль скрыт. Включите публикацию и согласие в профиле, чтобы попасть в подбор.\n\nНастроить видимость\nнавыки\nподтверждены",
    "invitations": "Демонстрационный стенд. Данные примеров и достижения ФСП — синтетические.\nОТ ПРЕДЛОЖЕНИЯ К ЗНАКОМСТВУ\nПриглашения\n\nИзучите условия до начала общения. При принятии контакты получит только пригласившая компания.\n\nПока нет приглашений\n\nВаш уровень подтверждён. Включите публикацию и согласие на обработку в профиле."
  },
  {
    "case": "B05",
    "published": true,
    "verified": true,
    "overview": "Ваш профиль — больше, чем резюме\nАналитика данных / SQL · Junior\n\nВаш уровень подтверждён тестом. Работодатели могут найти вас в соответствующей категории.\n\nПосмотреть приглашения\nнавыки\nподтверждены",
    "invitations": "Демонстрационный стенд. Данные примеров и достижения ФСП — синтетические.\nОТ ПРЕДЛОЖЕНИЯ К ЗНАКОМСТВУ\nПриглашения\n\nИзучите условия до начала общения. При принятии контакты получит только пригласившая компания.\n\nПока нет приглашений\n\nВаш профиль опубликован, уровень подтверждён. Ожидайте приглашений работодателей; настройки видимости доступны в профиле."
  },
  {
    "case": "republication_consent",
    "contacts_after_republish": null,
    "old_chat_available": false,
    "new_accepted_chat_available": true
  }
]
```
Повторяемость probe обеспечивается полным кодом ниже; сохранить во временный файл, запустить из корня.
Он повторяет bootstrap из проверенного scripts/smoke_stage_a.py; пароли случайные и не печатаются.
```python
from pathlib import Path
# Reuse only isolated demo bootstrap, never the smoke verdict/assertions.
exec(Path('scripts/smoke_stage_a.py').read_text().split('try:\n    with sync_playwright()')[0])
records=[]
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(); ctx=b.new_context(base_url=a.base_url,extra_http_headers={'X-Requested-With':'fsp-web'})
  assert ctx.request.post('/api/auth/login',data={k:accounts[0][k] for k in ['email','password']}).status==200
  def api(path,data=None,method=None):
   r=ctx.request.fetch('/api'+path,method=method or ('POST' if data is not None else 'GET'),data=data); assert r.ok,(path,r.status,r.text()); return r.json()
  attempt=api('/me/attempts',{'grade':'Junior'}); url='/me/attempts/'+attempt['id']
  api(url+'/answers',{'answers':{'1':'42'}},'PUT')
  for payload in [{'answers':{'1':'42'}},{'answers':{},'confirm_incomplete':False},{'answers':{str(i):' ' for i in range(1,9)}}]:
   r=ctx.request.post('/api'+url+'/submit',data=payload); saved=api('/me/attempts')[0]
   record={'case':'submit_without_confirmation','http':r.status,'body':r.json(),'status':saved['status'],'answers':saved['answers'],'same_expiry':saved['expires_at']==attempt['expires_at']}; records.append(record)
   assert r.status==409 and saved['status']=='active' and saved['answers']=={'1':'42'} and record['same_expiry']
  p=ctx.new_page(); p.goto(a.base_url)
  def nav(label): p.locator('nav').get_by_role('button',name=label,exact=True).click()
  fields=['name','phone','about','specialization','claimed_grade','skills','roles','soft_skills','experience_years','processing','published','show_experience']
  for verified in [False,True]:
   if verified:
    with Session(engine) as db: qs=db.get(Attempt,attempt['id']).questions
    api(url+'/submit',{'answers':{q['id']:str(solve(q)) for q in qs}})
   for published in [False,True]:
    own=api('/me/profile'); api('/me/profile',{**{k:own[k] for k in fields},'published':published},'PUT')
    p.reload(); nav('Обзор'); overview=p.locator('.feature-banner').inner_text()
    nav('Приглашения'); invitation=p.locator('main').inner_text()
    records.append({'case':'B05','published':published,'verified':verified,'overview':overview,'invitations':invitation})
    if verified and published:
     assert 'Ваш профиль опубликован, уровень подтверждён.' in invitation
     assert 'Подтвердите навыки и опубликуйте профиль' not in invitation
     assert 'Работодатели могут найти вас' in overview and 'Посмотреть приглашения' in overview
    if verified and not published:
     assert 'профиль скрыт' in overview and 'Работодатели могут найти вас' not in overview
  emp=b.new_context(base_url=a.base_url,extra_http_headers={'X-Requested-With':'fsp-web'})
  assert emp.request.post('/api/auth/login',data={k:accounts[1][k] for k in ['email','password']}).status==200
  def invite():
   r=emp.request.post('/api/invitations',data=dict(candidate_id=accounts[0]['id'],request_id=str(uuid4()),description='Независимая проверка нового согласия',salary_min=100000,salary_max=150000,currency='RUB')); assert r.ok; return r.json()
  inv=invite(); api('/invitations/'+inv['id'],{'status':'accepted'},'PATCH')
  own=api('/me/profile'); payload={k:own[k] for k in fields}
  api('/me/profile',dict(payload,published=False),'PUT'); api('/me/profile',dict(payload,published=True),'PUT')
  after=emp.request.get('/api/candidates/'+accounts[0]['id']).json(); assert after['contacts'] is None
  old=next(i for i in emp.request.get('/api/invitations').json() if i['id']==inv['id']); assert not old['chat_available']
  new=invite(); api('/invitations/'+new['id'],{'status':'accepted'},'PATCH')
  fresh=next(i for i in emp.request.get('/api/invitations').json() if i['id']==new['id']); assert fresh['chat_available']
  records.append({'case':'republication_consent','contacts_after_republish':after['contacts'],'old_chat_available':old['chat_available'],'new_accepted_chat_available':fresh['chat_available']})
  b.close()
finally:
 with Session(engine) as db:
  for account in accounts:
   profile=db.get(Profile,account['id'])
   if profile: profile.published=False
  db.commit()
 Path('/tmp/stage-a-independent/blockers.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
print(json.dumps(records,ensure_ascii=False,indent=2))

```

**Q3 PASS:** отсутствующий флаг, false, пробельные ответы → 409, active, прежний draft/expiry.
**Бывшие B05-блокеры не воспроизвелись:** hidden не обещает нахождение; published+verified не просит
заново подтвердить навыки. **Q4 PARTIAL:** в DOM feature-banner при verified=false остаётся
декоративная надпись «навыки подтверждены». Не считать полную согласованность всех текстов доказанной.
Воспроизведение без кода: неподтверждённый кандидат → Обзор → сравнить предложение пройти тест
с надписью в круглом блоке. Новый явный invite после republish возвращает chat; сам republish — нет.

<a id="matching"></a>
## Q7: повторное измерение

Чтобы не менять evaluation/results, fixture скопирована в `/tmp/stage-a-independent/evaluation/`.
Временный cwd; исходный скрипт и модули из workspace:
```sh
cd /tmp/stage-a-independent
PYTHONPATH=/root/hakaton/apps/api:/root/hakaton /root/hakaton/.venv/bin/python /root/hakaton/evaluation/stage_a_matching.py
```
Exit 0:
```text
{"old_weights": [60, 15, 20, 5], "selected_weights": [30, 15, 45, 10], "selection": "max dev P@5; tie: minimum L1 distance to old weights, then tuple order"}
dev 1.0 -> 1.0
test 0.8 -> 0.8

```
Dev: 16 кандидатов/2 запроса; holdout: 48/8, разные ID; авторские синтетические relevance labels.
Выбор по dev P@5, равенство — L1 к старым весам, затем tuple. Holdout не выбирает веса в скрипте.
Это не доказательство, что автор никогда не видел holdout; независимых экспертов нет.
P@5 не вырос, улучшение качества найма не заявляется. VERSION `matching-1.2.0` проверена live smoke.
Тест sanity подтверждает 66 > 63.75 при более сильном тесте+ФСП, при этом неизвестный навык остаётся unknown.

Дополнительно вызвана read-only функция `evaluation.bank_v2_audit.audit()` с `PYTHONPATH=apps/api:.`;
результат не записывался поверх старого evaluation JSON. Exit 0:
```json
{"oracle_checks": 36000, "oracle_mismatches": [], "simulated_attempts": 42000}

```

<a id="hashes"></a>
## Pck3: совпадение исполняемого кода

`npm run build` в apps/web, exit 0:
```text

> fsp-reverse-hiring@1.0.0 build
> tsc -b && vite build

vite v6.4.4 building for production...
transforming...
✓ 55 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.44 kB │ gzip:  0.33 kB
dist/assets/index-x85TwcNR.css   19.36 kB │ gzip:  5.18 kB
dist/assets/index-B9FXyoib.js   261.54 kB │ gzip: 79.00 kB
✓ built in 2.34s

```
Python SHA256 считались для всех `fsp/**/*.py` через `docker compose exec -T api python -c ...`
и аналогично task-worker, сравнивались с `apps/api/fsp/**/*.py`.
Web: `docker compose exec -T web sh -c 'cd /usr/share/nginx/html && find . -type f -exec sha256sum {} \;'`,
сравнение с новой локальной dist. Полное равенство списков web=false из-за штатного nginx 50x.html;
все файлы приложения, включая index.html, совпали. Это не устаревшая сборка.
```json
{
  "api": {
    "match": true,
    "container": {
      "fsp/schemas.py": "f8cd2f8fe464e3d3407ef07f1bbc12508fb84b4ad873d78825bd31baac573912",
      "fsp/seed.py": "9db892cab8be235b22f636d016c8d96a6f16c74395da8c9cfa8c2681aa8c60fc",
      "fsp/formatting.py": "8be015724ca30d94c9082bf7dac31e858e3880fab559de9ddee7dc775c789501",
      "fsp/tasks.py": "258134a8ea6e3a126a2a365e790775db8fcf1e99df20f5ed3f7ebee186082b6e",
      "fsp/models.py": "5040873b582b60ac9729c5f1459555684a5e9ad6131ab54a8f391dac8d5491cd",
      "fsp/matching.py": "6f4b042f1d438eaefceae3c92717b3426c89913143c1d80dddaedf3b4b39ad43",
      "fsp/pdf.py": "b7b3148f019176c1ee9704eb3ccb49c809a36612ae0eed21482bef74ac69a68d",
      "fsp/assessment.py": "d5b30eab36bfdda4d978584be30b42fea6c0cea537dd55f1ee91da0a2e369b58",
      "fsp/outputs.py": "2ec9c8e367979ccbf195a4223fc98510028fdf0178c8337d4e4ef5eec07871a6",
      "fsp/task_worker.py": "9dc4d9b97a9fec495ff08af98efc25428f3e7f92baf395f392a28bac661ee85f",
      "fsp/bank.py": "d4bd2697d15a30f742be50d07faa1e4124fc2fec584337939105ebb90c5a5d16",
      "fsp/main.py": "6e9e297743689b3018e8ee8d540a12325baee117e050cb6c49647c817d1a335b",
      "fsp/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "fsp/fsp_provider.py": "5b119010cf47324fc619228204ad12763b8cb7cfefb8ad39336a204fe5b11b64"
    },
    "workspace": {
      "fsp/schemas.py": "f8cd2f8fe464e3d3407ef07f1bbc12508fb84b4ad873d78825bd31baac573912",
      "fsp/seed.py": "9db892cab8be235b22f636d016c8d96a6f16c74395da8c9cfa8c2681aa8c60fc",
      "fsp/formatting.py": "8be015724ca30d94c9082bf7dac31e858e3880fab559de9ddee7dc775c789501",
      "fsp/tasks.py": "258134a8ea6e3a126a2a365e790775db8fcf1e99df20f5ed3f7ebee186082b6e",
      "fsp/models.py": "5040873b582b60ac9729c5f1459555684a5e9ad6131ab54a8f391dac8d5491cd",
      "fsp/matching.py": "6f4b042f1d438eaefceae3c92717b3426c89913143c1d80dddaedf3b4b39ad43",
      "fsp/pdf.py": "b7b3148f019176c1ee9704eb3ccb49c809a36612ae0eed21482bef74ac69a68d",
      "fsp/assessment.py": "d5b30eab36bfdda4d978584be30b42fea6c0cea537dd55f1ee91da0a2e369b58",
      "fsp/outputs.py": "2ec9c8e367979ccbf195a4223fc98510028fdf0178c8337d4e4ef5eec07871a6",
      "fsp/task_worker.py": "9dc4d9b97a9fec495ff08af98efc25428f3e7f92baf395f392a28bac661ee85f",
      "fsp/bank.py": "d4bd2697d15a30f742be50d07faa1e4124fc2fec584337939105ebb90c5a5d16",
      "fsp/main.py": "6e9e297743689b3018e8ee8d540a12325baee117e050cb6c49647c817d1a335b",
      "fsp/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "fsp/fsp_provider.py": "5b119010cf47324fc619228204ad12763b8cb7cfefb8ad39336a204fe5b11b64"
    }
  },
  "task-worker": {
    "match": true,
    "container": {
      "fsp/schemas.py": "f8cd2f8fe464e3d3407ef07f1bbc12508fb84b4ad873d78825bd31baac573912",
      "fsp/seed.py": "9db892cab8be235b22f636d016c8d96a6f16c74395da8c9cfa8c2681aa8c60fc",
      "fsp/formatting.py": "8be015724ca30d94c9082bf7dac31e858e3880fab559de9ddee7dc775c789501",
      "fsp/tasks.py": "258134a8ea6e3a126a2a365e790775db8fcf1e99df20f5ed3f7ebee186082b6e",
      "fsp/models.py": "5040873b582b60ac9729c5f1459555684a5e9ad6131ab54a8f391dac8d5491cd",
      "fsp/matching.py": "6f4b042f1d438eaefceae3c92717b3426c89913143c1d80dddaedf3b4b39ad43",
      "fsp/pdf.py": "b7b3148f019176c1ee9704eb3ccb49c809a36612ae0eed21482bef74ac69a68d",
      "fsp/assessment.py": "d5b30eab36bfdda4d978584be30b42fea6c0cea537dd55f1ee91da0a2e369b58",
      "fsp/outputs.py": "2ec9c8e367979ccbf195a4223fc98510028fdf0178c8337d4e4ef5eec07871a6",
      "fsp/task_worker.py": "9dc4d9b97a9fec495ff08af98efc25428f3e7f92baf395f392a28bac661ee85f",
      "fsp/bank.py": "d4bd2697d15a30f742be50d07faa1e4124fc2fec584337939105ebb90c5a5d16",
      "fsp/main.py": "6e9e297743689b3018e8ee8d540a12325baee117e050cb6c49647c817d1a335b",
      "fsp/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "fsp/fsp_provider.py": "5b119010cf47324fc619228204ad12763b8cb7cfefb8ad39336a204fe5b11b64"
    },
    "workspace": {
      "fsp/schemas.py": "f8cd2f8fe464e3d3407ef07f1bbc12508fb84b4ad873d78825bd31baac573912",
      "fsp/seed.py": "9db892cab8be235b22f636d016c8d96a6f16c74395da8c9cfa8c2681aa8c60fc",
      "fsp/formatting.py": "8be015724ca30d94c9082bf7dac31e858e3880fab559de9ddee7dc775c789501",
      "fsp/tasks.py": "258134a8ea6e3a126a2a365e790775db8fcf1e99df20f5ed3f7ebee186082b6e",
      "fsp/models.py": "5040873b582b60ac9729c5f1459555684a5e9ad6131ab54a8f391dac8d5491cd",
      "fsp/matching.py": "6f4b042f1d438eaefceae3c92717b3426c89913143c1d80dddaedf3b4b39ad43",
      "fsp/pdf.py": "b7b3148f019176c1ee9704eb3ccb49c809a36612ae0eed21482bef74ac69a68d",
      "fsp/assessment.py": "d5b30eab36bfdda4d978584be30b42fea6c0cea537dd55f1ee91da0a2e369b58",
      "fsp/outputs.py": "2ec9c8e367979ccbf195a4223fc98510028fdf0178c8337d4e4ef5eec07871a6",
      "fsp/task_worker.py": "9dc4d9b97a9fec495ff08af98efc25428f3e7f92baf395f392a28bac661ee85f",
      "fsp/bank.py": "d4bd2697d15a30f742be50d07faa1e4124fc2fec584337939105ebb90c5a5d16",
      "fsp/main.py": "6e9e297743689b3018e8ee8d540a12325baee117e050cb6c49647c817d1a335b",
      "fsp/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "fsp/fsp_provider.py": "5b119010cf47324fc619228204ad12763b8cb7cfefb8ad39336a204fe5b11b64"
    }
  },
  "web": {
    "match": false,
    "container": {
      "50x.html": "876766b4e80133fd490603e073d3567425b88794828a9292104244c9e40875ed",
      "index.html": "41c62f8ec585615e69b2d1d56e94863e751e260450863551d8db4c4c48538394",
      "assets/index-x85TwcNR.css": "84e3e536817c07c4d727f5eb69d16b05a65f6d19b2886afb37730962853a8060",
      "assets/index-B9FXyoib.js": "5fa38d42be8c1a6a8139f3f4597448f3044de03aa3f3513e06342355f18e821a"
    },
    "workspace_dist": {
      "index.html": "41c62f8ec585615e69b2d1d56e94863e751e260450863551d8db4c4c48538394",
      "assets/index-x85TwcNR.css": "84e3e536817c07c4d727f5eb69d16b05a65f6d19b2886afb37730962853a8060",
      "assets/index-B9FXyoib.js": "5fa38d42be8c1a6a8139f3f4597448f3044de03aa3f3513e06342355f18e821a"
    },
    "rebuilt_workspace_dist": {
      "index.html": "41c62f8ec585615e69b2d1d56e94863e751e260450863551d8db4c4c48538394",
      "assets/index-x85TwcNR.css": "84e3e536817c07c4d727f5eb69d16b05a65f6d19b2886afb37730962853a8060",
      "assets/index-B9FXyoib.js": "5fa38d42be8c1a6a8139f3f4597448f3044de03aa3f3513e06342355f18e821a"
    },
    "application_files_match": true,
    "extra_container_files": [
      "50x.html"
    ]
  }
}
```
Хеши входов (включая неизменённую презентацию):
```json
{
  "scripts/smoke_stage_a.py": "ac4f7eb28f826856a962082db06573797b63b66ac4e7757afb3660e8eabdc3eb",
  "evaluation/stage_a_matching.py": "fdff5ee7ff84ffbdb712a317ff399df3771880334db56e943a47f0f36662e5b8",
  "evaluation/matching_fixtures.json": "0f4bb52e97a78d1326e6da2031303315dc6105461f59860fc3581402b3e50850",
  "apps/web/src/App.tsx": "d16b8e6e58739279e1be1fb69fccfc3acad92b1369d4951ae89e57ec8ef55bec",
  "docs/delivery/CHANGELOG_STAGE_A.md": "3685bf33002ecedcd06dd8999dca03c6d2ab8ab9f9b1f63db88c98cfebb28eba",
  "docs/delivery/FOR_JURY.md": "e16b8fa66caece077c32cd1edb8cbd6a0f63e6182a0141ddafe306b8e440698a",
  "demo/FSP_NIKITA_SUBMISSION.pptx": "41e86f5eb8cc809facb6240f87c81fdb83f8d000a67cb80a4735eaa164e930f8"
}
```
SHA контейнерной image label не заявляется: проверено побайтовое равенство прикладных файлов текущему
workspace, свежая web-сборка и версии в живом API. Remote GitHub отстаёт — отдельный Pck2.

## Упаковка и итоговые вердикты

Pck1 FAIL: в CHANGELOG_STAGE_A.md начало говорит о серверном запрете неполной сдачи,
а заключительный «Контроль сдачи» утверждает HTTP 200, Q3 FAIL, B05 снова воспроизводится.
История не обозначена как отменённая; эксперт не получает однозначного текущего статуса за 2 минуты.
Не переписано: это найденный дефект документа сдачи. Нужна явная историческая пометка и актуальный итог,
в том числе честный PARTIAL Q4. SUBMISSION_LINKS «Закрыты Q1–Q7» также нельзя копировать без уточнения.
Pck2 содержит нужные поля и рабочие логины, но ссылки GitHub пока не ведут на обновления этапа A.
NOTTODO: diff demo/presentation пуст, matching/evaluation diff — перебор весов и банк, не IRT pipeline;
SMTP/ФСП честно ограничены. Внешние действия, SMTP, новый нагрузочный тест, пилот и календарная неделя — NOT_RUN.

| ID | Вердикт | Остаток |
|---|---|---|
| Q1 | PASS | Человеческая проверка по связанному протоколу; автоматический DoD проверен. |
| Q2 | PASS | Человеческая проверка по связанному протоколу; автоматический DoD проверен. |
| Q3 | PASS | Человеческая проверка по связанному протоколу; автоматический DoD проверен. |
| Q4 | PARTIAL | Статичная надпись «навыки подтверждены» показана и при verified=false: полная согласованность всех текстов не достигнута. Прежние два сценария B05 исправлены.; Требуется человеческая оценка этой надписи; PARTIAL пока не отражён в актуальном changelog. |
| Q5 | PASS | Человеческая проверка по связанному протоколу; автоматический DoD проверен. |
| Q6 | PASS | Человеческая проверка по связанному протоколу; автоматический DoD проверен. |
| Q7 | PASS | Человеческая проверка по связанному протоколу; автоматический DoD проверен. |
| Pck1 | FAIL | Упаковка противоречит свежим проверкам и собственному описанию исправлений. Старый STOP выглядит действующим.; Нужно явно отделить историю от текущего результата и указать оставшийся PARTIAL Q4; в этой сессии файл changelog не менялся. |
| Pck2 | PARTIAL | Изменения этапа A и актуальные документы не опубликованы в ветке GitHub.; Человеческий маршрут общих аккаунтов может упереться в cooldown; это не разрешение сбрасывать попытки или БД. |
| Pck3 | PASS | Человеческая проверка по связанному протоколу; автоматический DoD проверен. |
| Pck4 | PASS | Человеческая проверка по связанному протоколу; автоматический DoD проверен. |
| Pck5 | HUMAN_ONLY | Нужны исправление упаковки, push, human PASS и подтверждение отправки. |
| REG_FSP | PASS | Человеческая проверка по связанному протоколу; автоматический DoD проверен. |
| REG_ISO | PASS | Человеческая проверка по связанному протоколу; автоматический DoD проверен. |
| REG_OLD_SEL | PASS | Человеческая проверка по связанному протоколу; автоматический DoD проверен. |
| NOTTODO | PASS | Человеческая проверка по связанному протоколу; автоматический DoD проверен. |

Для отправки: исправить противоречивую упаковку; решить/честно описать PARTIAL Q4; повторно проверить изменённое; опубликовать ветку; заполнить человеческий протокол без FAIL по ★. Pck5 закрывает только человек.

## Завершение verify-сессии

После создания verify-коммита выполнен настоящий `GIT_TERMINAL_PROMPT=0 git push origin codex/fsp-mvp`.
Exit 128:
```text
fatal: could not read Username for 'https://github.com': terminal prompts disabled
```
Push не выполнен. Эта запись добавлена в тот же локальный verify-коммит через amend;
продуктовый код не менялся. Перед отправкой человек должен обеспечить публикацию из авторизованного окружения.
Проверка структуры: 16 уникальных ID, все обязательные поля и evidence заполнены,
все human_checks_required имеют полные шаги; 22 человеческих шага. `git diff --cached --check` — без ошибок.

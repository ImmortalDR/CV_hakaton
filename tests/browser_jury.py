"""Two successive jury checks on the SAME demo accounts, through two browser sessions.

Keeps previous records. Adds labelled synthetic invitations/tasks; no email is sent.
"""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import pymupdf
from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--runs', type=int, default=2)
    parser.add_argument('--out', type=Path, default=Path('audit/current/jury-replay'))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    checks, errors, completed = [], [], []
    tag = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        def context(state=None):
            ctx = browser.new_context(base_url=args.base_url, storage_state=state,
                viewport={'width':1365,'height':1000}, locale='ru-RU')
            ctx.on('page', lambda p: p.on('pageerror', lambda e: errors.append(str(e))))
            return ctx
        def get(ctx, path):
            response = ctx.request.get('/api' + path)
            assert response.ok, (path, response.status)
            return response.json()
        def nav(page, label):
            page.locator('nav').get_by_role('button', name=re.compile('^'+re.escape(label))).click()
        def click(scope, label):
            scope.get_by_role('button', name=label, exact=True).click()
        def pause(page):
            # Close the tab, lose React state/sessionStorage, retain only browser login.
            ctx, url = page.context, page.url
            page.close()
            page = ctx.new_page(); page.goto(url)
            expect(page.locator('nav')).to_be_visible()
            return page
        def pdf_text(page, card):
            with page.expect_download() as download:
                card.get_by_role('link', name='Скачать PDF профиля', exact=True).click()
            with pymupdf.open(download.value.path()) as pdf:
                return '\n'.join(p.get_text() for p in pdf)
        def checked(message):
            checks.append(message); print('PASS '+message, flush=True)
        c, e = context(), context()
        cp, ep = c.new_page(), e.new_page()
        try:
            cp.goto('/login'); click(cp, 'Я кандидат')
            ep.goto('/login'); click(ep, 'Я работодатель')
            expect(cp.locator('.workspace-label')).to_have_text('КАБИНЕТ КАНДИДАТА')
            expect(ep.locator('.workspace-label')).to_have_text('КАБИНЕТ РАБОТОДАТЕЛЯ')
            candidate, employer = get(c, '/auth/me'), get(e, '/auth/me')
            own = get(c, '/me/profile'); cid, code = own['id'], own['candidate_code']
            original_history = get(c, '/me/attempts')
            original_ids = {a['id'] for a in original_history}
            assert original_ids
            finished = next(a for a in original_history if a.get('result') and a['result']['score'] == 100)
            grade = own['verified_grade']
            # An earlier visitor may have hidden the shared profile. Restore visibility
            # through the same explicit settings the guide describes; no data reset.
            nav(cp, 'Мой профиль')
            cp.get_by_label('Согласен на обработку данных для работы профиля').check()
            cp.get_by_label('Публиковать профиль в банке кандидатов').check()
            click(cp, 'Сохранить профиль')
            expect(cp.get_by_text('Профиль сохранён', exact=True)).to_be_visible()
            prior_invites = {i['id'] for i in get(e, '/invitations')}
            prior_tasks = {p['id'] for p in get(e, '/tasks')['plans']}
            for iteration in range(args.runs):
                mark = f'Проверка жюри {tag} — {iteration+1}'
                if iteration:
                    cs, es = c.storage_state(), e.storage_state()
                    c.close(); e.close()
                    c, e = context(cs), context(es)
                    cp, ep = c.new_page(), e.new_page()
                    cp.goto('/assessment'); ep.goto('/search')
                    expect(cp.locator('nav')).to_be_visible(); expect(ep.locator('nav')).to_be_visible()
                assert get(c, '/auth/me')['id'] == candidate['id']
                assert get(e, '/auth/me')['id'] == employer['id']
                assert prior_invites <= {i['id'] for i in get(e, '/invitations')}
                assert prior_tasks <= {p['id'] for p in get(e, '/tasks')['plans']}
                cp.goto('/assessment?attempt='+finished['id'])
                expect(cp.locator('.result')).to_contain_text('100%')
                expect(cp.locator('.question')).to_have_count(len(finished['questions']))
                cp = pause(cp); expect(cp.locator('.result')).to_contain_text('100%')
                expect(cp.locator('.history-list > div')).to_have_count(len(original_history))
                checked(f'{iteration+1}: retained login, original history and result after closing the tab')

                nav(ep, 'Подбор кандидатов'); click(ep, 'По потребности')
                ep.get_by_label('Специализация', exact=True).select_option('python')
                for g in ['Junior','Middle','Senior']: ep.get_by_label(g, exact=True).set_checked(g == grade)
                ep.get_by_label('Python', exact=True).select_option('required')
                ep.get_by_label('Тестирование', exact=True).select_option('desired')
                ep.get_by_label('HTTP / API', exact=True).select_option('none')
                ep.get_by_label('Только с достижениями ФСП (демо)').uncheck()
                click(ep, 'Сформировать подборку')
                card = ep.locator('.candidate-card').filter(has_text=code)
                expect(card).to_contain_text('Почему в подборке')
                card.get_by_text('Результаты и источники', exact=True).click()
                expect(card).to_contain_text('Python · 4/4')
                ep.get_by_label('HTTP / API', exact=True).select_option('required')
                click(ep, 'Сформировать подборку')
                expect(card).to_contain_text('Неполное соответствие обязательным навыкам')
                expect(card).to_contain_text('Не проверено')
                ep.get_by_label('HTTP / API', exact=True).select_option('none')
                click(ep, 'Сформировать подборку')
                click(ep, 'Банк кандидатов'); click(ep, 'Сбросить фильтры')
                ep.get_by_label('Номер кандидата', exact=True).fill(code); click(ep, 'Применить фильтры')
                expect(ep.locator('.candidate-card')).to_have_count(1)
                visible = get(e, '/candidates/'+cid)
                pdf = pdf_text(ep, card)
                assert code in pdf or own['display_name'] in pdf
                assert (own['contacts']['email'] in pdf) == bool(visible['contacts'])
                checked(f'{iteration+1}: matching, missing HTTP proof, exact identifier search and PDF follows current consent')

                def send_offer(description, retry_company=False):
                    card = ep.locator('.candidate-card').filter(has_text=code)
                    if retry_company:
                        ep.route('**/api/me/company', lambda r: r.fulfill(status=503,
                            content_type='application/json', body='{"detail":"Временная ошибка"}'))
                    click(card, 'Пригласить')
                    ep.get_by_label('Предложение и задачи', exact=True).fill(description)
                    ep.get_by_label('Зарплата от, ₽ / месяц', exact=True).fill('100000')
                    ep.get_by_label('Зарплата до, ₽ / месяц', exact=True).fill('150000')
                    if retry_company:
                        expect(ep.get_by_text('Не удалось загрузить компанию.', exact=False)).to_be_visible()
                        expect(ep.get_by_role('button', name='Отправить приглашение', exact=True)).to_be_disabled()
                        ep.unroute('**/api/me/company'); click(ep, 'Загрузить компанию повторно')
                        expect(ep.locator('.invitation-preview')).to_contain_text('Вымышленная компания')
                        expect(ep.get_by_label('Предложение и задачи', exact=True)).to_have_value(description)
                        expect(ep.get_by_label('Зарплата до, ₽ / месяц', exact=True)).to_have_value('150000')
                    click(ep, 'Отправить приглашение')
                    expect(ep.get_by_role('heading', name='Приглашение отправлено', exact=True)).to_be_visible()
                    click(ep, 'Готово')
                send_offer(mark, True)
                assert len([i for i in get(e, '/invitations') if i['description']==mark]) == 1
                ep = pause(ep)
                nav(cp, 'Приглашения'); cp = pause(cp)
                ci = cp.locator('.invitation').filter(has_text=mark)
                expect(ci).to_contain_text('100 000 — 150 000')
                # Keep employer tasks open before acceptance, then refresh recipients.
                nav(ep, 'Задания от компаний')
                click(ci, 'Принять и раскрыть контакты'); expect(ci.locator('.badge')).to_have_text('Принято')
                cp = pause(cp)
                click(ep, 'Обновить задания')
                expect(ep.get_by_label('Получатель задания').locator('option[value="'+cid+'"]')).to_have_count(1)
                checked(f'{iteration+1}: company retry preserves draft; sent invite survives interruption; task recipients refresh after acceptance')

                nav(ep, 'Приглашения')
                ei = ep.locator('.invitation').filter(has_text=mark)
                expect(ei).to_contain_text(own['contacts']['email'])
                click(ei, 'Открыть диалог'); ei.get_by_label('Сообщение', exact=True).fill('Здравствуйте! Обсудим задачи завтра?')
                click(ei, 'Отправить'); expect(ei.get_by_text('Здравствуйте! Обсудим задачи завтра?', exact=True)).to_be_visible()
                ep = pause(ep)
                ei = ep.locator('.invitation').filter(has_text=mark)
                expect(ei.get_by_text('Здравствуйте! Обсудим задачи завтра?', exact=True)).to_be_visible()
                ci = cp.locator('.invitation').filter(has_text=mark); click(ci, 'Открыть диалог')
                expect(ci.get_by_text('Здравствуйте! Обсудим задачи завтра?', exact=True)).to_be_visible()
                ci.get_by_label('Сообщение', exact=True).fill('Да, завтра в 12:00 удобно.'); click(ci, 'Отправить')
                click(ei, 'Обновить'); expect(ei.get_by_text('Да, завтра в 12:00 удобно.', exact=True)).to_be_visible()
                ep.goto('/search?candidate_code='+code)
                card = ep.locator('.candidate-card').filter(has_text=code)
                expect(card).to_be_visible(); assert own['contacts']['email'] in pdf_text(ep, card)
                checked(f'{iteration+1}: consent, disclosed PDF, two-way chat and retained messages after interruption')

                title = 'Ошибки API — '+mark
                nav(ep, 'Задания от компаний'); ep.get_by_label('Получатель задания').select_option(cid)
                ep.get_by_label('Название задания', exact=True).fill(title)
                ep.get_by_label('Задача и ожидаемый ответ').fill('Как повторять запрос при временной ошибке API и предотвращать дублирование операции?')
                ep.get_by_label('Критерии оценки', exact=True).fill('Ограничение повторов, задержка между ними, защита от дублей.')
                click(ep, 'Предложить план кандидату')
                expect(ep.locator('.task-plan').filter(has_text=title)).to_contain_text('Ожидает согласия')
                nav(cp, 'Задания от компаний'); plan = cp.locator('.task-plan').filter(has_text=title)
                click(plan, 'Согласиться и включить выдачу')
                cp = pause(cp); plan = cp.locator('.task-plan').filter(has_text=title)
                plan.get_by_label('Ответ на задание').fill('Ограничиваю число повторов, увеличиваю задержку, использую ключ идемпотентности.')
                click(plan, 'Отправить ответ'); expect(plan).to_contain_text('На проверке')
                cp = pause(cp); expect(cp.locator('.task-plan').filter(has_text=title)).to_contain_text('На проверке')
                click(ep, 'Обновить задания'); plan_e = ep.locator('.task-plan').filter(has_text=title)
                plan_e.get_by_label('Оценка от 0 до 100').fill('85')
                plan_e.get_by_label('Обоснование оценки').fill('Учтены ограничение повторов, задержка и защита от дублирования.')
                click(plan_e, 'Сохранить оценку'); expect(plan_e).to_contain_text('85/100')
                click(cp, 'Обновить задания'); plan = cp.locator('.task-plan').filter(has_text=title)
                expect(plan).to_contain_text('85/100'); click(plan, 'Приостановить выдачу')
                cp = pause(cp); plan = cp.locator('.task-plan').filter(has_text=title)
                expect(plan).to_contain_text('Выдача приостановлена'); click(plan, 'Согласиться и включить выдачу')
                expect(plan).to_contain_text('Выдача включена')
                task = next(p for p in get(c, '/tasks')['plans'] if p['title']==title)
                assert len(task['assignments'])==1
                click(plan, 'Закрыть план'); expect(plan).to_contain_text('План закрыт')
                assert get(c, '/me/profile')['verified_grade']==grade
                checked(f'{iteration+1}: task consent, saved answer, review, pause/resume across tab closure; no duplicate assignment')

                nav(cp, 'Достижения ФСП')
                connect = cp.get_by_role('button', name='Связать демонстрационный ФСП ID', exact=True)
                if connect.count(): connect.click()
                expect(cp.get_by_role('heading', name='Демонстрационный профиль связан', exact=True)).to_be_visible()
                assert get(c, '/me/profile')['verified_grade']==grade
                checked(f'{iteration+1}: existing or newly linked FSP achievements preserve grade')

                nav(cp, 'Мой профиль'); cp.get_by_label('Публиковать профиль в банке кандидатов').uncheck()
                click(cp, 'Сохранить профиль'); expect(cp.get_by_text('Профиль сохранён', exact=True)).to_be_visible()
                cp = pause(cp); expect(cp.get_by_label('Публиковать профиль в банке кандидатов')).not_to_be_checked()
                ep.goto('/search?candidate_code='+code)
                expect(ep.get_by_text('Подходящих профилей пока нет', exact=True)).to_be_visible()
                assert e.request.get('/api/profiles/'+cid+'/pdf').status==404
                nav(ep, 'Приглашения'); ei = ep.locator('.invitation').filter(has_text=mark)
                expect(ei).to_contain_text('согласие на доступ к профилю отозвано')
                expect(ei.get_by_role('button', name='Открыть диалог', exact=True)).to_have_count(0)
                cp.get_by_label('Публиковать профиль в банке кандидатов').check(); click(cp, 'Сохранить профиль')
                expect(cp.get_by_text('Профиль сохранён', exact=True)).to_be_visible()
                assert get(e, '/candidates/'+cid)['contacts'] is None
                ep.goto('/search?candidate_code='+code); card = ep.locator('.candidate-card').filter(has_text=code)
                expect(card).to_be_visible(); assert own['contacts']['email'] not in pdf_text(ep, card)
                renewed = mark+' — новое согласие'; send_offer(renewed)
                nav(cp, 'Приглашения'); ci = cp.locator('.invitation').filter(has_text=renewed)
                click(ci, 'Принять и раскрыть контакты'); expect(ci.locator('.badge')).to_have_text('Принято')
                nav(ep, 'Приглашения'); expect(ep.locator('.invitation').filter(has_text=renewed)).to_contain_text(own['contacts']['email'])
                checked(f'{iteration+1}: hide, interrupt, resume, republish, new invitation restores consent explicitly')
                assert {a['id'] for a in get(c, '/me/attempts')} == original_ids
                assert get(c, '/me/profile')['published']
                prior_invites = {i['id'] for i in get(e, '/invitations')}
                prior_tasks = {p['id'] for p in get(e, '/tasks')['plans']}
                nav(cp, 'Подтверждение навыков'); cp.set_viewport_size({'width':390,'height':844})
                expect(cp.locator('.history-list > div')).to_have_count(len(original_history))
                assert cp.evaluate('document.documentElement.scrollWidth <= innerWidth')
                cp.screenshot(path=str(args.out/f'run-{iteration+1}-history-mobile.png'), full_page=True)
                ep.screenshot(path=str(args.out/f'run-{iteration+1}-invitations.png'), full_page=True)
                completed.append({'candidate_id':cid,'code':code,'employer_id':employer['id'],
                    'history_ids':sorted(original_ids),'invitations':len(prior_invites),'task_plans':len(prior_tasks)})
                print(f'PASS complete repeated scenario {iteration+1}', flush=True)
            assert not errors, errors
        except Exception:
            for label, page in [('candidate',cp),('employer',ep)]:
                if not page.is_closed():
                    page.screenshot(path=str(args.out/f'failure-{label}.png'), full_page=True)
                    (args.out/f'failure-{label}.txt').write_text(page.locator('body').inner_text())
            raise
        finally:
            (args.out/'result.json').write_text(json.dumps({'complete_runs':len(completed),
                'same_accounts':True,'separate_sessions':True,'runs':completed,'checks':checks,'page_errors':errors,
                'scope':'Common demo accounts; existing history preserved; synthetic records added through UI; no reset or email'},ensure_ascii=False,indent=2)+'\n')
            browser.close()

if __name__=='__main__': main()

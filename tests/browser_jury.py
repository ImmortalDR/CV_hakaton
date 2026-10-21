"""Repeat the published jury walkthrough through real UI, only in new demo runs.

Usage: .venv/bin/python tests/browser_jury.py --base-url https://... --runs 2
No existing users or shared demo business data are changed. No email is sent.
"""
import argparse
import json
from pathlib import Path

import pymupdf
from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--runs', type=int, default=2)
    parser.add_argument('--out', type=Path, default=Path('audit/current/jury'))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    checks, errors, starts, completed = [], [], [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        def context():
            ctx = browser.new_context(base_url=args.base_url, viewport={'width':1365, 'height':1000}, locale='ru-RU')
            ctx.on('page', lambda p: p.on('pageerror', lambda e: errors.append(str(e))))
            return ctx
        def get(ctx, path):
            response = ctx.request.get('/api' + path)
            assert response.ok, (path, response.status)
            return response.json()
        def nav(page, label):
            page.locator('nav').get_by_role('button', name=label, exact=True).click()
        def button(page, label):
            page.get_by_role('button', name=label, exact=True).click()
        def pdf_text(ctx, cid):
            response = ctx.request.get('/api/profiles/' + cid + '/pdf')
            assert response.ok
            with pymupdf.open(stream=response.body(), filetype='pdf') as pdf:
                return '\n'.join(p.get_text() for p in pdf)
        try:
            for iteration in range(args.runs):
                c, e = context(), context()
                cp, ep = c.new_page(), e.new_page()
                cp.goto('/login')
                button(cp, 'Начать новый демопроход')
                link = cp.get_by_label('Ссылка на этот демопроход', exact=True).input_value()
                assert '#demo=' in link
                button(cp, 'Я кандидат')
                expect(cp.locator('.feature-banner')).to_contain_text('Junior')
                own = get(c, '/me/profile')
                cid, code = own['id'], own['candidate_code']
                expect(cp.locator('.demo-run-info')).to_contain_text(code)
                ep.goto(link)
                button(ep, 'Я работодатель')
                expect(ep.locator('nav')).to_be_visible()
                assert get(e, '/auth/me')['demo_run_id'] == get(c, '/auth/me')['demo_run_id']
                assert '#demo=' not in ep.url
                history = get(c, '/me/attempts')
                baseline = {'grade':own['verified_grade'], 'published':own['published'],
                    'history_scores':[a['result']['score'] for a in history],
                    'question_counts':[len(a['questions']) for a in history],
                    'invites':len(get(e, '/invitations')), 'searches':len(get(e, '/searches')),
                    'tasks':len(get(e, '/tasks')['plans']), 'achievements':len(own['achievements']),
                    'contacts':get(e, '/candidates/' + cid)['contacts']}
                assert baseline == {'grade':'Junior','published':True,'history_scores':[50,100],
                    'question_counts':[8,8], 'invites':0,'searches':0,'tasks':0,'achievements':0,'contacts':None}
                starts.append(baseline)

                nav(cp, 'Подтверждение навыков')
                rows = cp.locator('.history-list > div')
                expect(rows).to_have_count(2)
                rows.filter(has_text='100%').get_by_role('button', name='Посмотреть').click()
                expect(cp.locator('.result')).to_contain_text('100%')
                expect(cp.locator('.question')).to_have_count(8)
                expect(cp.locator('.question .correct')).to_have_count(8)
                cp.reload(); expect(cp.locator('.result')).to_contain_text('100%')
                rows.filter(has_text='50%').get_by_role('button', name='Посмотреть').click()
                expect(cp.locator('.result')).to_contain_text('Прежний подтверждённый уровень')
                nav(cp, 'Обзор'); expect(cp.locator('.feature-banner')).to_contain_text('Junior')
                checks.append(f'{iteration+1}: history, answers, explanations, failed attempt preserves Junior')

                # A failed history request must not claim that no attempts exist.
                c.route('**/api/me/attempts', lambda route: route.abort())
                cp.goto('/assessment')
                expect(cp.get_by_text('Не удалось загрузить историю.', exact=False)).to_be_visible()
                expect(cp.get_by_text('Первый результат ещё впереди')).not_to_be_visible()
                c.unroute('**/api/me/attempts')
                button(cp, 'Обновить историю'); expect(cp.locator('.history-list > div')).to_have_count(2)
                c.route('**/api/me/assessment-availability', lambda route: route.abort())
                cp.reload(); expect(cp.locator('.history-list > div')).to_have_count(2)
                c.unroute('**/api/me/assessment-availability')
                button(cp, 'Обновить историю')
                checks.append(f'{iteration+1}: history survives availability failure and recovers after network failure')

                nav(ep, 'Подбор кандидатов'); button(ep, 'По потребности')
                ep.get_by_label('Специализация', exact=True).select_option('python')
                for grade in ['Junior','Middle','Senior']:
                    ep.get_by_label(grade, exact=True).set_checked(grade == 'Junior')
                ep.get_by_label('Python', exact=True).select_option('required')
                ep.get_by_label('Тестирование', exact=True).select_option('desired')
                ep.get_by_label('HTTP / API', exact=True).select_option('none')
                button(ep, 'Сформировать подборку')
                card = ep.locator('.candidate-card').filter(has_text=code)
                expect(card).to_contain_text('Почему в подборке')
                expect(card).to_contain_text('Балл 90.00')
                card.get_by_text('Результаты и источники', exact=True).click()
                expect(card).to_contain_text('Python · 4/4')
                ep.get_by_label('HTTP / API', exact=True).select_option('required')
                button(ep, 'Сформировать подборку')
                expect(card).to_contain_text('Неполное соответствие обязательным навыкам')
                expect(card).to_contain_text('Не проверено')
                expect(card).to_contain_text('Балл 75.00')
                ep.get_by_label('HTTP / API', exact=True).select_option('none')
                button(ep, 'Сформировать подборку'); expect(card).to_contain_text('Балл 90.00')
                button(ep, 'Банк кандидатов'); button(ep, 'Сбросить фильтры')
                ep.get_by_label('Номер кандидата', exact=True).fill(code)
                button(ep, 'Применить фильтры'); expect(ep.locator('.candidate-card')).to_have_count(1)
                expect(card.locator('h3')).to_contain_text(code)
                hidden = pdf_text(e, cid)
                assert code in hidden and own['contacts']['email'] not in hidden
                checks.append(f'{iteration+1}: matching, missing HTTP proof, exact code search, anonymous PDF')

                def send_offer():
                    button(card, 'Пригласить')
                    ep.get_by_label('Предложение и задачи', exact=True).fill('Разработка API на Python')
                    ep.get_by_label('Зарплата от, ₽ / месяц', exact=True).fill('100000')
                    ep.get_by_label('Зарплата до, ₽ / месяц', exact=True).fill('150000')
                    button(ep, 'Отправить приглашение')
                    expect(ep.get_by_role('heading', name='Приглашение отправлено', exact=True)).to_be_visible()
                    button(ep, 'Готово')
                    expect(ep.get_by_role('dialog')).not_to_be_visible()
                send_offer()
                nav(cp, 'Приглашения')
                expect(cp.locator('.salary')).to_contain_text('100 000 — 150 000')
                button(cp, 'Принять и раскрыть контакты')
                expect(cp.locator('.invitation .badge')).to_have_text('Принято')
                nav(ep, 'Приглашения')
                expect(ep.locator('.invitation')).to_contain_text(own['contacts']['email'])
                opened = pdf_text(e, cid)
                assert own['display_name'] in opened and own['contacts']['email'] in opened
                for page in (cp, ep): button(page, 'Открыть диалог')
                ep.get_by_label('Сообщение', exact=True).fill('Здравствуйте! Обсудим задачи завтра?')
                button(ep, 'Отправить'); expect(ep.get_by_text('Здравствуйте! Обсудим задачи завтра?', exact=True)).to_be_visible()
                button(cp, 'Обновить'); expect(cp.get_by_text('Здравствуйте! Обсудим задачи завтра?', exact=True)).to_be_visible()
                cp.get_by_label('Сообщение', exact=True).fill('Да, завтра в 12:00 удобно.')
                button(cp, 'Отправить'); expect(cp.get_by_text('Да, завтра в 12:00 удобно.', exact=True)).to_be_visible()
                button(ep, 'Обновить'); expect(ep.get_by_text('Да, завтра в 12:00 удобно.', exact=True)).to_be_visible()
                checks.append(f'{iteration+1}: invitation, scoped consent, disclosed PDF, two-way chat')

                nav(ep, 'Задания от компаний')
                ep.get_by_label('Получатель задания').select_option(cid)
                ep.get_by_label('Название задания', exact=True).fill('Проверка обработки ошибок API')
                ep.get_by_label('Задача и ожидаемый ответ').fill('Как повторять запрос при временной ошибке API и предотвращать дублирование операции?')
                ep.get_by_label('Критерии оценки', exact=True).fill('Ограничение повторов, задержка между ними, защита от дублей.')
                button(ep, 'Предложить план кандидату'); expect(ep.locator('.task-plan')).to_contain_text('Ожидает согласия')
                nav(cp, 'Задания от компаний'); button(cp, 'Согласиться и включить выдачу')
                cp.get_by_label('Ответ на задание').fill('Ограничиваю число повторов, увеличиваю задержку, использую ключ идемпотентности.')
                button(cp, 'Отправить ответ'); expect(cp.locator('.task-assignment')).to_contain_text('На проверке')
                button(ep, 'Обновить задания')
                ep.get_by_label('Оценка от 0 до 100').fill('85')
                ep.get_by_label('Обоснование оценки').fill('Учтены ограничение повторов, задержка и защита от дублирования.')
                button(ep, 'Сохранить оценку'); expect(ep.locator('.task-assignment')).to_contain_text('85/100')
                button(cp, 'Обновить задания'); expect(cp.locator('.task-assignment')).to_contain_text('85/100')
                assert get(c, '/me/profile')['verified_grade'] == 'Junior'
                button(cp, 'Приостановить выдачу'); expect(cp.locator('.task-plan')).to_contain_text('Выдача приостановлена')
                button(cp, 'Согласиться и включить выдачу'); expect(cp.locator('.task-plan')).to_contain_text('Выдача включена')
                assert len(get(c, '/tasks')['plans'][0]['assignments']) == 1
                checks.append(f'{iteration+1}: task consent, answer, 85/100 review, pause/resume, unchanged grade')

                nav(cp, 'Достижения ФСП'); button(cp, 'Связать демонстрационный ФСП ID')
                expect(cp.get_by_role('heading', name='Демонстрационный профиль связан', exact=True)).to_be_visible()
                assert get(c, '/me/profile')['verified_grade'] == 'Junior'
                nav(ep, 'Подбор кандидатов'); button(ep, 'По потребности'); button(ep, 'Сформировать подборку')
                expect(card).to_contain_text('Балл 96.00')
                checks.append(f'{iteration+1}: FSP adds 6 ranking points and does not change grade')

                nav(cp, 'Мой профиль')
                cp.get_by_label('Публиковать профиль в банке кандидатов').uncheck()
                button(cp, 'Сохранить профиль'); expect(cp.get_by_text('Профиль сохранён', exact=True)).to_be_visible()
                ep.reload(); expect(ep.locator('.candidate-card').filter(has_text=code)).to_have_count(0)
                assert e.request.get('/api/profiles/' + cid + '/pdf').status == 404
                nav(ep, 'Приглашения'); expect(ep.locator('.invitation')).to_contain_text('согласие на доступ к профилю отозвано')
                expect(ep.get_by_role('button', name='Открыть диалог', exact=True)).to_have_count(0)
                cp.get_by_label('Публиковать профиль в банке кандидатов').check()
                button(cp, 'Сохранить профиль'); expect(cp.get_by_text('Профиль сохранён', exact=True)).to_be_visible()
                ep.reload(); expect(ep.locator('.invitation')).to_contain_text('согласие на доступ к профилю отозвано')
                assert get(e, '/candidates/' + cid)['contacts'] is None
                nav(ep, 'Подбор кандидатов'); button(ep, 'Банк кандидатов')
                ep.get_by_label('Номер кандидата', exact=True).fill(code); button(ep, 'Применить фильтры')
                expect(card).to_be_visible(); send_offer()
                nav(cp, 'Приглашения'); button(cp, 'Принять и раскрыть контакты')
                expect(cp.locator('.invitation .badge')).to_have_text(['Принято', 'Принято'])
                nav(ep, 'Приглашения'); expect(ep.locator('.invitation').first).to_contain_text(own['contacts']['email'])
                checks.append(f'{iteration+1}: hide removes search/PDF/chat; republish requires new invitation and consent')

                cp.set_viewport_size({'width':390, 'height':844})
                cp.locator('.mobile-menu').click(); nav(cp, 'Подтверждение навыков')
                expect(cp.locator('.history-list > div')).to_have_count(2)
                assert cp.evaluate('document.documentElement.scrollWidth <= innerWidth')
                cp.screenshot(path=str(args.out / f'run-{iteration+1}-history-mobile.png'), full_page=True)
                ep.screenshot(path=str(args.out / f'run-{iteration+1}-consented.png'), full_page=True)
                # Also check the first run remains intact after starting the next one.
                if completed:
                    previous = completed[-1]
                    assert e.request.get('/api/candidates/' + previous['candidate_id']).status == 404
                completed.append({'candidate_id':cid, 'code':code, 'checks':8})
                for page in (cp, ep): button(page, 'Выйти')
                c.close(); e.close()
                print(f'PASS full jury run {iteration+1}', flush=True)
            assert all(s == starts[0] for s in starts)
            assert not errors, errors
        except Exception:
            for label, page in [('candidate', cp), ('employer', ep)]:
                page.screenshot(path=str(args.out / f'failure-{label}.png'), full_page=True)
                (args.out / f'failure-{label}.txt').write_text(page.locator('body').inner_text())
            raise
        finally:
            browser.close()
            (args.out / 'result.json').write_text(json.dumps({'complete_runs':len(completed),
                'checks':checks, 'identical_initial_states':len(starts)>1 and all(s==starts[0] for s in starts),
                'initial_states':starts, 'page_errors':errors, 'scope':'New isolated synthetic demo runs only; business actions via UI; read-only API/PDF assertions; no external email'}, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    main()

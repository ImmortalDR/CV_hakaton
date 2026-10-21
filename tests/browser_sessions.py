"""Saved-cookie entry, cross-tab identity, history retry and stalled requests.

Only a new synthetic demo run is used. No email or existing business data changes.
Run against an isolated fixture or the public demo with --base-url.
"""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--out', type=Path, default=Path('audit/current/sessions'))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    checks, errors = [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        def context(**kwargs):
            ctx = browser.new_context(base_url=args.base_url, locale='ru-RU', **kwargs)
            ctx.on('page', lambda page: page.on('pageerror', lambda error: errors.append(str(error))))
            return ctx
        def click(page, label):
            page.get_by_role('button', name=label, exact=True).click()
        def nav(page, label):
            page.locator('nav').get_by_role('button', name=label, exact=True).click()
        def checked(message):
            checks.append(message)
            print('PASS ' + message, flush=True)
        def retry(page):
            with page.expect_response(lambda r: r.url.endswith('/api/me/attempts') and r.status == 200):
                click(page, 'Обновить историю')
            expect(page.locator('.history-list > div')).to_have_count(2)
        ctx = context()
        page = ctx.new_page()
        try:
            page.goto('/login'); click(page, 'Начать новый демопроход')
            link = page.get_by_label('Ссылка на этот демопроход', exact=True).input_value()
            click(page, 'Я кандидат'); expect(page.locator('.feature-banner')).to_contain_text('Junior')
            candidate = ctx.request.get('/api/auth/me').json()
            state = ctx.storage_state()
            nav(page, 'Подтверждение навыков')
            expect(page.locator('.history-list > div')).to_have_count(2)
            attempt = ctx.request.get('/api/me/attempts').json()[0]['id']

            for path in ['/', '/assessment', '/assessment?attempt=' + attempt]:
                saved = context(storage_state=state)
                restored = saved.new_page()
                logins = []
                restored.on('request', lambda r: logins.append(r.url) if r.method == 'POST' and '/auth/' in r.url else None)
                restored.goto(path)
                expect(restored.locator('.account')).to_contain_text(candidate['email'])
                if path == '/': nav(restored, 'Подтверждение навыков')
                expect(restored.locator('.history-list > div')).to_have_count(2)
                if '?attempt=' in path: expect(restored.locator('.result')).to_contain_text('50%')
                retry(restored)
                restored.reload(); expect(restored.locator('.history-list > div')).to_have_count(2)
                assert not logins, logins
                saved.close()
            checked('saved cookie in fresh browser contexts: home, history, result deep link, reload and real retry')

            pending = []
            page.route('**/api/me/assessment-availability', lambda route: pending.append(route))
            page.reload(); expect(page.locator('.history-list > div')).to_have_count(2)
            expect(page.locator('.assessment-access')).to_contain_text('Проверяем доступность теста')
            assert pending
            retry(page)
            page.unroute('**/api/me/assessment-availability')
            for route in pending: route.abort()
            retry(page)
            expect(page.locator('.assessment-access')).to_contain_text('Тест Junior')
            checked('history renders and refreshes while availability request is stalled')

            stalled = []
            def stall_first(route):
                if not stalled: stalled.append(route)
                else: route.continue_()
            page.route('**/api/me/attempts', stall_first)
            page.reload()
            expect(page.locator('.assessment-access')).to_contain_text('Тест Junior')
            assert stalled
            expect(page.get_by_role('button', name='Обновить историю', exact=True)).to_be_enabled()
            retry(page)
            stalled[0].abort(); page.unroute('**/api/me/attempts')
            checked('manual history retry cancels a stuck request and starts a new one')

            timed_out = []
            page.route('**/api/me/attempts', lambda route: timed_out.append(route))
            page.reload()
            expect(page.get_by_text('Не удалось загрузить историю.', exact=False)).to_be_visible(timeout=20000)
            expect(page.get_by_text('Первый результат ещё впереди')).not_to_be_visible()
            expect(page.get_by_text('История не загружена', exact=True)).to_be_visible()
            page.unroute('**/api/me/attempts')
            for route in timed_out: route.abort()
            retry(page)
            page.route('**/api/me/attempts', lambda route: route.abort())
            click(page, 'Обновить историю')
            expect(page.get_by_text('Не удалось загрузить историю.', exact=False)).to_be_visible()
            expect(page.locator('.history-list > div')).to_have_count(2)
            page.unroute('**/api/me/attempts'); retry(page)
            checked('request timeout, network failure and retry preserve loaded history without false empty state')

            # Same browser: changing role in tab B must update tab A as well.
            other = ctx.new_page(); other.goto('/')
            click(other, 'Выйти'); other.goto(link); click(other, 'Я работодатель')
            expect(other.locator('.workspace-label')).to_have_text('КАБИНЕТ РАБОТОДАТЕЛЯ')
            page.bring_to_front(); page.evaluate("window.dispatchEvent(new Event('focus'))")
            expect(page.locator('.workspace-label')).to_have_text('КАБИНЕТ РАБОТОДАТЕЛЯ')
            expect(page.locator('.history-list')).to_have_count(0)
            expect(page.locator('.account')).not_to_contain_text(candidate['email'])
            checked('role change in another tab clears candidate UI and restores the actual employer session')

            # Replace the cookie without storage/focus events (e.g. restored tab).
            response = ctx.request.post('/api/auth/demo', headers={'X-Requested-With':'fsp-web'},
                data={'account':'candidate', 'run_token':link.split('#demo=')[1]})
            assert response.ok
            page.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted:true}))")
            expect(page.locator('.account')).to_contain_text(candidate['email'])
            nav(page, 'Подтверждение навыков'); expect(page.locator('.history-list > div')).to_have_count(2)
            # New identity of the SAME role; the old header must stop an old tab's request.
            run = ctx.request.post('/api/auth/demo-runs', headers={'X-Requested-With':'fsp-web'}, data={}).json()
            replacement = ctx.request.post('/api/auth/demo', headers={'X-Requested-With':'fsp-web'},
                data={'account':'candidate', 'run_token':run['token']}).json()
            click(page, 'Обновить историю')
            expect(page.locator('.account')).to_contain_text(replacement['email'])
            expect(page.locator('.history-list > div')).to_have_count(2)
            expect(page.locator('.demo-run-info')).to_contain_text(run['candidate_code'])
            checked('restored-page event and history retry recover role changes and same-role account changes')

            ctx.clear_cookies()
            click(page, 'Обновить историю')
            expect(page.get_by_role('heading', name='Добро пожаловать', exact=True)).to_be_visible()
            expect(page.locator('.history-list')).to_have_count(0)
            # Expired sessions can log in again and reach the requested section.
            page.goto(link); click(page, 'Я кандидат')
            nav(page, 'Подтверждение навыков'); expect(page.locator('.history-list > div')).to_have_count(2)
            checked('expired session redirects to login, clears private UI, and fresh login restores the original history')
            assert not errors, errors
            page.screenshot(path=str(args.out / 'restored-history.png'), full_page=True)
        except Exception:
            page.screenshot(path=str(args.out / 'failure.png'), full_page=True)
            raise
        finally:
            (args.out / 'result.json').write_text(json.dumps({'checks':checks, 'page_errors':errors}, ensure_ascii=False, indent=2))
            browser.close()


if __name__ == '__main__':
    main()

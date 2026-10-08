"""Visible-UI acceptance audit. No database reads and no API account setup.

Only creates fictional demo accounts. Answers are computed from displayed task
text; PDF checks use files downloaded through visible links. Does not touch
other users' profiles. Screenshots/results are local and contain test data only.
"""
import argparse
import ast
import json
import re
import secrets
import time
from pathlib import Path

import pymupdf
from playwright.sync_api import expect, sync_playwright


def solve_visible(text):
    if 'Планировщик Python' in text:
        a, b, c, d = map(int, re.findall(r'[ABCD] \((\d+) с\)', text))
        return max(a + c, b) + d
    if 'Клиент делает ровно' in text:
        n = int(re.search(r'ровно (\d+)', text)[1])
        duration = int(re.search(r'занимает (\d+)', text)[1])
        pause = int(re.search(r'пауза (\d+)', text)[1])
        return n * duration + sum(pause * 2**i for i in range(n-1))
    if 'Пустой LRU-кеш Python' in text:
        from collections import OrderedDict
        capacity = int(re.search(r'хранит (\d+)',text)[1])
        keys = ast.literal_eval(re.search(r'Обращения: (\[[^\]]+\])',text)[1])
        latency = int(re.search(r'длительностью (\d+)',text)[1])
        cache, misses = OrderedDict(), 0
        for key in keys:
            if key in cache: cache.move_to_end(key)
            else:
                misses += 1
                cache[key] = True
                if len(cache) > capacity: cache.popitem(last=False)
        return misses * latency
    if 'Клиент выполняет четыре операции' in text:
        streams = ast.literal_eval(re.search(r'операциям: (\[.*\])\.',text)[1])
        duration = int(re.search(r'длится (\d+)',text)[1])
        return sum(next((i+1 for i,status in enumerate(stream) if status != 503),3) for stream in streams)*duration
    if 'Требование: функция возвращает abs(x)' in text:
        values=ast.literal_eval(re.search(r'Входы тестов: (\[[^\]]+\])',text)[1])
        return sum(abs(v)!=v for v in values)
    if 'xs = ' in text:
        values = ast.literal_eval(re.search(r'xs = (\[[^\n]+\])', text)[1])
        if 'total =' in text:
            start=int(re.search(r'total = (\d+)',text)[1])
            return start + sum(v * (-1 if i%2 else 1) for i,v in enumerate(values))
        divisor = int(re.search(r'x % (\d+)', text)[1])
        return sum(v for v in values if v % divisor == 0)
    if 'Спецификация:' in text:
        low, high = map(int, re.search(r'(\d+) ≤ x ≤ (\d+)', text).groups())
        values = ast.literal_eval(re.search(r'Входы тестов: (\[[^\]]+\])', text)[1])
        return sum(v in (low, high) for v in values)
    raise ValueError('Unexpected visible task; no hidden answer fallback')


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='https://85-137-26-131.sslip.io')
    parser.add_argument('--output', type=Path, default=Path('audit/timofey-2026-10-09/ui'))
    parser.add_argument('--expect-core-rule', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    suffix = secrets.token_hex(4)
    email = f'research-{suffix}@example.org'
    password = 'Synthetic-' + secrets.token_hex(12)
    checks, errors, server_errors = [], [], []
    started = time.monotonic()
    result = dict(base_url=args.base_url, accounts='3 new fictional accounts; publication cleanup recorded separately',
                  scope='Visible UI only, no database/hidden answer access', checks=checks,
                  page_errors=errors, server_errors=server_errors)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        contexts = [browser.new_context(viewport={'width':1440,'height':1000},locale='ru-RU') for _ in range(3)]
        pages = [c.new_page() for c in contexts]
        for page in pages:
            page.on('pageerror',lambda error: errors.append(str(error)))
            page.on('response',lambda r: server_errors.append(dict(url=r.url,status=r.status)) if r.status>=500 else None)
            page.goto(args.base_url)
        candidate, first, second = pages
        expect(candidate.get_by_text('Демонстрационный стенд · используйте только вымышленные данные')).to_be_visible()

        def passed(name, page=None, screenshot=None):
            checks.append(dict(name=name,status='pass'))
            print(name,flush=True)
            if screenshot: page.screenshot(path=str(args.output/screenshot),full_page=True)

        def register(page, address, role):
            page.get_by_role('button',name='Регистрация',exact=True).click()
            page.get_by_label('Я на платформе как').select_option(role)
            page.get_by_label('Электронная почта').fill(address)
            page.get_by_label('Пароль',exact=True).fill(password)
            page.get_by_role('checkbox').check()
            page.get_by_role('button',name='Создать аккаунт',exact=True).click()
            page.get_by_role('button',name='Подтвердить почту',exact=True).click()
            page.get_by_role('button',name='Войти в кабинет').click()
            page.locator('.sidebar').wait_for()

        def nav(page, name): page.get_by_role('button',name=name,exact=True).click()
        def profile_save():
            candidate.get_by_role('button',name='Сохранить профиль',exact=True).click()
            expect(candidate.get_by_role('status')).to_contain_text('Профиль сохранён')
        def bank_page(page):
            nav(page,'Подбор кандидатов')
            nav(page,'Банк кандидатов')
            page.get_by_role('button',name='Применить фильтры').click()
            page.wait_for_load_state('networkidle')
        def card(page): return page.locator('.candidate-card').filter(has=page.locator(f'a[href="{pdf_href}"]'))
        def download_pdf(page, link, name):
            with page.expect_download() as d: link.click()
            dest = args.output/name
            d.value.save_as(str(dest))
            with pymupdf.open(dest) as doc: return '\n'.join(p.get_text() for p in doc)
        try:
            register(candidate,email,'candidate')
            nav(candidate,'Мой профиль')
            candidate.get_by_label('Имя и фамилия').fill('Исследовательский Тест')
            candidate.get_by_label('Телефон / способ связи').fill('+7 000 555-01-09')
            candidate.get_by_label('О себе',exact=True).fill('Вымышленный профиль. Скрытый контакт '+email)
            candidate.get_by_label('Роли в команде').fill('Разработчик, связь '+email)
            candidate.get_by_label('Python',exact=True).check()
            candidate.get_by_label('Тестирование',exact=True).check()
            candidate.get_by_label('Публиковать профиль в банке кандидатов').check()
            profile_save()
            pdf_href = candidate.get_by_role('link',name='Скачать мой PDF').get_attribute('href')
            passed('ТЗ: регистрация, демоподтверждение почты, профиль и согласия',candidate,'01-profile.png')
            nav(candidate,'Подтверждение навыков')
            candidate.get_by_label('Уровень теста').select_option('Senior')
            nav(candidate,'Начать тест')
            candidate.get_by_label('Ответ на задание 1',exact=True).wait_for()
            wrong_core = 0
            failed_core_count = 2 if candidate.locator(".question").count() == 8 else 1
            for q in candidate.locator('.question').all():
                text = q.locator('pre').inner_text()
                answer = '-99999'
                if args.expect_core_rule:
                    answer = str(solve_visible(text))
                    if 'Планировщик Python' in text and wrong_core < failed_core_count:
                        answer = '-99999'
                        wrong_core += 1
                q.locator('input').fill(answer)
            nav(candidate,'Завершить и узнать результат')
            expect(candidate.locator('.result')).to_contain_text('Пока не подтверждён')
            expect(candidate.locator('.result')).to_contain_text('75%' if args.expect_core_rule else '0%')
            if args.expect_core_rule:
                passed('Новая рубрика: 75% с недостаточным подтверждением основного навыка не подтверждают Senior')
            passed('ТЗ: провал Senior не присваивает более низкий грейд',candidate,'02-failed.png')
            nav(candidate,'К выбору уровня')
            candidate.get_by_label('Уровень теста').select_option('Junior')
            nav(candidate,'Начать тест')
            candidate.get_by_label('Ответ на задание 1',exact=True).wait_for()
            for q in candidate.locator('.question').all():
                q.locator('input').fill(str(solve_visible(q.locator('pre').inner_text())))
            nav(candidate,'Завершить и узнать результат')
            expect(candidate.locator('.result')).to_contain_text('Уровень подтверждён')
            expect(candidate.locator('.result')).to_contain_text('100%')
            passed('ТЗ: добровольный Junior, ответы из видимого текста, подтверждение и объяснения',candidate,'03-passed.png')
            nav(candidate,'К выбору уровня')
            nav(candidate,'Начать тест')
            expect(candidate.get_by_role('alert')).to_contain_text('24 часа')
            candidate.get_by_label('Уровень теста').select_option('Middle')
            nav(candidate,'Начать тест')
            expect(candidate.get_by_role('alert')).to_contain_text('90 дней')
            passed('ТЗ: интерфейс показывает ограничения повторной сдачи и смены грейда')
            nav(candidate,'Мой профиль')
            own_pdf = download_pdf(candidate,candidate.get_by_role('link',name='Скачать мой PDF'),'own.pdf')
            assert 'Исследовательский Тест' in own_pdf and email in own_pdf
            passed('ТЗ: PDF скачивается, кириллица и собственные контакты читаются')

            for i,page in enumerate([first,second],1):
                register(page,f'employer-{i}-{suffix}@example.org','employer')
                nav(page,'Моя компания')
                page.get_by_label('Название компании').fill(f'Аудит {i} {suffix}')
                page.get_by_label('Направление деятельности').fill('Тестовая разработка')
                page.get_by_label('Способ связи с работодателем').fill(f'hr-{i}@example.org')
                page.get_by_label('О компании и команде').fill('Вымышленная компания для проверки сценариев.')
                nav(page,'Сохранить компанию')
                expect(page.get_by_role('status')).to_contain_text('Компания сохранена')
                bank_page(page)
                expect(card(page)).to_contain_text('Контакты после согласия')
                expect(card(page)).not_to_contain_text(email)
                redacted = download_pdf(page,card(page).get_by_role('link',name='Скачать PDF профиля'),f'employer-{i}-before.pdf')
                assert email not in redacted and '+7 000 555-01-09' not in redacted
            passed('ТЗ: две компании видят профиль без ФСП, контакты закрыты в карточке и PDF',first,'04-employer.png')

            nav(first,'По потребности')
            first.get_by_label('Название потребности').fill('Контроль React '+suffix)
            required=first.locator('.field').filter(has=first.locator('span',has_text=re.compile('^Обязательные навыки$')))
            required.get_by_label('React',exact=True).check()
            nav(first,'Сформировать подборку')
            expect(first.get_by_role('heading',name='Подтверждённых соответствий нет')).to_be_visible()
            expect(first.get_by_role('heading',name=re.compile('Частичное соответствие'))).to_be_visible()
            passed('ТЗ: обязательный непроверяемый React не выдается за полное совпадение',first,'05-no-full-match.png')
            required.get_by_label('React',exact=True).uncheck()
            first.get_by_label('Название потребности').fill('Контроль Python '+suffix)
            nav(first,'Сформировать подборку')
            expect(first.locator('.saved-searches button')).to_have_count(2)
            first.locator('.saved-searches button').filter(has_text='Контроль React').click()
            expect(first.get_by_role('heading',name='Подтверждённых соответствий нет')).to_be_visible()
            passed('ТЗ: уточнение запроса сохраняет предыдущую подборку')
            bank_page(first)
            first.get_by_label('Подтверждённый навык').select_option('react')
            nav(first,'Применить фильтры')
            expect(first.get_by_role('heading',name='Подходящих профилей пока нет')).to_be_visible()
            first.get_by_label('Подтверждённый навык').select_option('')
            nav(first,'Применить фильтры')
            expect(card(first)).to_be_visible()
            passed('ТЗ: фильтр по неподтверждаемому навыку дает пустой банк')

            for i,page in enumerate([first,second],1):
                card(page).get_by_role('button',name='Пригласить',exact=True).click()
                page.get_by_label('Зарплата от, ₽ / месяц').fill('0')
                nav(page,'Отправить приглашение')
                assert not page.get_by_label('Зарплата от, ₽ / месяц').evaluate('(e)=>e.checkValidity()')
                expect(page.get_by_role('heading',name='Начните с открытых условий')).to_be_visible()
                page.get_by_label('Зарплата от, ₽ / месяц').fill('100000')
                page.get_by_label('Зарплата до, ₽ / месяц').fill('90000')
                nav(page,'Отправить приглашение')
                assert not page.get_by_label('Зарплата до, ₽ / месяц').evaluate('(e)=>e.checkValidity()')
                page.get_by_label('Зарплата до, ₽ / месяц').fill('150000')
                nav(page,'Отправить приглашение')
                expect(page.get_by_role('heading',name='Приглашение отправлено')).to_be_visible()
                nav(page,'Готово')
            passed('ТЗ: нулевая/перевернутая вилка отвергается, корректное приглашение без вакансии отправляется')
            nav(candidate,'Приглашения')
            offer=candidate.locator('.invitation').filter(has_text=f'Аудит 1 {suffix}')
            expect(offer).to_contain_text('hr-1@example.org')
            expect(offer).to_contain_text('150')
            offer.get_by_role('button',name='Отметить просмотренным',exact=True).click()
            expect(offer.locator('.badge')).to_have_text('Просмотрено')
            offer.get_by_role('button',name='Принять и раскрыть контакты').click()
            expect(offer.locator('.badge')).to_have_text('Принято')
            other=candidate.locator('.invitation').filter(has_text=f'Аудит 2 {suffix}')
            other.get_by_role('button',name='Отклонить',exact=True).click()
            expect(other.locator('.badge')).to_have_text('Отклонено')
            passed('ТЗ: условия до общения, просмотр/принятие/отклонение',candidate,'06-decisions.png')
            for page in [first,second]:
                nav(page,'Приглашения')
            expect(first.locator('.invitation')).to_contain_text(email)
            expect(second.locator('.invitation')).not_to_contain_text(email)
            expect(second.locator('.invitation .badge')).to_have_text('Отклонено')
            bank_page(second)
            redacted=download_pdf(second,card(second).get_by_role('link',name='Скачать PDF профиля'),'second-after.pdf')
            assert email not in redacted
            passed('ТЗ: принятие одной компании не раскрывает контакты второй, в том числе PDF')
            offer.get_by_role('button',name='Открыть диалог').click()
            candidate.get_by_label('Сообщение',exact=True).fill('Контрольное сообщение аудита')
            nav(candidate,'Отправить')
            first.get_by_role('button',name='Открыть диалог').click()
            expect(first.locator('.message')).to_contain_text('Контрольное сообщение аудита')
            passed('O03: участники принятого приглашения видят внутренний диалог')
            nav(candidate,'Достижения ФСП')
            nav(candidate,'Связать демонстрационный ФСП ID')
            expect(candidate.get_by_role('heading',name='Демонстрационный профиль связан')).to_be_visible()
            passed('ТЗ: демонстрационная привязка ФСП после полного сценария без ФСП',candidate,'07-fsp.png')
            nav(candidate,'Подтверждение навыков')
            expect(candidate.locator('.assessment-start')).to_contain_text('Junior')
            passed('ТЗ: привязка ФСП не меняет подтверждённый грейд')
            for page in pages:
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal mobile overflow'
            first.screenshot(path=str(args.output/'08-mobile.png'),full_page=True)
            passed('O04: текущие экраны обеих ролей не имеют горизонтального переполнения на 390px')
            nav(candidate,'Мой профиль')
            candidate.get_by_label('Публиковать профиль в банке кандидатов').uncheck()
            profile_save()
            bank_page(first)
            expect(card(first)).to_have_count(0)
            nav(first,'Приглашения')
            expect(first.locator('.invitation')).not_to_contain_text(email)
            passed('ТЗ: отзыв публикации скрывает профиль и ранее раскрытые контакты')
            assert not errors and not server_errors, (errors,server_errors)
            result['status']='pass'
        except Exception as error:
            result['status']='fail'
            result['failure']=str(error)
            for i,page in enumerate(pages):
                page.screenshot(path=str(args.output/f'failure-{i}.png'),full_page=True)
                (args.output/f'failure-{i}.txt').write_text(page.locator('body').inner_text())
            raise
        finally:
            try:
                nav(candidate,'Мой профиль')
                publication = candidate.get_by_label('Публиковать профиль в банке кандидатов')
                if publication.is_checked():
                    publication.uncheck()
                    profile_save()
                result['own_candidate_unpublished'] = True
            except Exception as cleanup_error:
                result['cleanup_error'] = str(cleanup_error)
            result['duration_seconds']=round(time.monotonic()-started,2)
            (args.output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
            browser.close()
    print(json.dumps(dict(status=result['status'],checks=len(checks),seconds=result['duration_seconds']),ensure_ascii=False))

if __name__=='__main__': run()

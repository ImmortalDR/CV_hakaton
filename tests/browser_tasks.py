"""Employer-task UI and API acceptance with four new fictional accounts only."""
import argparse
import json
import secrets
import time
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base-url',default='http://127.0.0.1:3082');parser.add_argument('--out',type=Path,default=Path('audit/modernization/tasks-ui'));args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True);start=time.monotonic();records=[];errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        def actor(role):
            context=browser.new_context(viewport={'width':1365,'height':1000},extra_http_headers={'X-Requested-With':'fsp-web'})
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            email='tasks-'+secrets.token_hex(5)+'@example.org';password=secrets.token_urlsafe(20)
            def call(path,body=None,method=None):
                deadline=time.monotonic()+65
                while True:
                    response=context.request.fetch(args.base_url+'/api'+path,method=method or ('GET' if body is None else 'POST'),data=body)
                    if response.status!=429 or time.monotonic()>=deadline:return response
                    page.wait_for_timeout(1000)  # Respect the existing public auth limiter.

            r=call('/auth/register',dict(email=email,password=password,role=role,processing=True));assert r.status==201,r.text()
            token=r.json()['demo_verification_url'].split('#verify=')[1]
            assert call('/auth/verify',{'token':token}).status==200
            assert call('/auth/login',{'email':email,'password':password}).status==200
            uid=call('/auth/me').json()['id'];records.append(dict(role=role,id=uid,email=email))
            page.goto(args.base_url);return page,call,uid
        candidate,c,cid=actor('candidate');employer,e,eid=actor('employer');outsider,o,oid=actor('candidate');second,s,sid=actor('employer')
        profile=dict(name='Кандидат Адресных Заданий',phone='+7 000 111-22-33',about='Вымышленная анкета для проверки',specialization='python',claimed_grade='Junior',skills=['python'],processing=True,published=True,show_experience=True)
        assert c('/me/profile',profile,'PUT').status==200
        for call in [e,s]:assert call('/me/company',dict(name='Компания Тест Заданий',description='Вымышленная команда проверки заданий',sector='ИТ',contact='hr@example.org'),'PUT').status==200
        invitation=e('/invitations',dict(candidate_id=cid,request_id=str(uuid4()),description='Адресное предложение для тестового кандидата',salary_min=100000,salary_max=150000,currency='RUB')).json()
        assert c('/invitations/'+invitation['id'],{'status':'accepted'},'PATCH').status==200
        # Reload obtains persisted role/profile state, then all task actions use visible UI.
        employer.reload();candidate.reload()
        def nav(page):page.locator('nav').get_by_role('button',name='Задания от компаний').click()
        nav(employer)
        employer.get_by_label('Получатель задания').select_option(cid)
        employer.get_by_label('Название задания',exact=True).fill('Надёжный API')
        employer.get_by_label('Задача и ожидаемый ответ').fill('Предложите безопасные повторы запросов при сетевых сбоях.')
        employer.get_by_label('Критерии оценки',exact=True).fill('Идемпотентность, ограничение попыток и задержка повторов.')
        employer.get_by_role('button',name='Предложить план кандидату').click()
        expect(employer.locator('.task-plan')).to_contain_text('Ожидает согласия')
        plan=e('/tasks').json()['plans'][0];records.append(dict(plan_id=plan['id'],invitation_id=invitation['id']))
        assert s('/tasks').json()['plans']==[] and o('/tasks').json()['plans']==[]
        assert o('/tasks/plans/'+plan['id'],{'status':'active'},'PATCH').status==404
        nav(candidate);expect(candidate.locator('.task-plan')).to_contain_text('Надёжный API')
        candidate.screenshot(path=str(args.out/'01-consent.png'),full_page=True)
        candidate.get_by_role('button',name='Согласиться и включить выдачу').click()
        expect(candidate.locator('.task-assignment')).to_contain_text('Ожидает ответа')
        for width in [360,390,768]:
            candidate.set_viewport_size({'width':width,'height':900})
            assert candidate.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'),width
        candidate.screenshot(path=str(args.out/'02-task-mobile.png'),full_page=True)
        candidate.get_by_label('Ответ на задание').fill('Ключ идемпотентности, не более трёх попыток, экспоненциальная задержка.')
        candidate.get_by_role('button',name='Отправить ответ',exact=True).click()
        expect(candidate.locator('.task-assignment')).to_contain_text('На проверке')
        employer.get_by_role('button',name='Обновить задания').click()
        employer.get_by_label('Оценка от 0 до 100').fill('85')
        employer.get_by_label('Обоснование оценки').fill('Учтены идемпотентность и число повторов; стоит добавить jitter.')
        employer.get_by_role('button',name='Сохранить оценку').click()
        expect(employer.locator('.task-assignment')).to_contain_text('85/100')
        employer.screenshot(path=str(args.out/'03-reviewed.png'),full_page=True)
        candidate.get_by_role('button',name='Обновить задания').click()
        expect(candidate.locator('.task-assignment')).to_contain_text('85/100')
        assert c('/me/profile').json()['verified_grade'] is None
        assert c('/me/profile').json()['task_last_reviewed_at']
        assert s('/candidates/'+cid).json().get('task_last_reviewed_at') is None
        aid=c('/tasks').json()['plans'][0]['assignments'][0]['id']
        assert s('/tasks/assignments/'+aid+'/review',{'score':99,'feedback':'Попытка подмены другой компанией'}).status==404
        candidate.get_by_role('button',name='Приостановить выдачу').click()
        expect(candidate.locator('.task-plan')).to_contain_text('Выдача приостановлена')
        # Remove only our own publication; answers disappear from the company view.
        assert c('/me/profile',profile|{'published':False},'PUT').status==200
        employer.get_by_role('button',name='Обновить задания').click()
        expect(employer.locator('.task-assignment')).to_have_count(0)
        expect(employer.locator('.task-plan')).to_contain_text('нужно действующее согласие')
        employer.screenshot(path=str(args.out/'04-revoked.png'),full_page=True)
        assert not errors,errors
        browser.close()
    result=dict(status='pass',base_url=args.base_url,duration_seconds=round(time.monotonic()-start,2),
                checks=['consent','create','answer','review','grade_unchanged','profile_freshness','cross_company_isolation','cross_candidate_isolation','mobile_360_390_768','pause','revocation'],
                page_errors=errors,records=records,own_candidate_unpublished=True,
                scope='Task lifecycle through UI; fictional account/invitation setup and adversarial checks through API; periodic deadlines covered separately by server/worker tests')
    (args.out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()

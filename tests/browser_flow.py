"""Real Chromium flow against the running demo. No API responses are mocked.

Creates two new fictional accounts, reads server-side task parameters ONLY for
the test oracle, then operates all business actions through the UI. Run via
scripts/run_local.py so the independent oracle can read the same demo database.
"""

import argparse
import json
import os
import secrets
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from evaluation.oracles import solve
from fsp.models import Attempt, now
from fsp import bank
from datetime import timedelta
from urllib.parse import urlsplit
import pymupdf


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:3080")
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--legacy-fixture", action="store_true", help="Only on isolated fsp_test: add a historical attempt to our new account")
    args = parser.parse_args()
    output = args.out or (Path("demo") if args.record else Path("audit/current/browser"))
    output.mkdir(parents=True, exist_ok=True)
    suffix = secrets.token_hex(4)
    candidate_email = f"candidate-{suffix}@example.org"
    employer_email = f"employer-{suffix}@example.org"
    password = "Synthetic-demo-" + secrets.token_hex(8)
    if args.legacy_fixture:
        assert urlsplit(os.environ["DATABASE_URL"]).path == "/fsp_test", "Historical fixture requires isolated fsp_test"
    engine = create_engine(os.environ["DATABASE_URL"])
    errors = []
    chapters = []
    started = time.monotonic()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        kwargs = {"viewport": {"width": 1440, "height": 1000}, "locale": "ru-RU"}
        if args.record:
            kwargs.update(
                record_video_dir=str(output / "raw-video"),
                record_video_size={"width": 1440, "height": 1000},
            )
        context = browser.new_context(**kwargs)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.base_url)
        assert context.request.get(args.base_url + "/api/health").json()[
            "demo"
        ], "Only a demo environment may be used"

        def chapter(title, filename=None):
            print(title, flush=True)
            chapters.append(
                {"seconds": round(time.monotonic() - started, 1), "title": title}
            )
            page.evaluate("document.getElementById('demo-caption')?.remove()")
            if filename:
                page.screenshot(path=str(output / filename), full_page=False)
            if args.record:
                page.evaluate(
                    """title=>{document.getElementById('demo-caption')?.remove();const e=document.createElement('div');e.id='demo-caption';e.textContent=title;e.style.cssText='position:fixed;left:250px;right:24px;bottom:18px;background:#310f53;color:white;padding:16px 22px;border-radius:12px;z-index:100;box-shadow:0 6px 24px #0003;font:16px system-ui;pointer-events:none';document.body.append(e)}""",
                    title,
                )
                page.wait_for_timeout(11000)

        def mobile_check(name):
            for width in (360, 390, 768):
                page.set_viewport_size({"width": width, "height": 844})
                if not page.evaluate("document.documentElement.scrollWidth <= innerWidth"):
                    page.screenshot(path=str(output/(name+"-overflow.png")), full_page=True)
                    print(page.evaluate("[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>({tag:e.tagName,cls:e.className,right:e.getBoundingClientRect().right})).slice(0,20)"), flush=True)
                    raise AssertionError(f"{name}: overflow at {width}")
                if width == 390:
                    page.screenshot(path=str(output / (name+"-mobile.png")), full_page=False)
            page.set_viewport_size({"width": 1440, "height": 1000})

        def pdf_check(opened):
            response = context.request.get(args.base_url + f"/api/profiles/{candidate_id}/pdf")
            assert response.status == 200
            content = response.body()
            stem = "pdf-open" if opened else "pdf-closed"
            (output/(stem+".pdf")).write_bytes(content)
            with pymupdf.open(stream=content, filetype="pdf") as doc:
                text = "\n".join(p.get_text() for p in doc)
                assert (candidate_email in text) == opened
                assert "МСК (UTC+03:00)" in text
                if opened:
                    assert "Электронная почта:" in text and "Телефон:" in text
                else:
                    assert "+7 000 000-00-00" not in text
                doc[0].get_pixmap(matrix=pymupdf.Matrix(1.3,1.3)).save(str(output/(stem+".png")))

        def register(email, role):
            page.get_by_role("button", name="Регистрация", exact=True).click()
            page.get_by_label("Я на платформе как").select_option(role)
            page.get_by_label("Электронная почта").fill(email)
            page.get_by_label("Пароль", exact=True).fill(password)
            page.get_by_role("checkbox").check()
            page.get_by_role("button", name="Создать аккаунт", exact=True).click()
            page.get_by_role("button", name="Подтвердить почту", exact=True).wait_for()
            chapter("Подтверждение e-mail: в демо доставка письма явно имитируется")
            page.get_by_role("button", name="Подтвердить почту", exact=True).click()
            page.get_by_role("button", name="Войти в кабинет").click()
            page.locator(".sidebar").wait_for()

        def login(email):
            page.get_by_label("Электронная почта").fill(email)
            page.get_by_label("Пароль", exact=True).fill(password)
            page.get_by_role("button", name="Войти в кабинет").click()
            page.locator(".sidebar").wait_for()

        def logout():
            page.get_by_role("button", name="Выйти", exact=True).click()
            page.get_by_label("Электронная почта").wait_for()

        chapter(
            "ФСП · Обратный найм: навыки → категория → личное предложение",
            "01-welcome.png",
        )
        register(candidate_email, "candidate")
        page.get_by_role("button", name="Мой профиль", exact=True).click()
        page.get_by_label("Имя и фамилия").fill("Алексей Демонстрационный")
        page.get_by_label("Телефон / способ связи").fill("+7 000 000-00-00")
        page.get_by_label("Роли в команде").fill("Бэкенд-разработчик")
        page.get_by_label("Навыки совместной работы").fill(
            "Командная работа, обратная связь"
        )
        page.get_by_label("Стаж, лет").fill("1")
        page.get_by_label("О себе", exact=True).fill(
            "Вымышленный профиль для сквозной демонстрации. Контакт закрыт до согласия."
        )
        page.get_by_label("Python", exact=True).check()
        page.get_by_label("Тестирование", exact=True).check()
        page.get_by_label("Публиковать профиль в банке кандидатов").check()
        page.get_by_role("button", name="Сохранить профиль", exact=True).click()
        expect(page.get_by_role("status")).to_contain_text("Профиль сохранён")
        # Prefer page-bound fetch (shares UI cookies). APIRequestContext alone
        # has failed on the public stand with a body missing `id`.
        me = page.evaluate(
            """async () => {
              const r = await fetch('/api/auth/me', { credentials: 'include' });
              return await r.json();
            }"""
        )
        if not isinstance(me, dict) or "id" not in me:
            me = context.request.get(args.base_url + "/api/auth/me").json()
        candidate_id = me["id"]
        if args.legacy_fixture:
            # This account was just created by this script; no existing records are edited.
            with Session(engine) as db:
                qs = bank.generate("python", "Junior", "legacy-ui-"+suffix, version="1.1.0")
                old = Attempt(user_id=candidate_id, specialization="python", grade="Junior",
                    seed="legacy-ui-"+suffix, version="1.1.0", variant_hash=bank.fingerprint(qs),
                    questions=qs, answers={}, result=bank.grade_answers(qs, {}, version="1.1.0"),
                    status="completed", created_at=now()-timedelta(days=100),
                    finished_at=now()-timedelta(days=100), expires_at=now()-timedelta(days=100))
                db.add(old); db.commit()
        chapter(
            "Ручное заполнение профиля и отдельное согласие на публикацию",
            "02-profile.png",
        )
        page.get_by_role("button", name="Подтверждение навыков", exact=True).click()
        page.get_by_label("Уровень теста").select_option("Junior")
        expect(page.locator(".page-title")).to_contain_text("8 заданий")
        expect(page.locator(".assessment-access")).to_contain_text("доступен сейчас")
        mobile_check("01-test-start")
        if args.legacy_fixture:
            expect(page.locator(".history-list")).to_contain_text("4 задания")
            page.get_by_role("button", name="Посмотреть", exact=True).first.click()
            expect(page.locator(".page-title")).to_contain_text("4 задания")
            expect(page.locator(".question-label").last).to_contain_text("Задание 4 из 4")
            chapter("Историческая методика 1.1.0: четыре сохранённых задания", "legacy-four.png")
            mobile_check("legacy-four")
            page.get_by_role("button", name="К выбору уровня").click()
        page.get_by_role("button", name="Начать тест", exact=True).click()
        page.get_by_label("Ответ на задание 1", exact=True).wait_for()
        expect(page.locator(".question-label").last).to_contain_text("Задание 8 из 8")
        expect(page.locator(".page-title")).to_contain_text("8 заданий")
        mobile_check("02-test-active")
        page.locator(".question").last.scroll_into_view_if_needed()
        page.screenshot(path=str(output/"eight-of-eight.png"))
        page.evaluate("scrollTo(0,0)")
        chapter(
            "Первичный тест: 8 заданий. Эталон и оценка хранятся на сервере",
            "03-assessment.png",
        )
        with Session(engine) as db:
            attempt = db.scalar(
                select(Attempt).where(
                    Attempt.user_id == candidate_id, Attempt.status == "active"
                )
            )
            assert attempt is not None
            answers = {q["id"]: str(solve(q)) for q in attempt.questions}
        for number, answer in answers.items():
            page.get_by_label(f"Ответ на задание {number}", exact=True).fill(answer)
        page.get_by_role("button", name="Завершить и узнать результат").click()
        expect(page.locator(".result")).to_contain_text("100%")
        chapter(
            "Результат 100%: Junior подтверждён. Это реальный ответ работающего API",
            "04-result.png",
        )
        expect(page.locator(".result")).to_contain_text("Верных ответов: 8 из 8")
        expect(page.locator(".history-list")).to_contain_text("8 заданий")
        mobile_check("03-test-result")
        page.get_by_role("button", name="К выбору уровня").click()
        expect(page.get_by_role("button", name="Начать тест", exact=True)).to_be_disabled()
        expect(page.locator(".assessment-access")).to_contain_text("24 часа")
        expect(page.locator(".assessment-access")).to_contain_text("Ближайшее начало")
        chapter("Пересдача: ограничение и дата видны до запроса", "retake-24h.png")
        page.get_by_label("Уровень теста").select_option("Middle")
        expect(page.locator(".assessment-access")).to_contain_text("90 дней")
        expect(page.get_by_role("button", name="Начать тест", exact=True)).to_be_disabled()
        mobile_check("04-grade-cooldown")
        chapter("Смена уровня: ограничение 90 дней до запуска", "grade-90d.png")
        page.get_by_role("button", name="Мой профиль", exact=True).click()
        with page.expect_download() as download:
            page.get_by_role("link", name="Скачать мой PDF").click()
        download.value.save_as(str(output / "candidate-profile.pdf"))
        chapter("Профиль автоматически доступен в PDF. ФСП ID для этого не требуется")
        logout()
        register(employer_email, "employer")
        page.get_by_role("button", name="Моя компания", exact=True).click()
        page.get_by_label("Название компании").fill("Орбита — демонстрация")
        page.get_by_label("Направление деятельности").fill(
            "Разработка программных продуктов"
        )
        page.get_by_label("Способ связи с работодателем").fill("demo-team@example.org")
        page.get_by_label("О компании и команде").fill(
            "Вымышленная команда разработки API. Создаём сервисы для обработки данных."
        )
        page.get_by_role("button", name="Сохранить компанию", exact=True).click()
        expect(page.get_by_role("status")).to_contain_text("Компания сохранена")
        chapter(
            "Кабинет работодателя: профиль компании и способ связи", "05-company.png"
        )
        page.get_by_role("button", name="Подбор кандидатов", exact=True).click()
        expect(page.locator(".candidate-card").first).to_be_visible()
        page.get_by_role("button", name="По потребности", exact=True).click()
        page.get_by_role("button", name="Сформировать подборку").click()
        expect(page.locator(".saved-searches button").first).to_be_visible()
        chapter(
            "Структурированная потребность → категории, доказательства и сохранённая подборка",
            "06-search.png",
        )
        card = page.locator(".candidate-card").filter(
            has=page.locator(f'a[href="/api/profiles/{candidate_id}/pdf"]')
        )
        expect(card).to_contain_text("Контакты после согласия")
        expect(card).not_to_contain_text(candidate_email)
        expect(card).to_contain_text("1 год · со слов кандидата")
        card.get_by_text("Результаты и источники", exact=True).click()
        expect(card).to_contain_text("2.0.0")
        pdf_check(False)
        card.scroll_into_view_if_needed()
        chapter("До согласия имя, контакты и свободный текст кандидата скрыты")
        card.get_by_role("button", name="Пригласить", exact=True).click()
        page.get_by_label("Зарплата от, ₽ / месяц").fill("120000")
        page.get_by_label("Зарплата до, ₽ / месяц").fill("100000")
        page.get_by_role("button", name="Отправить приглашение").click()
        expect(page.locator(".modal [role=alert]")).to_contain_text("Нижняя граница не должна превышать верхнюю")
        page.screenshot(path=str(output/"salary-validation.png"))
        mobile_check("05-salary-error")
        page.get_by_label("Зарплата до, ₽ / месяц").fill("180000")
        chapter(
            "Адресное приглашение: обязательная вилка в рублях, без публикации вакансии",
            "07-invitation.png",
        )
        page.get_by_role("button", name="Отправить приглашение").click()
        expect(
            page.get_by_role("heading", name="Приглашение отправлено")
        ).to_be_visible()
        page.get_by_role("button", name="Готово", exact=True).click()
        logout()
        login(candidate_email)
        page.get_by_role("button", name="Приглашения", exact=True).click()
        expect(page.locator(".invitation")).to_contain_text("120")
        page.get_by_role("button", name="Отметить просмотренным", exact=True).click()
        expect(page.locator(".invitation .badge")).to_have_text("Просмотрено")
        chapter(
            "Кандидат видит компанию, задачи, зарплату и связь до принятия",
            "08-offer.png",
        )
        page.get_by_role("button", name="Принять и раскрыть контакты").click()
        expect(page.locator(".invitation .badge")).to_have_text("Принято")
        chapter("Принятие раскрывает контакты только этой компании", "09-accepted.png")
        page.get_by_role("button", name="Открыть диалог").click()
        page.get_by_label("Сообщение", exact=True).fill(
            "Добрый день! Готов обсудить задачи команды."
        )
        page.get_by_role("button", name="Отправить", exact=True).click()
        expect(page.locator(".message")).to_contain_text("Готов обсудить")
        chapter("Внутренний диалог доступен участникам принятого приглашения")
        logout()
        login(employer_email)
        page.get_by_role("button", name="Приглашения", exact=True).click()
        expect(page.locator(".invitation .notice")).to_contain_text(candidate_email)
        page.get_by_role("button", name="Открыть диалог").click()
        expect(page.locator(".message")).to_contain_text("Готов обсудить")
        pdf_check(True)
        chapter(
            "Работодатель получил согласие, контакт и сообщение кандидата",
            "10-employer-contact.png",
        )
        if not args.record:
            # A narrow screen must remain usable without horizontal document overflow.
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate(
                "document.documentElement.scrollWidth <= innerWidth"
            ), "Mobile horizontal overflow"
            chapter(
                "Русский интерфейс адаптирован к мобильному экрану", "11-mobile.png"
            )
            page.set_viewport_size({"width": 1440, "height": 1000})
        assert not errors, errors
        video = page.video
        context.close()
        if video:
            video.save_as(str(output / "walkthrough.webm"))
        browser.close()
    engine.dispose()
    result = {
        "status": "pass",
        "browser": "Chromium / Playwright 1.52.0",
        "base_url": args.base_url,
        "duration_seconds": round(time.monotonic() - started, 2),
        "page_errors": errors,
        "chapters": chapters,
        "oracle": "evaluation.oracles.solve reads test parameters from DB, never from a public API",
        "accounts": "two newly registered fictional accounts; no mocks; data retained",
    }
    (output / "browser-result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {k: v for k, v in result.items() if k != "chapters"}, ensure_ascii=False
        ),
        flush=True,
    )


if __name__ == "__main__":
    run()

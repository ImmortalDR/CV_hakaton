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
from fsp.models import Attempt


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:3080")
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    output = Path("demo") if args.record else Path("audit/current/browser")
    output.mkdir(parents=True, exist_ok=True)
    suffix = secrets.token_hex(4)
    candidate_email = f"candidate-{suffix}@example.org"
    employer_email = f"employer-{suffix}@example.org"
    password = "Synthetic-demo-" + secrets.token_hex(8)
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
        chapter(
            "Ручное заполнение профиля и отдельное согласие на публикацию",
            "02-profile.png",
        )
        page.get_by_role("button", name="Подтверждение навыков", exact=True).click()
        page.get_by_label("Уровень теста").select_option("Junior")
        page.get_by_role("button", name="Начать тест", exact=True).click()
        page.get_by_label("Ответ на задание 1", exact=True).wait_for()
        chapter(
            "Первичный тест: 4 варианта задач. Эталон и оценка хранятся на сервере",
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
        card.scroll_into_view_if_needed()
        chapter("До согласия имя, контакты и свободный текст кандидата скрыты")
        card.get_by_role("button", name="Пригласить", exact=True).click()
        page.get_by_label("Зарплата от, ₽ / месяц").fill("120000")
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

#!/usr/bin/env python3
"""Fill LCT solution block (template slides 15–20, 25, 19, 26) — recommended structure 01–06.

Does NOT touch locked 7–11. Keeps expert slides 12–14 as-is (already filled).
After edit: python gate_check_solution.py && capture frames.
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER
from pptx.util import Pt

ROOT = Path(__file__).resolve().parent
PPTX = ROOT / "FSP_NIKITA_DRAFT.pptx"
ASSETS = ROOT / "assets"
EMU = 914400

INK = RGBColor(0x2A, 0x27, 0x33)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
TITLE_ON_DARK = WHITE
ACCENT = RGBColor(0x6B, 0x2D, 0x8B)

PT_TITLE = 22.0
PT_H = 15.0
PT_BODY = 13.0
PT_NUM = 16.0


def _shape(slide, name: str):
    for sh in slide.shapes:
        if sh.name == name:
            return sh
    raise RuntimeError(f"missing shape {name!r}")


def _set(
    shape,
    text: str,
    *,
    pt: float,
    rgb: RGBColor,
    bold: bool | None = None,
    fill_height: bool = False,
) -> None:
    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True
    try:
        tf.auto_size = None
    except Exception:
        pass
    lines = text.split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        run = p.add_run()
        run.text = line
        run.font.size = Pt(pt)
        run.font.color.rgb = rgb
        if bold is not None:
            run.font.bold = bold
        p.space_before = Pt(0)
        p.space_after = Pt(2 if i < len(lines) - 1 else 0)
        # Stock template line spacing was ~1.5 → text overflowed card feet
        try:
            p.line_spacing = 1.05
        except Exception:
            pass
    if fill_height and len(lines) > 1:
        # Tall template cards leave a white foot if lines stay top-stacked
        box_h_pt = (shape.height / 914400.0) * 72.0
        line_h_pt = pt * 1.25
        used = 0.0
        w_in = max(shape.width / 914400.0, 1.0)
        cpl = max(8, int(w_in / (0.52 * pt / 72.0)))
        for line in lines:
            if not line.strip():
                used += line_h_pt * 0.4
            else:
                used += line_h_pt * max(1, (len(line) + cpl - 1) // cpl)
        # Use nearly full box; 0.88 left a visible white foot in PPT
        remain = max(0.0, box_h_pt * 0.97 - used)
        gap = remain / (len(lines) - 1)
        for p in tf.paragraphs[:-1]:
            p.space_after = Pt(max(2.0, gap))
        if tf.paragraphs:
            tf.paragraphs[-1].space_after = Pt(0)


def _fill_pic(slide, path: Path, prefer_left: float | None = None) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    slots = []
    for sh in list(slide.shapes):
        try:
            if sh.is_placeholder and sh.placeholder_format.type == PP_PLACEHOLDER.PICTURE:
                slots.append((sh.left, sh.top, sh.width, sh.height, sh))
        except Exception:
            continue
    if not slots:
        for sh in list(slide.shapes):
            try:
                if sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    slots.append((sh.left, sh.top, sh.width, sh.height, sh))
            except Exception:
                continue
    if not slots:
        raise RuntimeError("no picture slot")
    slots.sort(key=lambda x: (x[1], x[0]))
    if prefer_left is not None:
        slots.sort(key=lambda x: abs(x[0] / 914400 - prefer_left))
    left, top, w, h, ph = slots[0]
    try:
        ph._element.getparent().remove(ph._element)
    except Exception:
        pass
    # drop prior pictures in same area
    for sh in list(slide.shapes):
        try:
            if sh.shape_type == MSO_SHAPE_TYPE.PICTURE and abs(sh.left - left) < 200000:
                sh._element.getparent().remove(sh._element)
        except Exception:
            pass
    slide.shapes.add_picture(str(path), left, top, width=w, height=h)


def fill_15(slide) -> None:
    """01 Подробное описание решения — 5 строк."""
    _set(_shape(slide, "Заголовок 5"), "01 · Подробное описание решения", pt=PT_TITLE, rgb=ACCENT, bold=True)
    rows = [
        "Кандидат проходит тест навыка. Грейд считает сервер — резюме его не присваивает.",
        "Работодатель задаёт потребность и получает выдачу с основаниями «почему в списке».",
        "Статусы честные: подтверждено / нет / не проверено. «Не проверено» ≠ полный матч.",
        "Адресное приглашение с вилкой ₽ до переписки — без обязательной публикации вакансии.",
        "Контакты открываются только после согласия и только этой компании. Стенд живой.",
    ]
    for name, text in zip(
        ["Текст 7", "Текст 8", "Текст 9", "Текст 10", "Текст 11"], rows
    ):
        _set(_shape(slide, name), text, pt=PT_BODY, rgb=INK)


def fill_16(slide) -> None:
    """02 Маркетинговая часть — 4 колонки ценности."""
    title = _shape(slide, "Заголовок 13")
    title.top = int(0.48 * EMU)
    title.height = int(0.46 * EMU)
    title_txt = "Зачем это рынку"
    # Pink pill must fully cover the title glyphs
    try:
        pill = _shape(slide, "Скругленный прямоугольник 9")
        pill.width = int(5.80 * EMU)
        pill.height = int(0.72 * EMU)
        pill.top = int(0.35 * EMU)
        pill.left = int(0.38 * EMU)
        from pptx.oxml.ns import qn

        spPr = pill._element.spPr
        ln = spPr.find(qn("a:ln")) if spPr is not None else None
        if ln is not None:
            spPr.remove(ln)
    except RuntimeError:
        pass
    _set(title, title_txt, pt=PT_TITLE, rgb=WHITE, bold=True)
    # Compact stack: numbers → heads → bodies with fixed 1.05 line spacing (no fill_height)
    want_card_top = int(1.85 * EMU)
    num_top = int(2.05 * EMU)
    head_top = int(2.55 * EMU)
    body_top = int(3.10 * EMU)
    body_h = int(2.35 * EMU)  # room for wraps; card hugs below
    cards = [
        sh
        for sh in slide.shapes
        if "Скругленный прямоугольник" in (getattr(sh, "name", "") or "")
        and sh.width > 2.5 * EMU
        and sh.height > 2.5 * EMU
    ]
    for sh in cards:
        sh.top = want_card_top
    for name, top in (
        ("Текст 14", num_top),
        ("Текст 15", num_top),
        ("Текст 16", num_top),
        ("Текст 17", num_top),
        ("Текст 1", head_top),
        ("Текст 3", head_top),
        ("Текст 5", head_top),
        ("Текст 7", head_top),
        ("Текст 2", body_top),
        ("Текст 4", body_top),
        ("Текст 6", body_top),
        ("Текст 8", body_top),
    ):
        try:
            _shape(slide, name).top = top
        except RuntimeError:
            pass
    for bname in ("Текст 2", "Текст 4", "Текст 6", "Текст 8"):
        try:
            _shape(slide, bname).height = body_h
        except RuntimeError:
            pass
    if cards:
        card_h = (body_top + body_h + int(0.35 * EMU)) - want_card_top
        for sh in cards:
            sh.height = card_h
            from pptx.oxml.ns import qn

            spPr = sh._element.spPr
            ln = spPr.find(qn("a:ln")) if spPr is not None else None
            if ln is not None:
                spPr.remove(ln)
    nums = [("Текст 14", "01"), ("Текст 15", "02"), ("Текст 16", "03"), ("Текст 17", "04")]
    for name, num in nums:
        _set(_shape(slide, name), num, pt=PT_NUM, rgb=ACCENT, bold=True)
    heads = [
        ("Текст 1", "Для HR"),
        ("Текст 3", "Для кандидата"),
        ("Текст 5", "Для платформы"),
        ("Текст 7", "Для ФСП"),
    ]
    # Keep lines short so 2.5″ body width doesn't wrap into overflow
    bodies = [
        (
            "Текст 2",
            "Меньше ложных матчей.\n"
            "Доказательства теста в карточке.\n"
            "Честный статус, не «резюме».\n"
            "Вилка ₽ уже в приглашении.\n"
            "Контакты — после согласия.",
        ),
        (
            "Текст 4",
            "Навык говорит за вас.\n"
            "Грейд из теста, не из анкеты.\n"
            "Контакты открывает кандидат.\n"
            "Чужой HR связи не видит.\n"
            "Без обязательной вакансии.",
        ),
        (
            "Текст 6",
            "Своя платформа обратного найма.\n"
            "Не парсер внешних досок.\n"
            "Путь жив без боевого ФСП.\n"
            "Мок ФСП — по ТЗ, не дыра.\n"
            "HTTPS-стенд + открытый код.",
        ),
        (
            "Текст 8",
            "Достижения ФСП — в профиле.\n"
            "Грейд всё равно из теста.\n"
            "Демо ≠ боевой реестр.\n"
            "Честность статуса важнее.\n"
            "«Не проверено» ≠ матч.",
        ),
    ]
    for name, t in heads:
        _set(_shape(slide, name), t, pt=PT_H, rgb=ACCENT, bold=True)
    for name, t in bodies:
        _set(_shape(slide, name), t, pt=PT_BODY, rgb=INK, fill_height=False)


def fill_17(slide) -> None:
    """03 Бизнесовая составляющая — 3 колонки."""
    _set(_shape(slide, "Заголовок 13"), "03 · Бизнес-логика MVP", pt=PT_TITLE, rgb=WHITE, bold=True)
    for name, num in (("Текст 14", "01"), ("Текст 15", "02"), ("Текст 16", "03")):
        _set(_shape(slide, name), num, pt=PT_NUM, rgb=ACCENT, bold=True)
    _set(_shape(slide, "Текст 1"), "Кто платит вниманием", pt=PT_H, rgb=ACCENT, bold=True)
    _set(
        _shape(slide, "Текст 2"),
        "Работодатель ищет подтверждённую категорию и платит временем на оффер с вилкой — не на спам-рассылку.",
        pt=PT_BODY,
        rgb=INK,
    )
    _set(_shape(slide, "Текст 3"), "Что продаём как ценность", pt=PT_H, rgb=ACCENT, bold=True)
    _set(
        _shape(slide, "Текст 4"),
        "Доказуемый навык + честный статус + адресное согласие. Меньше переписок «вслепую».",
        pt=PT_BODY,
        rgb=INK,
    )
    _set(_shape(slide, "Текст 5"), "Пилот сейчас", pt=PT_H, rgb=ACCENT, bold=True)
    _set(
        _shape(slide, "Текст 6"),
        "Живой HTTPS-стенд и открытый код для экспертизы. Боевой ФСП/SMTP — следующий контур, не дыра ядра.",
        pt=PT_BODY,
        rgb=INK,
    )


def fill_18(slide) -> None:
    """05 Уникальность — 6 тезисов (двуколоночно)."""
    _set(_shape(slide, "Заголовок 13"), "05 · Чем мы не «ещё одна доска»", pt=PT_TITLE, rgb=WHITE, bold=True)
    items = [
        ("Текст 14", "01", "Текст 1", "Грейд ≠ резюме", "Текст 2", "Считает тест на сервере."),
        ("Текст 17", "02", "Текст 7", "Честные статусы", "Текст 8", "Нет подмены «почти» полным матчем."),
        ("Текст 15", "03", "Текст 3", "Обратный найм", "Текст 4", "HR находит категорию и шлёт оффер."),
        ("Текст 18", "04", "Текст 9", "Вилка до чата", "Текст 10", "₽ в приглашении, не после торга."),
        ("Текст 16", "05", "Текст 5", "Адресное согласие", "Текст 6", "Контакты только этой компании."),
        ("Текст 19", "06", "Текст 11", "Без ФСП путь жив", "Текст 12", "Мок по ТЗ + сценарий без привязки."),
    ]
    for num_sh, num, h_sh, h, b_sh, b in items:
        _set(_shape(slide, num_sh), num, pt=PT_NUM, rgb=ACCENT, bold=True)
        _set(_shape(slide, h_sh), h, pt=PT_H, rgb=ACCENT, bold=True)
        _set(_shape(slide, b_sh), b, pt=PT_BODY, rgb=INK)


def fill_20(slide) -> None:
    """04 Техническая проработка."""
    _set(_shape(slide, "Заголовок 13"), "04 · Техническая проработка", pt=PT_TITLE, rgb=WHITE, bold=True)
    _set(
        _shape(slide, "Текст 3"),
        "Стек: React + FastAPI + PostgreSQL — два кабинета на одном стенде.\n\n"
        "Грейд: серверная оценка теста; UI только отображает факт.\n\n"
        "Подбор: объяснимые статусы; фильтры по потребности.\n\n"
        "Права: контакты после принятия приглашения этой компанией.\n\n"
        "Проверка: HTTPS-стенд + открытый репозиторий.",
        pt=PT_BODY,
        rgb=INK,
    )
    rights = [
        ("Текст 4", "Тест навыка → результат в профиле"),
        ("Текст 5", "Подбор с основанием «почему в выдаче»"),
        ("Текст 6", "Приглашение с вилкой min–max ₽"),
        ("Текст 7", "Согласие → контакты у своего HR"),
        ("Текст 8", "Чужой работодатель контактов не видит"),
    ]
    for name, t in rights:
        _set(_shape(slide, name), t, pt=PT_BODY, rgb=INK)


def fill_25(slide) -> None:
    """Сквозной путь — 5 шагов слева направо (1↑ 2↓ 3↑ 4↓ 5↑ по сетке шаблона)."""
    title = _shape(slide, "Заголовок 13")
    title_txt = "Как проверить за один проход"
    title.top = int(0.48 * EMU)
    title.height = int(0.46 * EMU)
    title.width = int(9.40 * EMU)
    try:
        pill = _shape(slide, "Скругленный прямоугольник 11")
        pill.width = int(9.60 * EMU)
        pill.height = int(0.72 * EMU)
        pill.top = int(0.35 * EMU)
        pill.left = int(0.38 * EMU)
        from pptx.oxml.ns import qn

        spPr = pill._element.spPr
        ln = spPr.find(qn("a:ln")) if spPr is not None else None
        if ln is not None:
            spPr.remove(ln)
    except RuntimeError:
        pass
    _set(title, title_txt, pt=PT_TITLE, rgb=WHITE, bold=True)
    # Fixed card grid — upper: steps 1,3,5 ; lower: 2,4 — centers share X with pads
    upper_top = int(1.20 * EMU)
    lower_top = int(4.90 * EMU)
    card_h = int(2.30 * EMU)
    card_w = int(3.10 * EMU)
    head_h = int(0.40 * EMU)
    body_h = int(1.40 * EMU)
    body_dy = int(0.48 * EMU)
    # Absolute X for 5 steps (same order as template zigzag)
    step_lefts = [
        int(0.20 * EMU),   # 1 upper
        int(2.70 * EMU),   # 2 lower
        int(5.08 * EMU),   # 3 upper
        int(7.60 * EMU),   # 4 lower
        int(9.95 * EMU),   # 5 upper
    ]
    # Snap step cards by left order among wide rounded rects
    cards = [
        sh
        for sh in slide.shapes
        if "Скругленный прямоугольник" in (getattr(sh, "name", "") or "")
        and sh.width > 2.5 * EMU
        and sh.height > 1.2 * EMU
    ]
    cards.sort(key=lambda s: s.left)
    # Map cards to steps: template order by left is 1,2,3,4,5 ≈ upper/lower zigzag
    # Actual template lefts: 0.20, 2.70, 5.08, 7.60, 9.95
    for i, sh in enumerate(cards[:5]):
        sh.left = step_lefts[i]
        sh.width = card_w
        sh.height = card_h
        sh.top = upper_top if i % 2 == 0 else lower_top
        from pptx.oxml.ns import qn

        spPr = sh._element.spPr
        ln = spPr.find(qn("a:ln")) if spPr is not None else None
        if ln is not None:
            spPr.remove(ln)
    # Number pads centered under/over each step
    pad_h = int(0.70 * EMU)
    pad_w = int(0.96 * EMU)
    gap_mid = (upper_top + card_h + lower_top) // 2
    pad_top = gap_mid - pad_h // 2
    pads = [
        sh
        for sh in slide.shapes
        if "Скругленный прямоугольник" in (getattr(sh, "name", "") or "")
        and 0.7 * EMU < sh.width < 1.3 * EMU
    ]
    pads.sort(key=lambda s: s.left)
    pad_centers_x = []
    for i, sh in enumerate(pads[:5]):
        cx = step_lefts[i] + card_w // 2
        sh.left = cx - pad_w // 2
        sh.top = pad_top
        sh.width = pad_w
        sh.height = pad_h
        pad_centers_x.append(cx)
        from pptx.oxml.ns import qn

        spPr = sh._element.spPr
        ln = spPr.find(qn("a:ln")) if spPr is not None else None
        if ln is not None:
            spPr.remove(ln)
    # Horizontal connectors between consecutive pads
    h_lines = [
        sh
        for sh in slide.shapes
        if "соединительная линия" in (getattr(sh, "name", "") or "").lower()
        and sh.height < int(0.05 * EMU)
    ]
    h_lines.sort(key=lambda s: s.left)
    for i, sh in enumerate(h_lines):
        if i + 1 >= len(pad_centers_x):
            break
        x0 = pad_centers_x[i] + pad_w // 2
        x1 = pad_centers_x[i + 1] - pad_w // 2
        sh.left = x0
        sh.width = max(int(0.20 * EMU), x1 - x0)
        sh.top = gap_mid
        sh.height = 0
    # Vertical stubs: even steps (1,3,5) up; odd (2,4) down
    v_lines = [
        sh
        for sh in slide.shapes
        if "соединительная линия" in (getattr(sh, "name", "") or "").lower()
        and sh.width < int(0.05 * EMU)
    ]
    v_lines.sort(key=lambda s: s.left)
    for i, sh in enumerate(v_lines):
        if i >= len(pad_centers_x):
            break
        cx = pad_centers_x[i]
        sh.left = cx
        sh.width = 0
        if i % 2 == 0:
            sh.top = upper_top + card_h - int(0.05 * EMU)
            sh.height = pad_top - sh.top
        else:
            sh.top = pad_top + pad_h
            sh.height = lower_top + int(0.05 * EMU) - sh.top
    steps = [
        (
            "Текст 1",
            "1 · Тест",
            "Текст 2",
            "Кандидат проходит тест навыка.\n"
            "Результат сразу в профиле.\n"
            "Грейд не из резюме и не из самооценки.",
        ),
        (
            "Текст 7",
            "2 · Грейд",
            "Текст 8",
            "Сервер считает уровень.\n"
            "UI только показывает факт.\n"
            "Подделать грейд с клиента нельзя.",
        ),
        (
            "Текст 3",
            "3 · Подбор",
            "Текст 4",
            "HR задаёт потребность.\n"
            "В выдаче — основания и статусы.\n"
            "«Не проверено» ≠ полный матч.",
        ),
        (
            "Текст 9",
            "4 · Вилка ₽",
            "Текст 10",
            "Адресное приглашение с вилкой.\n"
            "До переписки, без обязательной вакансии.\n"
            "Вилка min–max уже в тексте оффера.",
        ),
        (
            "Текст 5",
            "5 · Согласие",
            "Текст 6",
            "После принятия — контакты своему HR.\n"
            "У другого работодателя контактов нет.\n"
            "Согласие — отдельный шаг, не «галочка в анкете».",
        ),
    ]
    # Text boxes: map by step index to absolute lefts (1,3,5 upper / 2,4 lower)
    text_map = [
        ("Текст 1", "Текст 2", 0),
        ("Текст 7", "Текст 8", 1),
        ("Текст 3", "Текст 4", 2),
        ("Текст 9", "Текст 10", 3),
        ("Текст 5", "Текст 6", 4),
    ]
    copy = {h: (ht, b, bt) for h, ht, b, bt in steps}
    for hname, bname, idx in text_map:
        hs, bs = _shape(slide, hname), _shape(slide, bname)
        left = step_lefts[idx] + int(0.18 * EMU)
        tw = card_w - int(0.36 * EMU)
        top_card = upper_top if idx % 2 == 0 else lower_top
        hs.left = left
        bs.left = left
        hs.width = tw
        bs.width = tw
        hs.top = top_card + int(0.10 * EMU)
        bs.top = top_card + body_dy
        hs.height = head_h
        bs.height = body_h
        ht, _, bt = copy[hname]
        _set(hs, ht, pt=PT_H, rgb=ACCENT, bold=True)
        _set(bs, bt, pt=PT_BODY, rgb=INK, fill_height=False)


def _fill_named_pic(slide, shape_name: str, path: Path) -> None:
    sh = _shape(slide, shape_name)
    left, top, w, h = sh.left, sh.top, sh.width, sh.height
    sh._element.getparent().remove(sh._element)
    slide.shapes.add_picture(str(path), left, top, width=w, height=h)


def fill_19(slide) -> None:
    """Демо-кадры стенда — плотный текст + 3 экрана без пустыни в боксе."""
    _set(_shape(slide, "Заголовок 13"), "Экран работодателя", pt=PT_TITLE, rgb=WHITE, bold=True)
    # Shrink the oversized caption box so it doesn't leave a white desert
    cap = _shape(slide, "Текст 5")
    cap.height = int(1.35 * 914400)
    _set(
        cap,
        "Живой кабинет HR на стенде.\n"
        "Подбор по компетенциям → карточки с тестами и статусами → "
        "приглашение с вилкой ₽ → контакты только после согласия.\n"
        "https://85-137-26-131.sslip.io/",
        pt=PT_BODY,
        rgb=INK,
    )
    # Re-runs rename placeholders → Picture N; always clear pics and place by geometry
    for sh in list(slide.shapes):
        try:
            if sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
                sh._element.getparent().remove(sh._element)
        except Exception:
            pass
        try:
            if sh.is_placeholder and sh.placeholder_format.type == PP_PLACEHOLDER.PICTURE:
                sh._element.getparent().remove(sh._element)
        except Exception:
            pass
    emu = 914400
    for path, L, T, W, H in (
        (ASSETS / "demo_desktop_search.png", 8.14, 1.11, 4.82, 3.37),
        (ASSETS / "demo_desktop_overview.png", 0.38, 3.53, 7.44, 3.26),
        (ASSETS / "demo_desktop_invites.png", 8.14, 4.80, 4.82, 1.98),
    ):
        slide.shapes.add_picture(
            str(path), int(L * emu), int(T * emu), width=int(W * emu), height=int(H * emu)
        )

def fill_26(slide) -> None:
    """Три якоря демо."""
    _set(_shape(slide, "Заголовок 13"), "Что увидеть за 2 минуты", pt=PT_TITLE, rgb=WHITE, bold=True)
    _set(_shape(slide, "Текст 3"), "Кабинет HR: поиск по компетенциям и доказательствам.", pt=PT_BODY, rgb=INK)
    _set(_shape(slide, "Текст 4"), "Приглашение с вилкой ₽ до переписки.", pt=PT_BODY, rgb=INK)
    _set(_shape(slide, "Текст 5"), "Контакты только после принятия этой компанией.", pt=PT_BODY, rgb=INK)
    try:
        _fill_pic(slide, ASSETS / "demo_desktop_overview.png", prefer_left=4.0)
    except Exception as e:
        print(f"  slide26 pic skip: {e}")


def main() -> None:
    if not PPTX.exists():
        raise SystemExit(f"missing {PPTX}")
    prs = Presentation(str(PPTX))
    # Ship only 16 + 25 in SUBMISSION (sparse template fills dropped)
    fill_16(prs.slides[15])
    print("filled 16 · рынок")
    fill_25(prs.slides[24])
    print("filled 25 · путь")
    prs.save(str(PPTX))
    print("saved", PPTX)


if __name__ == "__main__":
    main()

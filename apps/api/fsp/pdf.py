from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from .bank import SPECS, SKILLS


def profile_pdf(profile):
    if "DejaVu" not in pdfmetrics.getRegisteredFontNames():
        font = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        pdfmetrics.registerFont(TTFont("DejaVu", str(font)))
    b = BytesIO()
    style = ParagraphStyle(
        "body", fontName="DejaVu", fontSize=10, leading=15, spaceAfter=10
    )
    title = ParagraphStyle(
        "title",
        parent=style,
        fontSize=20,
        leading=26,
        textColor=colors.HexColor("#520978"),
    )
    story = [Paragraph("ФСП · Профиль компетенций", title), Spacer(1, 12)]
    lines = [
        profile["display_name"],
        SPECS[profile["specialization"]],
        "Подтверждённый уровень: " + (profile["verified_grade"] or "не подтверждён"),
        "Навыки со слов кандидата: " + ", ".join(SKILLS[s] for s in profile["skills"]),
        "Контакты: "
        + (
            "раскрыты по согласию"
            if profile["contacts"]
            else "закрыты до принятия приглашения"
        ),
    ]
    if profile["contacts"]:
        lines += [f"{k}: {v}" for k, v in profile["contacts"].items()]
        lines += [
            profile.get("roles", ""),
            profile.get("soft_skills", ""),
            profile.get("about", ""),
        ]
    for e in profile["evidence"]:
        lines.append(
            f"{SKILLS[e['skill']]}: {'подтверждено' if e['state']=='met' else 'критерий теста не выполнен'}; {e['correct']}/{e['total']}; методика {e['version']}; {e['date']}"
        )
    if profile["demo"]:
        lines.append("Демонстрационный профиль. Данные и результаты синтетические.")
    if profile["achievements"]:
        lines.append("Достижения: демонстрационный провайдер ФСП, не реальный реестр.")
    for line in lines:
        story.append(Paragraph(escape(str(line)).replace("\n", "<br/>"), style))
    SimpleDocTemplate(
        b,
        title="Профиль компетенций ФСП",
        author="ФСП MVP",
        leftMargin=44,
        rightMargin=44,
        topMargin=40,
        bottomMargin=40,
    ).build(story)
    return b.getvalue()

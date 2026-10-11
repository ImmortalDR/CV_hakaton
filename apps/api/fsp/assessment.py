"""One policy for assessment previews and locked server-side start checks."""
from datetime import timedelta

from . import bank


def configured_rubric(specialization, grade):
    # generate() emits two variants per configured family. Verify this contract
    # for every category in tests; do not infer new tests from an old attempt.
    families = bank.BLUEPRINT[specialization, grade]
    core = "python" if specialization == "python" else "sql"
    return bank.rubric() | {
        "question_count": 2 * len(families),
        "core_total": 2 * sum(bank.FAMILY_SKILL[f] == core for f in families),
    }


def stored_rubric(attempt):
    core = "python" if attempt.specialization == "python" else "sql"
    return bank.rubric(attempt.version) | {
        "question_count": len(attempt.questions),
        "core_total": sum(q["skill"] == core for q in attempt.questions),
    }


def availability(profile, grade, attempts, at):
    reasons = []
    def block(code, message, until=None):
        reasons.append({"code": code, "message": message, "until": until})

    if not profile.name or not profile.processing:
        block("profile", "Заполните профиль и дайте согласие на обработку данных.")
    active = next((a for a in attempts if a.status == "active" and a.expires_at > at), None)
    if active:
        block("active", "Сначала завершите текущую попытку.", active.expires_at)
    if profile.verified_grade and grade != profile.verified_grade:
        until = profile.grade_changed_at + timedelta(days=90)
        if at < until:
            block("grade_change", "Смена подтверждённого уровня — через 90 дней после последнего изменения.", until)
    previous = max((a.created_at for a in attempts if a.grade == grade and a.specialization == profile.specialization), default=None)
    if previous and at < previous + timedelta(hours=24):
        block("retake", "Повторный тест этого уровня — через 24 часа от начала предыдущей попытки.", previous + timedelta(hours=24))
    dates = [r["until"] for r in reasons if r["until"]]
    return {
        "grade": grade, "available": not reasons, "reasons": reasons,
        "next_available_at": max(dates) if dates and not any(r["until"] is None for r in reasons) else None,
        "rubric": configured_rubric(profile.specialization, grade),
    }

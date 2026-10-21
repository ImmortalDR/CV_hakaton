from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def count_label(value: int, one: str, few: str, many: str) -> str:
    n = abs(value)
    word = many if 11 <= n % 100 <= 14 else one if n % 10 == 1 else few if 2 <= n % 10 <= 4 else many
    return f"{value} {word}"


def readable_date(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ZoneInfo("Europe/Moscow")).strftime("%d.%m.%Y %H:%M") + " МСК (UTC+03:00)"

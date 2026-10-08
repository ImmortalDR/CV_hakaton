"""Original versioned task families; no submitted code is executed."""

import hashlib
import json
import random
from collections import Counter
from decimal import Decimal, InvalidOperation

VERSION = "1.2.0"
SPECS = {"python": "Python / бэкенд", "data": "Аналитика данных / SQL"}
GRADES = ["Junior", "Middle", "Senior"]
SKILLS = {
    "python": "Python",
    "testing": "Тестирование",
    "http": "HTTP / API",
    "sql": "SQL",
    "statistics": "Статистика",
    "transactions": "Транзакции",
    "docker": "Docker",
    "react": "React",
}
BLUEPRINT = {
    ("python", "Junior"): ["py_filter", "py_boundary"],
    ("python", "Middle"): ["py_alias", "http_keys"],
    ("python", "Senior"): ["py_dag", "http_backoff"],
    ("data", "Junior"): ["sql_where", "stats_median"],
    ("data", "Middle"): ["sql_join", "stats_weighted"],
    ("data", "Senior"): ["sql_rank", "tx_snapshot"],
}
FAMILY_SKILL = dict(
    zip(
        [
            "py_filter",
            "py_boundary",
            "py_alias",
            "http_keys",
            "py_dag",
            "http_backoff",
            "sql_where",
            "stats_median",
            "sql_join",
            "stats_weighted",
            "sql_rank",
            "tx_snapshot",
        ],
        [
            "python",
            "testing",
            "python",
            "http",
            "python",
            "http",
            "sql",
            "statistics",
            "sql",
            "statistics",
            "sql",
            "transactions",
        ],
    )
)


def question(family, rng):
    a = rng.randint(2, 9)
    b = rng.randint(2, 8)
    values = [rng.randint(1, 20) for _ in range(7)]
    p = {"a": a, "b": b, "values": values}
    if family == "py_filter":
        text = f"Какое число выведет Python?\nxs = {values}\nprint(sum(x for x in xs if x % {a} == 0))"
        answer = sum(x for x in values if x % a == 0)
        why = "Отбираем числа, делящиеся без остатка, затем складываем их."
    elif family == "py_boundary":
        values = [rng.randint(a - 2, a + b + 2) for _ in range(7)]
        p["values"] = values
        text = f"Спецификация: допустимы {a} ≤ x ≤ {a+b}. Реализация: {a} < x < {a+b}.\nВходы тестов: {values}. Сколько тестов обнаружат ошибку?"
        answer = sum(x in (a, a + b) for x in values)
        why = "Каждый вход, равный одной из включённых границ, обнаруживает расхождение; повторные входы считаются отдельно."
    elif family == "py_alias":
        text = f"Какое число выведет Python?\nrows = [[{a}]] * {b}\nrows[0].append({a+b})\nprint(sum(sum(row) for row in rows))"
        answer = b * (2 * a + b)
        why = "Умножение списка копирует ссылки: все строки указывают на один вложенный список."
    elif family == "http_keys":
        keys = [rng.choice(["alpha", "beta", "gamma", "delta"]) for _ in range(8)]
        p["keys"] = keys
        text = f"API списывает {a} ₽ за запрос. Одинаковый Idempotency-Key выполняется только один раз; все записи успешно сохранены атомарно.\nПоследовательность ключей: {keys}. Сколько рублей спишется всего?"
        answer = a * len(set(keys))
        why = "Списания считаются по уникальным ключам, повторы возвращают сохранённый результат."
    elif family == "py_dag":
        c = rng.randint(2, 12)
        p["c"] = c
        text = f"Планировщик Python запускает A ({a} с) и B ({b} с) параллельно. C ({c} с) ждёт A. D ({a+b} с) ждёт B и C.\nРабочих потоков достаточно, накладных расходов нет. Через сколько секунд завершится D?"
        answer = max(a + c, b) + a + b
        why = "D стартует после более длинной из ветвей B и A→C. Добавляем его длительность."
    elif family == "http_backoff":
        n = rng.randint(3, 5)
        p["n"] = n
        text = f"Клиент делает ровно {n} попытки HTTP. Каждая занимает {b} с. После неудачной попытки i (считая с 1) пауза {a} × 2^(i−1) с.\nПоследняя попытка успешна; паузы после неё нет. Сколько секунд прошло всего?"
        answer = n * b + a * (2 ** (n - 1) - 1)
        why = (
            "Суммируем время всех запросов и геометрическую прогрессию пауз между ними."
        )
    elif family == "sql_where":
        text = f"Таблица sales(amount) содержит строки {values}.\nКаков результат SELECT COALESCE(SUM(amount),0) FROM sales WHERE amount >= {a+b}?"
        answer = sum(x for x in values if x >= a + b)
        why = "WHERE сохраняет строки с включённой нижней границей, SUM складывает значения."
    elif family == "stats_median":
        text = f"Время ответа API (мс): {values}. Чему равна медиана этой выборки?"
        answer = sorted(values)[3]
        why = "После сортировки семи наблюдений медиана — четвёртое значение."
    elif family == "sql_join":
        orders = [rng.choice([1, 2, 3, 4]) for _ in range(6)]
        p["orders"] = orders
        text = f"customers(id): 1,2,3,4,5. orders(customer_id): {orders}. Все order.id заполнены.\nСколько вернёт SELECT COUNT(*) FROM customers c LEFT JOIN orders o ON c.id=o.customer_id WHERE o.id IS NULL?"
        answer = 5 - len(set(orders))
        why = "LEFT JOIN сохраняет клиентов без заказов; WHERE выбирает именно эти строки."
    elif family == "stats_weighted":
        text = f"Группа A: {a*10} конверсий из {a*100} посещений. Группа B: {b*30} конверсий из {b*100} посещений.\nОбщая конверсия в процентах? Округлите до двух знаков."
        answer = round((a * 10 + b * 30) / (a + b), 2)
        why = "Складываем конверсии и посещения отдельно. Среднее процентов без весов неверно."
    elif family == "sql_rank":
        target = values[0]
        p["target"] = target
        text = f"Таблица scores(value): {values}.\nКакой DENSE_RANK() OVER (ORDER BY value DESC) у строки со значением {target}?"
        answer = 1 + len({x for x in values if x > target})
        why = "Плотный ранг равен единице плюс число различных значений строго выше текущего."
    else:
        text = f"Баланс равен {a*100}. T1 и T2 читают его одновременно. T1 прибавляет {a}, T2 прибавляет {b}; обе записывают рассчитанное абсолютное значение. T1 пишет первой, затем T2 (без проверки конфликтов).\nНа сколько итог меньше суммы при последовательном выполнении обеих транзакций?"
        answer = a
        why = "T2 перезаписывает прибавку T1 на основе старого снимка: потеряно изменение T1."
    return {
        "family": family,
        "skill": FAMILY_SKILL[family],
        "text": text,
        "answer": str(answer),
        "explanation": why,
        "params": p,
    }


def generate(specialization, grade, seed):
    rng = random.Random(str(seed))
    qs = [
        question(f, rng) for f in BLUEPRINT[(specialization, grade)] for _ in range(2)
    ]
    rng.shuffle(qs)
    for i, q in enumerate(qs):
        q["id"] = str(i + 1)
    return qs


def fingerprint(questions):
    return hashlib.sha256(
        json.dumps([q["text"] for q in questions], ensure_ascii=False).encode()
    ).hexdigest()


def grade_answers(questions, answers, version=VERSION):
    details = []
    counts, totals = Counter(), Counter()
    for q in questions:
        try:
            value = Decimal(str(answers.get(q["id"], "")).strip().replace(",", "."))
            expected = Decimal(q["answer"])
            correct = value.is_finite() and abs(value - expected) <= Decimal("0.005")
        except (InvalidOperation, ValueError):
            correct = False
        counts[q["skill"]] += int(correct)
        totals[q["skill"]] += 1
        details.append(
            {
                "id": q["id"],
                "correct": bool(correct),
                "expected": q["answer"],
                "explanation": q["explanation"],
            }
        )
    score = sum(counts.values()) * 100 // len(questions)
    # v1.2 requires proof of the specialization's core skill. A high total in
    # supporting topics alone must not confirm Python/SQL competence. Stored
    # attempts retain their original rubric, including ones active at upgrade.
    core = "python" if "python" in totals else "sql"
    core_met = counts[core] == totals[core] and totals[core] > 0
    passed = score >= 75 and (version in {"1.0.0", "1.1.0"} or core_met)
    return {
        "score": score,
        "passed": passed,
        "threshold": 75,
        "details": details,
        "skills": [
            {
                "skill": s,
                "correct": counts[s],
                "total": n,
                "state": "met" if counts[s] / n >= 0.75 else "unmet",
            }
            for s, n in totals.items()
        ],
    }

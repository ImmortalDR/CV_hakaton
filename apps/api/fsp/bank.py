"""Original versioned task families; no submitted code is executed."""

import hashlib
import json
import random
from collections import Counter
from decimal import Decimal, InvalidOperation

VERSION = "2.0.0"
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
LEGACY_BLUEPRINT = {
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


EXTRA_BLUEPRINT = {
    ("python", "Junior"): ["py_accumulate", "testing_mutation"],
    ("python", "Middle"): ["py_default", "http_quota"],
    ("python", "Senior"): ["py_lru", "http_retry_budget"],
    ("data", "Junior"): ["sql_null_sum", "stats_mean_drop"],
    ("data", "Middle"): ["sql_group", "stats_conditional"],
    ("data", "Senior"): ["sql_window", "tx_optimistic"],
}
BLUEPRINT = {key: families + EXTRA_BLUEPRINT[key] for key, families in LEGACY_BLUEPRINT.items()}
FAMILY_SKILL.update({
    "py_accumulate": "python", "testing_mutation": "testing",
    "py_default": "python", "http_quota": "http",
    "py_lru": "python", "http_retry_budget": "http",
    "sql_null_sum": "sql", "stats_mean_drop": "statistics",
    "sql_group": "sql", "stats_conditional": "statistics",
    "sql_window": "sql", "tx_optimistic": "transactions",
})
SUPPORTED_VERSIONS = {"1.0.0", "1.1.0", "1.2.0", VERSION}


def rubric(version=VERSION):
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(f"Unsupported bank version: {version}")
    return {
        "question_count": 8 if version == VERSION else 4,
        "minutes": 30,
        "threshold": 75,
        "core_min_correct": 3 if version == VERSION else 2 if version == "1.2.0" else 0,
        "core_total": 4 if version == VERSION else 2,
    }


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
    elif family == "tx_snapshot":
        text = f"Баланс равен {a*100}. T1 и T2 читают его одновременно. T1 прибавляет {a}, T2 прибавляет {b}; обе записывают рассчитанное абсолютное значение. T1 пишет первой, затем T2 (без проверки конфликтов).\nНа сколько итог меньше суммы при последовательном выполнении обеих транзакций?"
        answer = a
        why = "T2 перезаписывает прибавку T1 на основе старого снимка: потеряно изменение T1."
    elif family == "py_accumulate":
        text = f"Какое число выведет Python?\nxs = {values}\ntotal = {a}\nfor i, x in enumerate(xs):\n    total += x if i % 2 == 0 else -x\nprint(total)"
        answer = a + sum(values[::2]) - sum(values[1::2])
        why = "Индексы начинаются с нуля: прибавляем элементы с чётными индексами, вычитаем с нечётными."
    elif family == "testing_mutation":
        xs = [rng.randint(-12, 12) for _ in range(8)]
        p["inputs"] = xs
        text = f"Требование: функция возвращает abs(x). Реализация возвращает x без изменений.\nВходы тестов: {xs}. Каждый тест сравнивает результат с требованием. Сколько тестов обнаружат дефект? Повторы считаются отдельно."
        answer = sum(x < 0 for x in xs)
        why = "Реализация расходится с модулем только для отрицательных входов; ноль не обнаруживает дефект."
    elif family == "py_default":
        c = rng.randint(10, 90)
        p["c"] = c
        text = f"Какое число выведет Python?\ndef add(value, bucket=[]):\n    bucket.append(value)\n    return sum(bucket)\nadd({a})\nadd({b}, [])\nprint(add({c}))"
        answer = a + c
        why = "Аргумент по умолчанию общий для первого и третьего вызова; второй получает отдельный список."
    elif family == "http_quota":
        times = sorted(rng.randrange(4 * b) for _ in range(12))
        p["times"] = times
        text = f"API допускает не более {a} запросов в каждом фиксированном окне {b} секунд: [0,{b}), [{b},{2*b}) и далее. Отклонённый запрос не расходует лимит.\nВремена запросов в секундах: {times}. Запросы обрабатываются по порядку, одновременные — в указанном порядке. Сколько запросов будет принято?"
        answer = sum(min(a, n) for n in Counter(t // b for t in times).values())
        why = "Считаем запросы отдельно в каждом полуоткрытом окне и ограничиваем число принятых лимитом."
    elif family == "py_lru":
        capacity = rng.randint(2, 4)
        keys = [rng.randint(1, 6) for _ in range(10)]
        p.update(capacity=capacity, keys=keys)
        text = f"Пустой LRU-кеш Python хранит {capacity} ключа. Попадание обновляет давность; при заполнении вытесняется самый давно использованный ключ.\nОбращения: {keys}. Каждый промах вызывает запрос к БД длительностью {a} мс, попадание — 0 мс. Обращения последовательны. Сколько миллисекунд суммарно займут запросы к БД?"
        cache, misses = [], 0
        for key in keys:
            if key in cache:
                cache.remove(key)
            else:
                misses += 1
                if len(cache) == capacity:
                    cache.pop(0)
            cache.append(key)
        answer = misses * a
        why = "Обновляем порядок LRU после каждого обращения; только промахи добавляют время БД."
    elif family == "http_retry_budget":
        streams = [[rng.choice([200, 400, 503]) for _ in range(3)] for _ in range(4)]
        p["streams"] = streams
        text = f"Клиент выполняет четыре операции последовательно. Для каждой максимум 3 попытки, повтор разрешён только после статуса 503; после 200 или 400 операция заканчивается. Паузы нет, каждая попытка длится {b} мс.\nВозможные ответы по операциям: {streams}. Неиспользованные ответы игнорируются. Сколько миллисекунд займут все операции?"
        count = 0
        for stream in streams:
            for status in stream:
                count += 1
                if status != 503:
                    break
        answer = b * count
        why = "Для каждой операции считаем попытки до первого ответа, отличного от 503, но не более трёх."
    elif family == "sql_null_sum":
        xs = [None if i in (1, 4) else v for i, v in enumerate(values)]
        p["nullable"] = xs
        rendered = ", ".join("NULL" if x is None else str(x) for x in xs)
        text = f"Таблица payments(amount) содержит строки: {rendered}.\nЧему равен SELECT SUM(COALESCE(amount, {a})) FROM payments?"
        answer = sum(a if x is None else x for x in xs)
        why = "COALESCE заменяет каждое NULL указанным числом до суммирования; остальные значения сохраняются."
    elif family == "stats_mean_drop":
        index = rng.randrange(len(values))
        p["drop_index"] = index
        text = f"Замеры времени (мс): {values}. Известно, что замер номер {index+1} ошибочен (нумерация с 1).\nЧему равно среднее арифметическое после удаления только этого замера? Округлите до двух знаков."
        answer = round((sum(values) - values[index]) / (len(values)-1), 2)
        why = "Исключаем одно наблюдение по номеру, даже если такое же значение встречается ещё раз, и делим на оставшееся число наблюдений."
    elif family == "sql_group":
        rows = [[i % 3 + 1, rng.randint(5, 40)] for i in range(9)]
        threshold = rng.randint(25, 65)
        p.update(rows=rows, threshold=threshold)
        totals = Counter()
        for team, amount in rows:
            totals[team] += amount
        text = f"Таблица sales(team, amount): {rows} (каждая пара — строка).\nЧему равен SELECT COALESCE(SUM(total),0) FROM (SELECT team, SUM(amount) AS total FROM sales GROUP BY team HAVING SUM(amount) >= {threshold}) s?"
        answer = sum(n for n in totals.values() if n >= threshold)
        why = "Сначала суммируем продажи по команде, затем HAVING отбирает группы, после чего складываем суммы выбранных групп."
    elif family == "stats_conditional":
        returning = rng.randint(20, 80)
        bought = rng.randint(1, returning-1)
        new = rng.randint(20, 80)
        p.update(returning=returning, bought=bought, new=new)
        text = f"За день пришли {returning} вернувшихся и {new} новых пользователей. Из вернувшихся покупку совершили {bought}.\nКакой процент вернувшихся совершил покупку? Округлите до двух знаков."
        answer = round(100 * bought / returning, 2)
        why = "Условная доля считается только среди вернувшихся; новые пользователи не входят в знаменатель."
    elif family == "sql_window":
        rows = [[i+1, i % 2 + 1, rng.randint(5, 40)] for i in range(8)]
        target = rng.randint(4, 8)
        p.update(rows=rows, target_id=target)
        team = rows[target-1][1]
        text = f"Таблица events(id, team, amount): {rows}. id уникален.\nЗапрос: SELECT id, SUM(amount) OVER (PARTITION BY team ORDER BY id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS total FROM events.\nКаково total у строки id={target}?"
        answer = sum(amount for ident, group, amount in rows if group == team and ident <= target)
        why = "Суммируем текущую и предыдущие строки только своей команды; фильтрация искомой строки делается после оконного расчёта."
    elif family == "tx_optimistic":
        changes = [[rng.randint(0, 3), rng.randint(3, 30)] for _ in range(8)]
        p["changes"] = changes
        balance, version = a * 100, 0
        for expected, delta in changes:
            if expected == version:
                balance += delta
                version += 1
        text = f"Начальный balance={a*100}, version=0. Последовательно выполняются UPDATE: balance=balance+delta, version=version+1 WHERE version=expected. Обновление атомарно; при несовпадении версии ничего не меняется, повторов нет.\nПары [expected, delta]: {changes}. Каков итоговый balance?"
        answer = balance
        why = "Применяем только обновления, чья ожидаемая версия совпадает с текущей; успешное обновление увеличивает версию на один."
    else:
        raise ValueError(f"Unknown question family: {family}")
    return {
        "family": family,
        "skill": FAMILY_SKILL[family],
        "text": text,
        "answer": str(answer),
        "explanation": why,
        "params": p,
    }


def generate(specialization, grade, seed, version=VERSION):
    rubric(version)
    blueprint = BLUEPRINT if version == VERSION else LEGACY_BLUEPRINT
    rng = random.Random(str(seed))
    qs = [
        question(f, rng) for f in blueprint[(specialization, grade)] for _ in range(2)
    ]
    if version == "1.0.0":
        raise ValueError("Generation of 1.0.0 is unavailable; use stored questions for replay")
    if version in {"1.2.0", VERSION}:
        rng.shuffle(qs)
    for i, q in enumerate(qs):
        q["id"] = str(i + 1)
    return qs


def fingerprint(questions):
    return hashlib.sha256(
        json.dumps([q["text"] for q in questions], ensure_ascii=False).encode()
    ).hexdigest()


def grade_answers(questions, answers, version=VERSION):
    policy = rubric(version)
    if not questions:
        raise ValueError("An assessment must contain questions")
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
    score = sum(counts.values()) * 100 / len(questions)
    # Versioned rubrics require proof of the specialization's core skill. A high total in
    # supporting topics alone must not confirm Python/SQL competence. Stored
    # attempts retain their original rubric, including ones active at upgrade.
    core = "python" if "python" in totals else "sql"
    core_met = counts[core] >= policy["core_min_correct"] and totals[core] > 0
    passed = score >= policy["threshold"] and (policy["core_min_correct"] == 0 or core_met)
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

"""Independent reference solvers. Never import the production generator/grader.

SQL is executed in an isolated in-memory SQLite database; Python tasks are
simulated step by step. Parameters, not the stored answer, are the input.
"""

import sqlite3
import statistics


def solve(question):
    family, p = question["family"], question["params"]
    a, b, values = p["a"], p["b"], p["values"]
    if family == "py_filter":
        selected = filter(lambda x: divmod(x, a)[1] == 0, values)
        return sum(selected)
    if family == "py_boundary":
        expected = [a <= x <= a + b for x in values]
        actual = [a < x < a + b for x in values]
        return sum(x != y for x, y in zip(expected, actual))
    if family == "py_alias":
        rows = [[a]] * b
        rows[0].append(a + b)
        result = 0
        for row in rows:
            for value in row:
                result += value
        return result
    if family == "http_keys":
        done, balance = {}, 0
        for key in p["keys"]:
            if key not in done:
                balance += a
                done[key] = True
        return balance
    if family == "py_dag":
        remaining = {"A": a, "B": b, "C": p["c"], "D": a + b}
        deps = {"A": [], "B": [], "C": ["A"], "D": ["B", "C"]}
        completed, clock = set(), 0
        while "D" not in completed:
            running = [
                k for k in remaining if k not in completed and set(deps[k]) <= completed
            ]
            clock += 1
            for k in running:
                remaining[k] -= 1
            completed.update(k for k in running if remaining[k] == 0)
        return clock
    if family == "http_backoff":
        clock, pause = 0, a
        for i in range(p["n"]):
            clock += b
            if i + 1 != p["n"]:
                clock += pause
                pause *= 2
        return clock
    if family == "stats_median":
        return statistics.median(values)
    if family == "stats_weighted":
        converted = [True] * (a * 10 + b * 30)
        visits = a * 100 + b * 100
        return round(100 * len(converted) / visits, 2)
    if family == "tx_snapshot":
        original = a * 100
        sequential = original + a + b
        read1, read2 = original, original
        balance = read1 + a
        balance = read2 + b
        return sequential - balance
    with sqlite3.connect(":memory:") as db:
        if family == "sql_where":
            db.execute("CREATE TABLE sales(amount INTEGER)")
            db.executemany("INSERT INTO sales VALUES (?)", [(x,) for x in values])
            return db.execute(
                "SELECT COALESCE(SUM(amount),0) FROM sales WHERE amount >= ?", (a + b,)
            ).fetchone()[0]
        if family == "sql_join":
            db.execute("CREATE TABLE customers(id INTEGER)")
            db.execute("CREATE TABLE orders(id INTEGER, customer_id INTEGER)")
            db.executemany(
                "INSERT INTO customers VALUES (?)", [(x,) for x in range(1, 6)]
            )
            db.executemany(
                "INSERT INTO orders VALUES (?, ?)", list(enumerate(p["orders"], 1))
            )
            return db.execute(
                "SELECT COUNT(*) FROM customers c LEFT JOIN orders o ON c.id=o.customer_id WHERE o.id IS NULL"
            ).fetchone()[0]
        if family == "sql_rank":
            db.execute("CREATE TABLE scores(value INTEGER)")
            db.executemany("INSERT INTO scores VALUES (?)", [(x,) for x in values])
            rows = db.execute(
                "SELECT value, DENSE_RANK() OVER (ORDER BY value DESC) FROM scores"
            ).fetchall()
            return next(rank for value, rank in rows if value == p["target"])
    raise ValueError(f"Unknown family: {family}")

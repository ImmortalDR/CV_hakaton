"""Replaceable boundary for external sports evidence; never assigns a grade."""

from typing import Protocol


class Provider(Protocol):
    def achievements(self, external_identity: str) -> list[dict]: ...


class DemoProvider:
    """Explicit simulation; identities are selected examples, not credentials."""

    def achievements(self, external_identity):
        if external_identity not in ("demo-winner", "demo-participant"):
            raise ValueError("Unknown demonstration identity")
        winner = external_identity == "demo-winner"
        return [
            {
                "provider": "demo_fsp",
                "title": "Демонстрационный турнир по программированию",
                "result": "Победитель" if winner else "Участник",
                "points": 3 if winner else 1,
                "date": "2026-09-01",
                "verification": "simulated",
            }
        ]

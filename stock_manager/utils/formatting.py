from __future__ import annotations

from decimal import Decimal


def currency(value: object) -> str:
    try:
        return f"NT$ {Decimal(str(value or 0)):,.0f}"
    except Exception:
        return "NT$ 0"


def number(value: object, digits: int = 2) -> str:
    try:
        return f"{Decimal(str(value or 0)):,.{digits}f}"
    except Exception:
        return "0"


def percent(value: object, ratio: bool = False) -> str:
    try:
        val = Decimal(str(value or 0)) * (100 if ratio else 1)
        return f"{val:+.2f}%"
    except Exception:
        return "0.00%"


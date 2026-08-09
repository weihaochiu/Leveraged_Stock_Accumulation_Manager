from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from stock_manager.database import PortfolioRepository
from stock_manager.domain import dec


class PortfolioService:
    def __init__(self, repository: PortfolioRepository):
        self.repository = repository

    def master_rows(self, filters: dict | None = None) -> list[dict]:
        rows = self.repository.master_rows()
        filters = filters or {}
        query = (filters.get("query") or "").strip().lower()
        if query:
            rows = [r for r in rows if query in f"{r['id']} {r['symbol']} {r['security_name']} {r.get('broker_name','')}".lower()]
        if filters.get("security_id"):
            rows = [r for r in rows if r["security_id"] == filters["security_id"]]
        if filters.get("broker_account_id"):
            rows = [r for r in rows if r["broker_account_id"] == filters["broker_account_id"]]
        if filters.get("funding_type"):
            rows = [r for r in rows if r["funding_type"] == filters["funding_type"]]
        if filters.get("strategy_status"):
            rows = [r for r in rows if r["strategy_status"].value == filters["strategy_status"]]
        return rows

    def stock_summary(self) -> list[dict]:
        groups: dict[int, dict] = {}
        for row in self.repository.master_rows():
            group = groups.setdefault(row["security_id"], {
                "security_id": row["security_id"], "symbol": row["symbol"], "name": row["security_name"],
                "remaining_shares": 0, "market_value": Decimal("0"), "lot_count": 0,
                "free_shares": 0, "free_share_value": Decimal("0"), "capital_at_risk": Decimal("0"),
            })
            group["remaining_shares"] += row["remaining_shares"]
            group["market_value"] += row["market_value"]
            group["lot_count"] += 1
            group["free_shares"] += row["free_shares"]
            group["free_share_value"] += row["free_share_value"]
            group["capital_at_risk"] += row["remaining_capital_at_risk"]
        return sorted(groups.values(), key=lambda r: r["symbol"])

    def capital_at_risk_by_stock(self) -> dict[str, float]:
        result: dict[str, Decimal] = defaultdict(Decimal)
        for row in self.repository.master_rows():
            result[f"{row['symbol']} {row['security_name']}"] += row["remaining_capital_at_risk"]
        return {k: float(v) for k, v in result.items() if v > 0}

    def recovery_status_counts(self) -> dict[str, int]:
        result: dict[str, int] = defaultdict(int)
        for row in self.repository.master_rows():
            result[row["strategy_status"].value] += 1
        return dict(result)

    def unrecovered_age_buckets(self) -> dict[str, dict]:
        buckets = {"<30天": [0, Decimal("0")], "30–90天": [0, Decimal("0")], "90–180天": [0, Decimal("0")], "180–365天": [0, Decimal("0")], ">1年": [0, Decimal("0")]}
        for row in self.repository.master_rows():
            if row["remaining_capital_at_risk"] <= 0:
                continue
            days = row["holding_days"]
            key = "<30天" if days < 30 else "30–90天" if days < 90 else "90–180天" if days < 180 else "180–365天" if days < 365 else ">1年"
            buckets[key][0] += 1
            buckets[key][1] += row["remaining_capital_at_risk"]
        return {k: {"lots": v[0], "capital": float(v[1])} for k, v in buckets.items()}


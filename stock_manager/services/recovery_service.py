from __future__ import annotations

from decimal import Decimal

from stock_manager.database import PortfolioRepository
from stock_manager.domain import FeePolicy, OptimizationMode, RecoveryMode, dec, simulate_recovery


class RecoveryService:
    def __init__(self, repository: PortfolioRepository):
        self.repository = repository

    def fee_policy(self) -> FeePolicy:
        s = self.repository.settings()
        return FeePolicy(dec(s["commission_rate"]), dec(s["commission_discount"]), dec(s["minimum_commission"]), dec(s["sell_tax_rate"]))

    def simulate(
        self,
        lot_id: str,
        price: object,
        recovery_mode: RecoveryMode,
        optimization_mode: OptimizationMode,
        tolerance: object,
        custom_target: object = 0,
    ):
        rows = {r["id"]: r for r in self.repository.master_rows()}
        if lot_id not in rows:
            raise ValueError("找不到買進批次")
        row = rows[lot_id]
        if recovery_mode == RecoveryMode.PRINCIPAL:
            target = row["original_capital"]
        elif recovery_mode == RecoveryMode.PRINCIPAL_TRADING_COST:
            target = row["original_capital"] + row["trading_costs"]
        elif recovery_mode == RecoveryMode.FULL_COST:
            target = row["full_cost"]
        else:
            target = dec(custom_target)
            if target <= 0:
                raise ValueError("自訂回收目標必須大於 0")
        options = simulate_recovery(
            remaining_shares=row["remaining_shares"], price=price,
            already_recovered=row["net_cash_recovered"] + row["dividend_recovery"],
            target=target, tolerance=tolerance, mode=optimization_mode,
            fee_policy=self.fee_policy(),
        )
        return row, Decimal(target), options


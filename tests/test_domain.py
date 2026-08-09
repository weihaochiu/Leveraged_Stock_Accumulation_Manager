from decimal import Decimal
import unittest

from stock_manager.domain import (
    FeePolicy, OptimizationMode, StrategyStatus, calculate_lot_metrics,
    simulate_recovery, suggest_budget_shares,
)


class DomainTests(unittest.TestCase):
    def test_budget_suggestion_uses_integer_shares_below_budget(self):
        self.assertEqual(suggest_budget_shares(10000, 51.05), 195)

    def test_recovery_ratio_can_exceed_one_hundred_percent(self):
        lot = {"original_shares": 10, "original_capital": 9243, "buy_price": 924.3, "target_return_pct": 10, "recovery_tolerance_amount": 100}
        sells = [{"shares": 4, "net_cash": 9321, "commission": 0, "tax": 0, "other_fee": 0}]
        result = calculate_lot_metrics(lot, sells, current_price=205)
        self.assertGreater(result.capital_recovery_ratio, Decimal("1"))
        self.assertEqual(result.cash_surplus, Decimal("78.00"))
        self.assertEqual(result.remaining_shares, 6)

    def test_tolerance_keeps_accounting_ratio_truthful(self):
        lot = {"original_shares": 51, "original_capital": 9987, "buy_price": 195.82, "target_return_pct": 10, "recovery_tolerance_amount": 100}
        sells = [{"shares": 45, "net_cash": 9954, "commission": 0, "tax": 0, "other_fee": 0}]
        result = calculate_lot_metrics(lot, sells, current_price=221)
        self.assertLess(result.capital_recovery_ratio, Decimal("1"))
        self.assertEqual(result.strategy_status, StrategyStatus.COMPLETED_WITH_TOLERANCE)
        self.assertEqual(result.recovery_difference, Decimal("-33.00"))

    def test_keep_max_shares_selects_first_tolerance_eligible_option(self):
        options = simulate_recovery(remaining_shares=51, price=221, already_recovered=0, target=9987, tolerance=100,
                                    mode=OptimizationMode.KEEP_MAX_SHARES,
                                    fee_policy=FeePolicy(Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0")))
        chosen = next(o for o in options if o.recommended)
        self.assertEqual(chosen.shares, 45)
        self.assertEqual(chosen.remaining_shares, 6)


if __name__ == "__main__":
    unittest.main()


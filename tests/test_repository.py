from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from stock_manager.database import Database, PortfolioRepository
from stock_manager.database.repository import DuplicateTradeError


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.db = Database(Path(self.temp.name) / "portfolio.db"); self.repo = PortfolioRepository(self.db)
        self.broker = self.repo.add_broker("測試券商"); self.security = self.repo.ensure_security("006208", "富邦台50")

    def tearDown(self):
        self.temp.cleanup()

    def add_lot(self, order="BUY-1"):
        return self.repo.add_buy_lot({"security_id": self.security, "broker_account_id": self.broker, "buy_date": "2026-01-01", "buy_price": 100,
            "original_shares": 100, "stock_amount": 10000, "buy_fee": 20, "funding_type": "CASH", "cash_funded": 10020, "loan_funded": 0,
            "target_return_pct": 10, "recovery_tolerance_amount": 100, "broker_order_id": order})

    def test_sell_must_not_exceed_lot_remaining_shares(self):
        lot = self.add_lot()
        with self.assertRaises(ValueError):
            self.repo.add_sell({"lot_id": lot, "security_id": self.security, "broker_account_id": self.broker, "sell_date": "2026-02-01", "sell_price": 110,
                "shares": 101, "gross_amount": 11110, "commission": 10, "tax": 33, "net_cash": 11067})

    def test_broker_order_id_is_unique_across_buy_and_sell(self):
        lot = self.add_lot("ORDER-1")
        with self.assertRaises(DuplicateTradeError):
            self.repo.add_sell({"lot_id": lot, "security_id": self.security, "broker_account_id": self.broker, "sell_date": "2026-02-01", "sell_price": 110,
                "shares": 10, "gross_amount": 1100, "commission": 1, "tax": 3, "net_cash": 1096, "broker_order_id": "ORDER-1"})

    def test_security_default_does_not_retroactively_change_existing_lot(self):
        lot = self.add_lot()
        self.repo.update_security_strategy(self.security, {"default_target_return_pct": 25})
        self.assertEqual(self.repo.get_lot(lot)["target_return_pct"], 10)


if __name__ == "__main__":
    unittest.main()


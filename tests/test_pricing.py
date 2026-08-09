from datetime import date
from decimal import Decimal
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from stock_manager.database import Database, PortfolioRepository
from stock_manager.pricing.models import MarketQuote
from stock_manager.pricing.price_update_service import PriceUpdateService
from stock_manager.pricing.providers import PriceProvider, ProviderError, TPExProvider, TWSEProvider


class FakeProvider(PriceProvider):
    source = "TWSE"
    exchange = "TWSE"

    def __init__(self, quote=None, error=None):
        super().__init__(1)
        self.quote = quote
        self.error = error
        self.calls = []

    def fetch_latest(self, symbol, as_of=None):
        self.calls.append(symbol)
        if self.error:
            raise self.error
        return self.quote


class ProviderParsingTests(unittest.TestCase):
    def test_twse_parser_uses_latest_valid_day(self):
        provider = TWSEProvider()
        provider._get_json = lambda *args, **kwargs: {
            "stat": "OK",
            "title": "115年08月 2330 台積電 各日成交資訊",
            "data": [
                ["115/08/06", "1,000", "900,000", "890", "910", "880", "900", "+10", "100", ""],
                ["115/08/07", "2,000", "1,840,000", "910", "930", "905", "920", "+20", "120", ""],
            ],
        }
        quote = provider.fetch_latest("2330", date(2026, 8, 9))
        self.assertEqual(quote.trade_date, date(2026, 8, 7))
        self.assertEqual(quote.close, Decimal("920"))
        self.assertEqual(quote.volume_shares, 2000)
        self.assertEqual(quote.exchange, "TWSE")

    def test_tpex_parser_standardizes_lots_and_thousand_twd(self):
        provider = TPExProvider()
        provider._get_json = lambda *args, **kwargs: {
            "stat": "ok", "code": "6488", "name": "環球晶",
            "tables": [{"data": [["115/08/07", "9,568", "8,407,255", "879", "910", "855", "872", "0", "18,536"]]}],
        }
        quote = provider.fetch_latest("6488", date(2026, 8, 9))
        self.assertEqual(quote.volume_shares, 9_568_000)
        self.assertEqual(quote.turnover_twd, 8_407_255_000)
        self.assertEqual(quote.transaction_count, 18_536)


class PriceUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.repo = PortfolioRepository(Database(Path(self.temp.name) / "portfolio.db"))
        self.security = self.repo.ensure_security("2330", "台積電", "TWSE")
        self.repo.add_buy_lot({
            "security_id": self.security, "buy_date": "2026-01-01", "buy_price": 800,
            "original_shares": 10, "stock_amount": 8000, "buy_fee": 0,
            "funding_type": "CASH", "cash_funded": 8000, "loan_funded": 0,
            "target_return_pct": 10, "recovery_tolerance_amount": 100,
        })

    def tearDown(self):
        self.temp.cleanup()

    def test_only_current_holdings_are_queried_and_saved(self):
        unheld = self.repo.ensure_security("0050", "元大台灣50", "TWSE")
        quote = MarketQuote("2330", "台積電", "TWSE", date(2026, 8, 7), Decimal("920"), source="TWSE")
        provider = FakeProvider(quote=quote)
        service = PriceUpdateService(self.repo, providers={"TWSE": provider}, retry_delays=(), sleeper=lambda _: None)
        summary = service.update(trigger_type="MANUAL_ALL", as_of=date(2026, 8, 9))
        self.assertEqual(provider.calls, ["2330"])
        self.assertEqual(summary.success_count, 1)
        self.assertEqual(self.repo.latest_price(self.security)["price"], 920)
        self.assertIsNone(self.repo.latest_price(unheld))

    def test_failure_keeps_cached_price(self):
        self.repo.add_price(self.security, 900, "2026-08-06")
        provider = FakeProvider(error=ProviderError("暫時無法連線"))
        service = PriceUpdateService(self.repo, providers={"TWSE": provider}, retry_delays=(), sleeper=lambda _: None)
        summary = service.update(trigger_type="MANUAL_ALL", as_of=date(2026, 8, 9))
        self.assertEqual(summary.failed_count, 1)
        self.assertEqual(self.repo.latest_price(self.security)["price"], 900)
        self.assertIn("沿用最近成功價格", summary.results[0].message)

    def test_manual_price_wins_over_official_on_same_trade_date(self):
        quote = MarketQuote("2330", "台積電", "TWSE", date(2026, 8, 7), Decimal("920"), source="TWSE")
        self.repo.save_market_quote(self.security, quote)
        self.repo.add_price(self.security, 925, "2026-08-07")
        self.assertEqual(self.repo.latest_price(self.security)["price"], 925)
        self.assertEqual(self.repo.latest_price(self.security)["source"], "MANUAL")


class MigrationTests(unittest.TestCase):
    def test_v1_price_table_is_upgraded_without_losing_data(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "portfolio.db"
            conn = sqlite3.connect(path)
            conn.execute("CREATE TABLE schema_info(version INTEGER NOT NULL,applied_at TEXT DEFAULT CURRENT_TIMESTAMP)")
            conn.execute("INSERT INTO schema_info(version) VALUES (1)")
            conn.execute("CREATE TABLE securities(id INTEGER PRIMARY KEY,symbol TEXT,name TEXT,market TEXT,currency TEXT,active INTEGER,created_at TEXT,updated_at TEXT)")
            conn.execute("INSERT INTO securities VALUES (1,'2330','台積電','TWSE','TWD',1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)")
            conn.execute("""CREATE TABLE price_history(
                id INTEGER PRIMARY KEY AUTOINCREMENT,security_id INTEGER,price REAL,price_date TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,source TEXT DEFAULT 'MANUAL',daily_change_pct REAL,
                UNIQUE(security_id,price_date,source))""")
            conn.execute("INSERT INTO price_history(security_id,price,price_date,source) VALUES (1,900,'2026-08-07','手動輸入')")
            conn.commit(); conn.close()
            database = Database(path)
            with database.connect() as upgraded:
                columns = {row["name"] for row in upgraded.execute("PRAGMA table_info(price_history)")}
                row = upgraded.execute("SELECT * FROM price_history").fetchone()
                version = upgraded.execute("SELECT MAX(version) FROM schema_info").fetchone()[0]
            self.assertIn("fetched_at", columns)
            self.assertEqual(row["price"], 900)
            self.assertEqual(row["is_manual_override"], 1)
            self.assertEqual(version, 2)


if __name__ == "__main__":
    unittest.main()

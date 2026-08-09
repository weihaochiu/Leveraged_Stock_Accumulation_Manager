from __future__ import annotations

from datetime import date

from stock_manager.database import PortfolioRepository


class PriceService:
    """V1 以可追溯的手動價格為主；外部報價來源可透過相同介面擴充。"""

    def __init__(self, repository: PortfolioRepository):
        self.repository = repository

    def update_manual(self, security_id: int, price: object, price_date: str | None = None) -> None:
        self.repository.add_price(security_id, price, price_date or date.today().isoformat(), "手動輸入")


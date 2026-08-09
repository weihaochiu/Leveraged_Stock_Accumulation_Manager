from __future__ import annotations

from datetime import date

from stock_manager.database import PortfolioRepository


class PriceService:
    """保留相容介面的手動價格服務。"""

    def __init__(self, repository: PortfolioRepository):
        self.repository = repository

    def update_manual(self, security_id: int, price: object, price_date: str | None = None) -> None:
        self.repository.add_price(security_id, price, price_date or date.today().isoformat(), "MANUAL")
